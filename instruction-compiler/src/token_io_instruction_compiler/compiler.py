"""将审核后的作者指令编译为同批静态资源，不实现业务流程执行器。"""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

from .bundle import make_skill_files, publish_compilation
from .contracts import (
    EVENTS,
    HOOK_ROOT,
    INSTRUCTION_IDENTITIES,
    POLICIES,
    POLICY_SECTION_KEYS,
    WORKFLOWS,
    parse_event_contract,
    validate_author_registry,
)
from .models import (
    CheckpointListing,
    CompilationReport,
    CompilationSummary,
    CompiledContent,
    CompiledContextIndex,
    CompiledDocument,
    CompiledFragment,
    DeliveryReport,
    DocumentIndex,
    EventInstruction,
    FragmentInstruction,
    Instruction,
    PolicyInstruction,
    RuleRegistry,
)
from .sources import (
    AuthorSources,
    CompilationError,
    canonical,
    digest,
    heading_sections,
    safe_file,
    source_path,
    validate_dependency_graph,
)

SCHEMA_VERSION = 3
COMPILER_VERSION = "4"
MAX_INSTRUCTION_CHARS = 120_000
_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


class Compiler:
    """编排单一中文作者源、政策索引和静态产物；不构建业务执行路径。"""

    def __init__(self, repository_root: Path, *, max_chars: int = MAX_INSTRUCTION_CHARS):
        """以仓库根目录装配已验证的作者契约；重复节点或隐含流程后继会阻止编译。"""
        project = repository_root.resolve() / "instruction-compiler"
        self.sources = AuthorSources(
            project / "sources/skill",
            max_chars=max_chars,
            instruction_ids=INSTRUCTION_IDENTITIES,
        )
        self.registry = validate_author_registry(
            json.loads((project / "sources/rule-registry.json").read_text())
        )
        self.index = validate_dependency_graph(
            json.loads((project / "sources/rule-context-index.json").read_text())
        )
        self.node_map = {node["node_id"]: node for node in self.registry["nodes"]}
        self.fragment_map = {item["fragment_id"]: item for item in self.index["fragments"]}
        self.index_nodes = {item["node_id"]: item for item in self.index["nodes"]}
        if len(self.node_map) != len(self.registry["nodes"]):
            raise CompilationError("duplicate rule node")
        if set(self.index_nodes) != set(self.node_map):
            raise CompilationError("registry and index nodes differ")
        if any(node.get("next_checkpoint_ids") for node in self.registry["nodes"]):
            raise CompilationError("static rule lookups must not declare workflow successors")
        self.delivery: DeliveryReport = {}

    @property
    def report(self) -> CompilationReport:
        """交付当前追溯快照，调用方修改报告不会反向修改源读取器。"""
        return {**copy.deepcopy(self.sources.trace), "delivery": copy.deepcopy(self.delivery)}

    def node_path(self, node_id: str) -> str:
        """将静态节点 ID 解析为唯一作者标题，仅用于选段和文档导航。"""
        node = self.node_map[node_id]
        return source_path(node["owner_path"]) + "#" + node["owner_section"]

    def fragment_roots(self, fragment_id: str) -> list[str]:
        """按依赖先后返回去重的作者选段；这是静态指令组合，不是业务调度。"""
        roots: list[str] = []
        seen: set[str] = set()

        def visit(key: str) -> None:
            if key in seen:
                return
            seen.add(key)
            spec = self.fragment_map[key]
            for dependency in spec.get("dependencies", []):
                visit(dependency)
            heading = spec.get("section")
            selected = spec["source_path"] + ("#" + heading if heading else "")
            if selected not in roots:
                roots.append(selected)

        visit(fragment_id)
        return roots

    def _compile_policy(self, selections: list[tuple[str, str]]) -> PolicyInstruction:
        """按审核过的标题组合政策，保留既有 API 所需的机器索引与选项说明。"""
        roots: list[str] = []
        sections: dict[str, str] = {}
        choices: dict[str, dict[str, str]] = {}
        for filename, title in selections:
            source = HOOK_ROOT + filename + ".md"
            roots.append(source + "#" + title)
            key = POLICY_SECTION_KEYS.get(title)
            if key is None:
                continue
            section = self.sources.select(source + "#" + title)
            sections[key] = section
            if "choice descriptions" in key:
                choices[key] = heading_sections(section, 4)
        return {**self.sources.instruction(roots), "sections": sections, "choices": choices}

    def policies(self) -> dict[str, PolicyInstruction]:
        """生成细粒度建议工具所用政策，保持每项政策自身的来源范围。"""
        return {owner: self._compile_policy(selections) for owner, selections in POLICIES.items()}

    def _validate_document_link(self, path: str, match: re.Match[str], delivered: set[str]) -> None:
        """本地导航必须留在本批交付中；外部链接不触发作者源展开。"""
        parts = urlsplit(match[2])
        if parts.scheme or parts.netloc or not parts.path:
            return
        target = ((self.sources.root / path).parent / unquote(parts.path)).resolve()
        if not target.is_relative_to(self.sources.root.resolve()):
            raise CompilationError(f"author document link leaves Skill: {path}: {match[2]}")
        relative = target.relative_to(self.sources.root.resolve()).as_posix()
        safe_file(self.sources.root, relative)
        if relative not in delivered:
            raise CompilationError(f"document target is not delivered: {path}: {match[2]}")

    def validate_links(self, paths: set[str]) -> None:
        """校验所选文档的导航闭包，拒绝逃逸、缺失或未交付的本地目标。"""
        for path in sorted(paths):
            for match in _LINK.finditer(self.sources.read(path)):
                self._validate_document_link(path, match, paths)

    def _compile_events(self) -> dict[str, EventInstruction]:
        """从同一事件卡读取结构契约，再组合共享约束，避免元数据与正文分离。"""
        events: dict[str, EventInstruction] = {}
        for event_id in EVENTS:
            path = HOOK_ROOT + event_id.replace("_", "-") + ".md"
            contract = parse_event_contract(self.sources.read(path), event_id, path)
            events[event_id] = {
                **contract,
                **self.sources.instruction([HOOK_ROOT + "shared.md", path]),
            }
        return events

    def _compile_nodes(self) -> dict[str, Instruction]:
        """为既有查询 ID 组合完整默认正文，不产生节点运行状态或后继步骤。"""
        nodes: dict[str, Instruction] = {}
        for node_id, spec in self.index_nodes.items():
            roots: list[str] = []
            for key in spec["default_fragment_ids"]:
                roots.extend(self.fragment_roots(key))
            nodes[node_id] = self.sources.instruction(roots)
        return nodes

    def _compile_fragments(self) -> dict[str, FragmentInstruction]:
        """生成显式片段正文与对应 Hash，保留片段协议使用的字段名称。"""
        fragments: dict[str, FragmentInstruction] = {}
        for fragment_id in self.fragment_map:
            item = self.sources.instruction(self.fragment_roots(fragment_id))
            fragments[fragment_id] = {
                "text": item["text"],
                "text_sha256": item["content_sha256"],
                "instruction_ids": item["instruction_ids"],
            }
        return fragments

    def _compiled_registry(self) -> RuleRegistry:
        """保留机器要求，只将作者路径改为产品内的 compiled 引用。"""
        registry = copy.deepcopy(self.registry)
        for node in registry["nodes"]:
            node["owner_path"] = f"compiled:{node['node_id']}"
            node["owner_section"] = "编译后的当前规则指令"
        return registry

    def _compiled_index(self) -> CompiledContextIndex:
        """发布静态片段依赖与中文标题，运行时索引不携带作者文件路径。"""
        fragments: list[CompiledFragment] = []
        for spec in self.index["fragments"]:
            fragment: CompiledFragment = {
                "fragment_id": spec["fragment_id"],
                "node_id": spec["node_id"],
                "section": spec.get("section", "完整当前事件卡"),
            }
            if "dependencies" in spec:
                fragment["dependencies"] = list(spec["dependencies"])
            fragments.append(fragment)
        return {
            "schema_version": 2,
            "nodes": copy.deepcopy(self.index["nodes"]),
            "fragments": fragments,
        }

    def _skill_cards(self) -> dict[str, str]:
        """仅选取获准的产品文档清单；目录内其它文件不会自动进入交付。"""
        paths = {
            "SKILL.md",
            "WORKFLOW_ARCHITECTURE.md",
            "workflows/coding.md",
            "agents/openai.yaml",
            *WORKFLOWS.values(),
        }
        paths.update(
            HOOK_ROOT + name + ".md"
            for name in ("README", "shared", *(event.replace("_", "-") for event in EVENTS))
        )
        self.validate_links(paths)
        return {path: self.sources.read(path) for path in sorted(paths)}

    def _record_delivery(self, body: CompiledDocument, files: dict[str, bytes]) -> None:
        """记录实际交付正文与入口字节规模；该报告不是任务运行状态。"""
        contract = body["nodes"]["contract"]["text"]
        self.delivery = {
            "default_contract": {"characters": len(contract), "bytes": len(contract.encode())},
            "skill_entry": {
                "characters": len(files["SKILL.md"].decode()),
                "bytes": len(files["SKILL.md"]),
            },
            "navigation_expanded": False,
        }

    def _checkpoint_listing(self, node_id: str) -> CheckpointListing:
        """将节点要求与唯一当前文档地址汇入纯文档查询索引。"""
        spec = self.node_map[node_id]
        return {
            "node_id": node_id,
            "required_facts": spec["required_facts"],
            "required_evidence": spec["required_evidence"],
            "legal_branches": spec["legal_branches"],
            "evaluation_mode": spec["evaluation_mode"],
            "failure_action": spec["failure_action"],
            "next_checkpoint_ids": spec["next_checkpoint_ids"],
            "document": self.node_path(node_id),
        }

    def document_index(self) -> DocumentIndex:
        """返回单中文文档导航索引；路径用于检索指令，不表示运行游标。"""
        return {
            "schema_version": 3,
            "language": "zh_cn",
            "events": {event: HOOK_ROOT + event.replace("_", "-") + ".md" for event in EVENTS},
            "workflows": dict(WORKFLOWS),
            "checkpoints": {
                node_id: self._checkpoint_listing(node_id) for node_id in self.node_map
            },
            "fragments": {key: self.fragment_roots(key) for key in self.fragment_map},
        }

    def _compile_workflows(self) -> dict[str, Instruction]:
        """只交付所选模式的短指令，不预加载事件正文或模拟执行路径。"""
        return {mode: self.sources.instruction([source]) for mode, source in WORKFLOWS.items()}

    def _compiled_content(self, document_units: dict[str, str]) -> CompiledContent:
        """汇总参与构建身份的静态内容；真实构建 ID 在汇总后计算。"""
        return {
            "schema_version": SCHEMA_VERSION,
            "compiler_version": COMPILER_VERSION,
            "language": "zh_cn",
            "registry": self._compiled_registry(),
            "context_index": self._compiled_index(),
            "nodes": self._compile_nodes(),
            "fragments": self._compile_fragments(),
            "policies": self.policies(),
            "events": self._compile_events(),
            "workflows": self._compile_workflows(),
            "document_units": document_units,
        }

    def compile(self) -> tuple[CompiledDocument, dict[str, bytes]]:
        """返回同一批次的资源正文和 Skill 文件；固定占位符避免构建身份自引用。"""
        cards = self._skill_cards()
        index = self.document_index()
        normalized = make_skill_files(cards, "__BUILD_ID__", index)
        document_units = {
            path: digest(data)
            for path, data in sorted(normalized.items())
            if path != "manifest.json"
        }
        content = self._compiled_content(document_units)
        build_id = digest(canonical(content))
        files = make_skill_files(cards, build_id, index)
        document: CompiledDocument = {
            **content,
            "build_id": build_id,
            "skill_files": {
                path: digest(data)
                for path, data in sorted(files.items())
                if path != "manifest.json"
            },
        }
        self._record_delivery(document, files)
        return document, files


def compile_repository(
    root: Path, *, check: bool = False, max_chars: int = MAX_INSTRUCTION_CHARS
) -> CompilationSummary:
    """从作者源编译后检查或发布；check 只校验，不创建可选导出或改写产物。"""
    compiler = Compiler(root, max_chars=max_chars)
    body, skill_files = compiler.compile()
    return publish_compilation(root, body, skill_files, compiler.report, check)


def main(argv: list[str] | None = None) -> int:
    """解析开发 CLI 参数，成功输出构建摘要，已知编译故障以非零状态结束。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", nargs="?", choices=["compile"], default="compile")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--max-chars", type=int, default=MAX_INSTRUCTION_CHARS)
    args = parser.parse_args(argv)
    try:
        result = compile_repository(args.root, check=args.check, max_chars=args.max_chars)
    except (CompilationError, OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"instruction compilation failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Compile reviewed author policies into self-contained product instruction resources.

The source index declares execution dependencies. Language switches, Related-concepts
sections, diagrams and directory navigation are not execution inputs. Each current
action contract is delivered directly; independent policies have exact, statically
validated instruction continuations. The private report records those boundaries for
semantic review. Nothing in this module
is imported at product startup or during wheel/sdist assembly.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import sys
import zipfile
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

SCHEMA_VERSION = 2
COMPILER_VERSION = "1"
LANGUAGES = ("en", "zh_cn")
MAX_INSTRUCTION_CHARS = 120_000
_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$", re.MULTILINE)
_MERMAID = re.compile(r"^```mermaid\s*\n.*?^```\s*$", re.MULTILINE | re.DOTALL)
_RELATED = re.compile(
    r"^## (?:Related concepts|Related documents|相关概念|相关文档)\s*$", re.MULTILINE
)
_STAGES = (
    ("entry_readiness", "entry-readiness"),
    ("session_readiness", "session-readiness"),
    ("work_definition", "work-definition"),
    ("execution", "single-execution"),
    ("verification_repair", "verification-repair"),
    ("documentation", "documentation"),
    ("delivery_acceptance", "delivery-acceptance"),
)
_POLICIES = {
    "child-role-selection": "delegation/child-role-selection.md",
    "task-assignment": "execution-planning/task-assignment.md",
    "output-token-routing": "execution-planning/output-token-routing.md",
    "session-role-ownership": "session-runtime/session-role-ownership.md",
    "decision-context-generation": "execution-planning/decision-context-generation.md",
    "workflow-routing-advice": "execution-planning/workflow-routing-advice.md",
    "candidate-compliance": "execution-planning/candidate-compliance.md",
    "output-materialization": "execution-planning/output-materialization.md",
}
_OPTIONAL = {
    "decision.workflow_routing_advice": "workflow-routing-advice",
    "implementation.candidate_compliance": "candidate-compliance",
    "implementation.output_materialization": "output-materialization",
}
_ALIASES = {
    "Role Decisions instructions": "职责 Decisions 指令",
    "Role choice descriptions": "职责选项说明",
    "Executor Decisions instructions": "执行主体 Decisions 指令",
    "Executor choice descriptions": "执行主体选项说明",
    "Child-selection Decisions instructions": "子代理选择 Decisions 指令",
    "Child-candidate choice descriptions": "子代理选项说明",
    "Output-token Decisions instructions": "Output Token Decisions 指令",
    "Output-token choice descriptions": "Output Token 选项说明",
}
_NODE_PHASE = {
    "contract": "entry_readiness",
    "mode": "mode",
    "context": "work_definition",
    "decision": "work_definition",
    "slice": "execution",
    "delegation": "execution",
    "implementation": "execution",
    "control": "execution",
    "verification": "verification_repair",
    "repair": "verification_repair",
    "repair_scope": "verification_repair",
    "repair_execution": "verification_repair",
    "repair_handoff": "verification_repair",
    "documentation": "documentation",
    "git": "delivery_acceptance",
    "acceptance": "delivery_acceptance",
    "task_intent": "entry_readiness",
    "output_class": "mode",
    "contract_change": "entry_readiness",
    "verification_impact": "verification_repair",
}
# These are explicit phase/continuation declarations, not an inference that every
# Markdown link is an execution dependency. A phase checks prior evidence; it
# does not rerun earlier effects or preload a future conditional operation.
_SOURCE_PHASE = {
    "contract": "entry_readiness",
    "environment": "entry_readiness",
    "environment-capability-inventory": "entry_readiness",
    "route-entry": "entry_readiness",
    "mode": "mode",
    "delegation-mode-confirmation": "mode",
    "delegation-mode-count-gate": "mode",
    "delegation-mode-reentry": "mode",
    "delegation-state-record": "mode",
    "session-model": "session_readiness",
    "session-audit-visibility": "session_readiness",
    "reasoning-summary-visibility": "session_readiness",
    "session-state-resolution": "session_readiness",
    "session-audit-resolution": "session_readiness",
    "runtime-provider-support": "execution",
    "child-role-selection": "execution",
    "delegation-child-creation": "execution",
    "delegation-child-dispatch": "execution",
    "delegation-child-lifecycle": "execution",
    "delegation-child-reuse-replacement": "execution",
    "delegation-child-role-allocation": "execution",
    "delegation-child-message-visibility": "execution",
    "delegation-worker-boundary": "execution",
    "task-assignment": "execution",
    "output-token-routing": "execution",
    "execution-control": "execution",
    "implementation": "execution",
    "control": "execution",
    "executor-selection": "execution",
    "output-route-selection": "execution",
    "role-reservation": "execution",
    "bootstrap-selection": "execution",
    "context": "work_definition",
    "execution-planning": "work_definition",
    "task-plan-memory-lifecycle": "work_definition",
    "decision-context-generation": "work_definition",
    "workflow-routing-advice": "work_definition",
    "context-source-selection": "work_definition",
    "planning-output-selection": "work_definition",
    "decision-context-selection": "work_definition",
    "verification": "verification_repair",
    "verification-independence": "verification_repair",
    "verification-reporting": "verification_repair",
    "verification-epoch": "verification_repair",
    "repair": "verification_repair",
    "repair-scope-gate": "verification_repair",
    "repair-execution": "verification_repair",
    "repair-verification-handoff": "verification_repair",
    "repair-disposition": "verification_repair",
    "documentation": "documentation",
    "documentation-impact": "documentation",
    "git": "delivery_acceptance",
    "acceptance": "delivery_acceptance",
    "entry-readiness": "entry_readiness",
    "session-readiness": "session_readiness",
    "work-definition": "work_definition",
    "single-execution": "execution",
    "delegated-execution": "execution",
    "verification-repair": "verification_repair",
    "delivery-acceptance": "delivery_acceptance",
}
_EXTRA_FRAGMENTS = {
    "context.project_tools": ("context", "session-runtime/LSP-MCP-Tools.md", "project_tools"),
    "context.memo": ("context", "context-exchange/content-memo.md", "context_exchange"),
    "delegation.creation": ("delegation", "delegation/delegation-child-creation.md", "creation"),
    "delegation.dispatch": ("delegation", "delegation/delegation-child-dispatch.md", "dispatch"),
    "delegation.lifecycle": ("delegation", "delegation/delegation-child-lifecycle.md", "lifecycle"),
    "delegation.reuse": (
        "delegation",
        "delegation/delegation-child-reuse-replacement.md",
        "lifecycle",
    ),
    "delegation.role_allocation": (
        "delegation",
        "delegation/delegation-child-role-allocation.md",
        "allocation",
    ),
    "implementation.feedback": (
        "implementation",
        "execution-control/execution-stage-feedback.md",
        "feedback",
    ),
    "decision.decision_context": (
        "decision",
        "execution-planning/decision-context-generation.md",
        "decision_context",
    ),
}
_SHARED_FRAGMENTS = {
    "common.hard_constraints": {
        "node_id": "contract",
        "path": "SKILL.md",
        "section_en": "Hard constraints",
        "section_zh_cn": "硬约束",
    },
    "route.single_agent.return_map": {
        "node_id": "context",
        "path": "references/coding/layer-04-workflows/coding-single-agent.md",
        "section_en": "Prerequisite return map",
        "section_zh_cn": "前置返回映射",
    },
    "route.multi_agent.return_map": {
        "node_id": "context",
        "path": "references/coding/layer-04-workflows/coding-multi-agent.md",
        "section_en": "Prerequisite return map",
        "section_zh_cn": "前置返回映射",
    },
}
_SOURCE_PHASE.update(
    {
        "child-role-selection": "allocation",
        "delegation-child-role-allocation": "allocation",
        "delegation-child-creation": "creation",
        "runtime-provider-support": "creation",
        "delegation-child-dispatch": "dispatch",
        "delegation-worker-boundary": "dispatch",
        "delegation-child-message-visibility": "dispatch",
        "delegation-child-lifecycle": "lifecycle",
        "delegation-child-reuse-replacement": "lifecycle",
        "content-memo": "context_exchange",
        "content-memo-dispatch": "context_exchange",
        "content-memo-lifecycle": "context_exchange",
        "context-exchange": "context_exchange",
        "context-exchange-handoff": "context_exchange",
        "context-exchange-workspace-boundary": "context_exchange",
        "LSP-MCP-Tools": "project_tools",
        "execution-stage-feedback": "feedback",
        "decision-context-generation": "decision_context",
    }
)


class CompilationError(ValueError):
    """Source, contract or approved-output integrity prevents compilation."""


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def digest(value: bytes | str) -> str:
    return hashlib.sha256(value.encode() if isinstance(value, str) else value).hexdigest()


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def mirror(path: str, language: str) -> str:
    return path if language == "en" else path.removesuffix(".md") + "_zh_cn.md"


def safe_file(root: Path, relative: str) -> Path:
    if "\\" in relative or "\0" in relative:
        raise CompilationError("invalid source path")
    item = Path(relative)
    if item.is_absolute() or ".." in item.parts:
        raise CompilationError(f"unsafe source path: {relative}")
    cursor = root
    for part in item.parts:
        cursor /= part
        if cursor.is_symlink():
            raise CompilationError(f"symlinked author source: {relative}")
    if not cursor.is_file() or not cursor.resolve().is_relative_to(root.resolve()):
        raise CompilationError(f"missing author source: {relative}")
    return cursor


def extract_heading(text: str, heading: str) -> str:
    """Select one real ATX heading, ignoring fenced examples."""
    fence: str | None = None
    matches: list[tuple[int, int, int, str]] = []
    offset = 0
    for line in text.splitlines(keepends=True):
        stripped = line.lstrip()
        if stripped.startswith(("```", "~~~")):
            marker = stripped[:3]
            fence = None if fence == marker else marker if fence is None else fence
        elif fence is None:
            match = _HEADING.fullmatch(line.rstrip("\r\n"))
            if match:
                matches.append((offset, offset + len(line), len(match[1]), match[2]))
        offset += len(line)
    selected = [entry for entry in matches if entry[3] == heading]
    if len(selected) != 1:
        raise CompilationError(f"missing or duplicate source heading: {heading}")
    start, _body, level, _ = selected[0]
    end = next((entry[0] for entry in matches if entry[0] > start and entry[2] <= level), len(text))
    result = text[start:end].strip()
    if not result.partition("\n")[2].strip():
        raise CompilationError(f"empty source heading: {heading}")
    return result


def validate_dependency_graph(index: dict[str, Any]) -> None:
    if index.get("schema_version") != 1:
        raise CompilationError("unsupported author context-index schema")
    fragments = index.get("fragments", [])
    lookup = {entry["fragment_id"]: entry for entry in fragments}
    if len(lookup) != len(fragments):
        raise CompilationError("duplicate author fragment identity")
    active: set[str] = set()
    done: set[str] = set()

    def visit(key: str) -> None:
        if key not in lookup:
            raise CompilationError(f"missing execution dependency: {key}")
        if key in active:
            raise CompilationError(f"execution dependency cycle: {key}")
        if key in done:
            return
        active.add(key)
        for dependency in lookup[key].get("dependencies", []):
            visit(dependency)
        active.remove(key)
        done.add(key)

    for key in lookup:
        visit(key)
    for node in index.get("nodes", []):
        for key in node["default_fragment_ids"]:
            visit(key)


class Compiler:
    def __init__(self, repository_root: Path, *, max_chars: int = MAX_INSTRUCTION_CHARS):
        self.root = repository_root.resolve()
        self.project = self.root / "instruction-compiler"
        self.source = self.project / "sources" / "skill"
        self.max_chars = max_chars
        self.registry = json.loads((self.project / "sources" / "rule-registry.json").read_text())
        self.index = json.loads((self.project / "sources" / "rule-context-index.json").read_text())
        for fragment_id, (node_id, _path, _phase) in _EXTRA_FRAGMENTS.items():
            if not any(item["fragment_id"] == fragment_id for item in self.index["fragments"]):
                self.index["fragments"].append(
                    {
                        "fragment_id": fragment_id,
                        "node_id": node_id,
                        "section_en": "General rules",
                        "section_zh_cn": "通用规范",
                    }
                )
        for fragment_id, spec in _SHARED_FRAGMENTS.items():
            if any(item["fragment_id"] == fragment_id for item in self.index["fragments"]):
                raise CompilationError(f"reserved shared instruction identity: {fragment_id}")
            self.index["fragments"].append(
                {
                    "fragment_id": fragment_id,
                    "node_id": spec["node_id"],
                    "section_en": spec["section_en"],
                    "section_zh_cn": spec["section_zh_cn"],
                }
            )
        self.node_map = {node["node_id"]: node for node in self.registry["nodes"]}
        self.fragment_map = {item["fragment_id"]: item for item in self.index["fragments"]}
        if len(self.node_map) != len(self.registry["nodes"]):
            raise CompilationError("duplicate rule node")
        if set(self.node_map) - set(_NODE_PHASE):
            raise CompilationError("unsupported rule node phase")
        if {node["node_id"] for node in self.index["nodes"]} != set(self.node_map):
            raise CompilationError("registry and index nodes differ")
        validate_dependency_graph(self.index)
        self.report: dict[str, Any] = {"closures": {}, "source_hashes": {}}
        self._content_cache: dict[tuple[str, str], str] = {}
        self.units: dict[str, tuple[str, str]] = {}

    def register_unit(self, path: str) -> tuple[str, str]:
        english = path.removesuffix("_zh_cn.md") + ".md" if path.endswith("_zh_cn.md") else path
        identity = "unit." + digest(english)[:16]
        phase = _SOURCE_PHASE.get(Path(english).stem, "work_definition")
        node = {
            "entry_readiness": "contract",
            "mode": "mode",
            "session_readiness": "context",
            "work_definition": "decision",
            "execution": "implementation",
            "verification_repair": "verification",
            "documentation": "documentation",
            "delivery_acceptance": "acceptance",
            "creation": "delegation",
            "dispatch": "delegation",
            "lifecycle": "delegation",
            "allocation": "delegation",
            "project_tools": "context",
            "context_exchange": "context",
            "feedback": "implementation",
            "decision_context": "decision",
        }.get(phase, "context")
        owners = [
            node_id
            for node_id, spec in self.node_map.items()
            if self.source_path(spec["owner_path"]) == english
        ]
        if len(owners) == 1:
            node = owners[0]
        self.units[identity] = (english, node)
        return identity, node

    def source_identity(self, path: str) -> str:
        source, separator, heading = path.partition("#")
        english = (
            source.removesuffix("_zh_cn.md") + ".md" if source.endswith("_zh_cn.md") else source
        )
        if english == "SKILL.md" and heading in {"Hard constraints", "硬约束"}:
            return "common.hard_constraints"
        if separator:
            for node_id, node in self.node_map.items():
                if self.source_path(node["owner_path"]) == english and heading in {
                    node["owner_section"],
                    node["owner_mirrors"]["zh_cn"]["section"],
                }:
                    return "selection." + node_id
        return "unit." + digest(english + ("#" + heading if separator else ""))[:16]

    def source_path(self, path: str) -> str:
        for prefix in ("instruction-compiler/sources/skill/", "docs/skill/"):
            if path.startswith(prefix):
                return path[len(prefix) :]
        if path.startswith("references/") or path.startswith("workflows/"):
            return path
        raise CompilationError(f"source outside the author Skill: {path}")

    def read_source(self, path: str) -> str:
        file = safe_file(self.source, path)
        text = file.read_text(encoding="utf-8")
        self.report["source_hashes"][path] = digest(text)
        return text

    def operational_source(self, path: str, profile: str) -> str:
        path, _separator, selected = path.partition("#")
        key = (path + "#" + selected, profile)
        if key in self._content_cache:
            return self._content_cache[key]
        text = self.read_source(path)
        related = _RELATED.search(text)
        if related:
            text = text[: related.start()]
        text = _MERMAID.sub("", text)
        lines = text.splitlines()
        lines = [line for line in lines if not ("[English](" in line and "[简体中文](" in line)]
        text = "\n".join(lines).strip()
        if selected:
            text = extract_heading(text, selected)
        elif path in {"SKILL.md", "SKILL_zh_cn.md"}:
            headings = (
                ("从这里开始", "硬约束")
                if path.endswith("_zh_cn.md")
                else ("Start here", "Hard constraints")
            )
            text = "\n\n".join(extract_heading(text, heading) for heading in headings)
        elif path in {"workflows/coding.md", "workflows/coding_zh_cn.md"}:
            headings = (
                ("入口", "路线", "完成")
                if path.endswith("_zh_cn.md")
                else ("Entry", "Routes", "Completion")
            )
            text = "\n\n".join(extract_heading(text, heading) for heading in headings)
        if "layer-01-fundamental-concepts/" in path and not selected:
            language = "zh_cn" if path.endswith("_zh_cn.md") else "en"
            general = "通用规范" if language == "zh_cn" else "General rules"
            codex = (
                "Codex CLI / ChatGPT Desktop 特别优化指令"
                if language == "zh_cn"
                else "Codex CLI / ChatGPT Desktop optimizations"
            )
            claude = (
                "Claude Code CLI / Claude Desktop 特别优化指令"
                if language == "zh_cn"
                else "Claude Code CLI / Claude Desktop optimizations"
            )
            title = lines[0] if lines else path
            sections = [extract_heading(text, general), extract_heading(text, codex)]
            if profile == "documents":
                sections.append(extract_heading(text, claude))
            text = title + "\n\n" + "\n\n".join(sections)
        self._content_cache[key] = text
        return text

    def local_links(self, path: str, text: str) -> list[tuple[str, str, str]]:
        """Resolve executable-section policy links, not Related/navigation links."""
        path = path.partition("#")[0]
        result = []
        for match in _LINK.finditer(text):
            raw = match[2].split(' "', 1)[0].strip().strip("<>")
            parts = urlsplit(raw)
            if parts.scheme or parts.netloc or (not parts.path and not parts.fragment):
                continue
            target = (
                ((self.source / path).parent / unquote(parts.path))
                if parts.path
                else self.source / path
            )
            resolved = target.resolve()
            if not resolved.is_relative_to(self.source.resolve()):
                # Runtime policy must not acquire a development-guide dependency.
                if parts.path.endswith(".md"):
                    raise CompilationError(
                        f"executable author link leaves policy tree: {path}: {raw}"
                    )
                continue
            if not resolved.is_file():
                if resolved.is_dir():
                    continue
                raise CompilationError(f"missing operational policy target: {path}: {raw}")
            if resolved.suffix != ".md":
                continue
            relative = resolved.relative_to(self.source.resolve()).as_posix()
            if relative.endswith("_zh_cn.md") != path.endswith("_zh_cn.md"):
                raise CompilationError(f"cross-language operational dependency: {path}: {raw}")
            result.append((relative, unquote(parts.fragment), match[2]))
        return result

    def clean_text(self, text: str, continuations: dict[str, str] | None = None) -> str:
        def replace(match: re.Match[str]) -> str:
            parts = urlsplit(match[2].split(' "', 1)[0].strip().strip("<>"))
            if parts.scheme or parts.netloc:
                return match[0]
            continuation = (continuations or {}).get(match[2])
            return match[1] + (
                f" (instruction continuation: {continuation})" if continuation else ""
            )

        return _LINK.sub(replace, text)

    def instruction_lookup(self, fragment_id: str, node_id: str, language: str) -> dict[str, Any]:
        return {
            "tool": "rules_get_context",
            "arguments": {
                "payload": {
                    "node_id": node_id,
                    "context_version": 2,
                    "language": language,
                    "fragment_ids": [fragment_id],
                    "max_chars": f"__BUDGET_{fragment_id}_{language}__",
                }
            },
        }

    def lookup_text(self, lookup: dict[str, Any]) -> str:
        return (
            "`rules_get_context(payload="
            + json.dumps(lookup["arguments"]["payload"], ensure_ascii=False, separators=(",", ":"))
            + ")`"
        )

    def render_text(
        self, path: str, text: str, language: str, profile: str, document_route: str | None = None
    ) -> tuple[str, dict[str, str]]:
        continuations = {}
        report = {}
        for target, _anchor, raw in self.local_links(path, text):
            stem = Path(target).stem.removesuffix("_zh_cn")
            if stem == "WORKFLOW_ARCHITECTURE":
                continuation = "workflow_capabilities()"
            else:
                unit_id, owner_node = self.register_unit(target)
                if profile == "documents":
                    module_number = next(
                        (
                            number
                            for number, (_stage, module) in enumerate(_STAGES, 1)
                            if stem == module or (number == 4 and stem == "delegated-execution")
                        ),
                        None,
                    )
                    if document_route and module_number and "/modules/" in target:
                        card = mirror(f"../steps/{document_route}{module_number:02d}.md", language)
                    else:
                        card = mirror(f"../instructions/{unit_id}.md", language)
                    continuation = f"[{unit_id}]({card})"
                else:
                    continuation = self.lookup_text(
                        self.instruction_lookup(unit_id, owner_node, language)
                    )
            continuations[raw] = continuation
            report[target] = continuation
        return self.clean_text(text, continuations), report

    def closure(
        self,
        roots: list[str],
        language: str,
        profile: str = "codex",
        *,
        phase: str = "common",
        include_hard_constraints: bool = True,
        document_route: str | None = None,
    ) -> dict[str, Any]:
        # An atomic instruction owns its current actions, guards, evidence and
        # failure boundary. A linked independent policy is a statically bound
        # instruction continuation, never an invitation to find author files.
        seen: set[str] = set()
        pending = list(roots)
        texts: list[str] = []
        continuations_report: dict[str, str] = {}
        while pending:
            path = pending.pop(0)
            if path in seen:
                continue
            seen.add(path)
            text = self.operational_source(path, profile)
            rendered, refs = self.render_text(path, text, language, profile, document_route)
            continuations_report.update(refs)
            texts.append(rendered)
        preface = (
            "Apply the current instruction and its included policy sections below. "
            "The current actions, guards, evidence and failure boundary are given directly. "
            "Before applying a named independent policy, obtain its exact "
            "instruction continuation; "
            "reuse any already held unit from this build and retain the affected action's "
            "return position. "
            "Do not retrieve author files or infer omitted policy. "
            "Check current facts and authorization before effects; an instruction is not a pass."
            if language == "en"
            else "下列直接给出当前动作、守卫、证据和失败边界。"
            "应用独立政策前，先按明确的指令继续入口取得对应单元；"
            "同一构建中已持有的单元直接复用，并保留受影响动作的准确恢复位置。不读取作者文件或推测缺失政策。"
            "执行副作用前核实当前事实与授权；指令内容可用不表示检查通过。"
        )
        hard_ids: list[str] = []
        if include_hard_constraints:
            hard_path = mirror("SKILL.md", language) + (
                "#Hard constraints" if language == "en" else "#硬约束"
            )
            hard = self.closure(
                [hard_path],
                language,
                profile,
                include_hard_constraints=False,
                document_route=document_route,
            )
            texts.insert(0, hard["text"].partition("\n\n")[2])
            hard_ids = hard["instruction_ids"]
        if any("layer-04-workflows/coding-" in path for path in roots):
            context_note = (
                "## Outer route scheduling context\n\nThe selector states entry prerequisites. "
                "Before initial route entry complete missing prerequisites; after entry verify "
                "held current pass evidence without replaying gates or prompts. "
                "The selected route below "
                "owns cross-module returns. Resume only the recorded caller/substep after producer "
                "readback and epoch/effect checks; the current module body does not "
                "replace this schedule."
                if language == "en"
                else "## 外层路线调度上下文\n\n选择器声明入口前置条件：首次进入路线前补齐缺项，"
                "进入后核验已持有的当前通过证据，不重放门禁或提示。下列已选路线负责跨模块返回；"
                "生产者读回及 epoch/副作用检查后，仅恢复已记录调用方子步骤。"
                "当前模块正文不替代该调度。"
            )
            texts.insert(1 if include_hard_constraints else 0, context_note)
        text = preface + "\n\n" + "\n\n".join(texts)
        if len(text) > self.max_chars:
            raise CompilationError(
                f"complete instruction exceeds approved bound for {roots}: "
                f"{len(text)} > {self.max_chars}"
            )
        ids = sorted({self.source_identity(path) for path in seen} | set(hard_ids))
        key = f"{language}:{profile}:" + ",".join(roots)
        self.report["closures"][key] = {
            "sources": sorted(seen),
            "characters": len(text),
            "continuations": continuations_report,
        }
        return {"text": text, "content_sha256": digest(text), "instruction_ids": ids}

    def node_path(self, node_id: str, language: str) -> str:
        node = self.node_map[node_id]
        path = node["owner_path"] if language == "en" else node["owner_mirrors"]["zh_cn"]["path"]
        result = self.source_path(path)
        if "layer-01-fundamental-concepts/" in result or result in {"SKILL.md", "SKILL_zh_cn.md"}:
            section = (
                node["owner_section"]
                if language == "en"
                else node["owner_mirrors"]["zh_cn"]["section"]
            )
            result += "#" + section
        return result

    def fragment_roots(self, fragment_id: str, language: str) -> list[str]:
        seen: set[str] = set()
        roots: list[str] = []

        def visit(key: str) -> None:
            if key in seen:
                return
            seen.add(key)
            if key in _SHARED_FRAGMENTS:
                spec = _SHARED_FRAGMENTS[key]
                heading = spec["section_en"] if language == "en" else spec["section_zh_cn"]
                roots.append(mirror(spec["path"], language) + "#" + heading)
                return
            fragment = self.fragment_map[key]
            owner = _OPTIONAL.get(key)
            extra = _EXTRA_FRAGMENTS.get(key)
            if extra:
                path = mirror(
                    "references/coding/layer-01-fundamental-concepts/" + extra[1], language
                )
            else:
                path = (
                    mirror(
                        "references/coding/layer-01-fundamental-concepts/" + _POLICIES[owner],
                        language,
                    )
                    if owner
                    else self.node_path(fragment["node_id"], language)
                )
                if owner:
                    section = (
                        fragment["section_en"] if language == "en" else fragment["section_zh_cn"]
                    )
                    path += "#" + section
                elif "#" not in path:
                    section = (
                        fragment["section_en"] if language == "en" else fragment["section_zh_cn"]
                    )
                    path += "#" + section
            if path not in roots:
                roots.append(path)
            for dependency in fragment.get("dependencies", []):
                visit(dependency)

        visit(fragment_id)
        return roots

    def route_stage_parts(self, route_path: str, language: str, number: int) -> dict[str, str]:
        source = self.read_source(route_path)
        checklist_heading = "Ordered route checklist" if language == "en" else "路线顺序检查清单"
        checklist = extract_heading(source, checklist_heading).partition("\n")[2].strip()
        checkpoints = list(re.finditer(r"(?m)^([1-7])\. \*\*(?:SM|MM)\d{2}\b", checklist))
        if [int(match[1]) for match in checkpoints] != list(range(1, 8)):
            raise CompilationError("route does not declare the seven ordered stage actions")
        start = checkpoints[number - 1].start()
        end = checkpoints[number].start() if number < 7 else len(checklist)
        return_heading = "Prerequisite return map" if language == "en" else "前置返回映射"
        recovery = extract_heading(source, return_heading).partition("\n")[2].strip()
        recovery_guard = re.split(r"(?m)^\|", recovery, maxsplit=1)[0].strip()
        mode = extract_heading(source, "Mode boundary" if language == "en" else "Mode 边界")
        return {
            "entry_guard": checklist[: checkpoints[0].start()].strip(),
            "current_step": checklist[start:end].strip(),
            "recovery_guard": recovery_guard,
            "mode_boundary": mode,
        }

    def critical_stage_guard(self, language: str) -> str:
        hard = extract_heading(
            self.read_source(mirror("SKILL.md", language)),
            "Hard constraints" if language == "en" else "硬约束",
        )
        bullets = [
            part.strip()
            for part in re.split(r"(?m)(?=^- )", hard)
            if part.startswith("- ") and "Computer Use" in part
        ]
        if len(bullets) != 1:
            raise CompilationError("mandatory Computer Use prohibition/stop guard is ambiguous")
        return bullets[0]

    def inline_stage_module(
        self, route_path: str, text: str, module_path: str, language: str
    ) -> str:
        references = {
            raw
            for target, _anchor, raw in self.local_links(route_path, text)
            if target == module_path
        }
        if len(references) != 1:
            raise CompilationError("current route step must identify its one inline module")
        note = (
            "the complete module provided below in this response"
            if language == "en"
            else "本响应下方已完整提供的模块"
        )
        return _LINK.sub(
            lambda match: f"{match[1]} ({note})" if match[2] in references else match[0], text
        )

    def shared_requirement(self, fragment_id: str, language: str, when: str) -> dict[str, Any]:
        return {
            "instruction_id": fragment_id,
            "when": when,
            "language": language,
            "text_sha256": f"__UNIT_HASH_{fragment_id}_{language}__",
            "reuse": "only_exact_held_unit_from_current_build_and_matching_hash",
            "lookup": self.instruction_lookup(
                fragment_id, _SHARED_FRAGMENTS[fragment_id]["node_id"], language
            ),
        }

    def document_integrity_notice(self, paths: list[str], language: str, manifest_href: str) -> str:
        entries = ", ".join(f'`manifest.files["{path}"]`' for path in paths)
        return (
            f"Document-only integrity: use the [Skill manifest]({manifest_href}). "
            "Its `manifest.build_id` must match the entry's Build and any held batch identity. "
            f"Verify {entries} against SHA-256 of each complete file's bytes, including its "
            "heading, language links and final newline. For other followed cards, use their "
            "exact paths relative to the Skill root in `manifest.files`. "
            "MCP `fragment.text_sha256` hashes the returned instruction body; it is not a "
            "document file hash. Never interchange these hashes. Missing batch evidence, "
            "manifest entries or matching content blocks dependent work and held-unit reuse."
            if language == "en"
            else f"纯文档完整性：使用 [Skill 清单]({manifest_href})。"
            "`manifest.build_id` 必须与入口 Build 及已持有的构建批次身份一致。"
            f"按 {entries} 核对各完整文件字节的 SHA-256，包括标题、语言链接和末尾换行。"
            "其它沿链接取得的卡片，使用其相对 Skill 根目录的准确路径查找 `manifest.files`。"
            "MCP `fragment.text_sha256` 是返回指令正文的哈希，不是文档文件哈希，两者不得混用。"
            "批次证据、清单条目或匹配内容缺失时，阻塞依赖工作及已持有单元的复用。"
        )

    def compile_stage(
        self,
        route: str,
        prefix: str,
        route_path: str,
        module_path: str,
        language: str,
        number: int,
        profile: str = "codex",
    ) -> dict[str, Any]:
        stage_id = _STAGES[number - 1][0]
        module = self.closure(
            [module_path],
            language,
            profile,
            phase=stage_id,
            include_hard_constraints=False,
            document_route=prefix,
        )
        parts = self.route_stage_parts(route_path, language, number)
        texts = []
        for name, source in parts.items():
            if name == "current_step":
                source = self.inline_stage_module(route_path, source, module_path, language)
            rendered, _refs = self.render_text(route_path, source, language, profile, prefix)
            texts.append((name, rendered))
        hard = self.shared_requirement("common.hard_constraints", language, "before_any_action")
        recovery = self.shared_requirement(
            f"route.{route}.return_map", language, "needs_prerequisite"
        )
        if profile == "documents":
            hard_card = mirror("../instructions/common.hard_constraints.md", language)
            return_card = mirror(f"../instructions/route.{route}.return_map.md", language)
            hard_lookup = f"[common.hard_constraints]({hard_card})"
            return_lookup = f"[route.{route}.return_map]({return_card})"
        else:
            hard_lookup = self.lookup_text(hard["lookup"])
            return_lookup = self.lookup_text(recovery["lookup"])
        guard = (
            "Before any workflow action, obtain and apply the complete shared constraints: "
            f"{hard_lookup}. Reuse is allowed only for the exact unit actually held from the "
            "current build with its matching hash; do not infer availability from a caller "
            "assertion. This response does not authorize effects or pass a gate. Missing, "
            "incompatible or unavailable required instructions block dependent work; "
            "do not infer policy or read author sources.\n\n"
            "If a prerequisite is missing, stop the dependent action and obtain its producer "
            f"mapping: {return_lookup}. Retain the original caller/substep, completed effects "
            "and nested continuation. Resume only after producer readback and current "
            "epoch/effect checks; do not replay gates or effects. A next-stage label applies only "
            "after current checks complete and no return is pending."
            if language == "en"
            else f"执行任何工作流动作前，先取得并应用完整共享约束：{hard_lookup}。"
            "只有实际已持有当前构建的准确单元且哈希匹配时才能复用；"
            "不得仅凭调用方声明假定内容可用。本响应不授权副作用，也不通过门禁。必需指令缺失、不兼容或不可用时阻塞依赖工作，"
            "不推断政策、不读取作者源。\n\n"
            f"缺少前置时，先停止依赖动作并取得生产者映射：{return_lookup}。保留原调用方子步骤、已完成副作用与嵌套继续位置；"
            "只有生产者读回及当前 epoch/副作用检查完成后才能原位恢复，不重放门禁或副作用。"
            "下一阶段标签只在当前检查完成且无待返回时适用。"
        )
        chunks = [guard, self.critical_stage_guard(language)]
        if profile == "documents":
            chunks.insert(
                1,
                self.document_integrity_notice(
                    [
                        mirror(f"steps/{prefix}{number:02d}.md", language),
                        mirror("instructions/common.hard_constraints.md", language),
                        mirror(f"instructions/route.{route}.return_map.md", language),
                    ],
                    language,
                    "../manifest.json",
                ),
            )
        chunks.extend(text for _name, text in texts)
        chunks.append(module["text"])
        text = "\n\n".join(chunks)
        if len(text) > self.max_chars:
            raise CompilationError(f"complete stage exceeds approved bound: {stage_id}")
        ids = set(module["instruction_ids"])
        ids.add("common.critical_guards")
        ids.update(f"route.{route}.{name}.{number:02d}" for name in parts)
        return {
            "module_id": f"{prefix}{number:02d}",
            "text": text,
            "content_sha256": digest(text),
            "instruction_ids": sorted(ids),
            "next_stage": _STAGES[number][0] if number < len(_STAGES) else None,
            "next_stage_condition": "current_checks_complete_and_no_return_pending",
            "shared_requirements": [hard, recovery],
        }

    def policies(self) -> dict[str, Any]:
        result = {}
        for owner, relative in _POLICIES.items():
            result[owner] = {}
            for language in LANGUAGES:
                path = mirror(
                    "references/coding/layer-01-fundamental-concepts/" + relative, language
                )
                original = self.read_source(path)
                full = self.closure([path], language, phase=_SOURCE_PHASE.get(owner, "common"))
                sections = {}
                choices = {}
                for english, chinese in _ALIASES.items():
                    title = english if language == "en" else chinese
                    try:
                        section = extract_heading(original, title)
                    except CompilationError:
                        continue
                    sections[english] = self.clean_text(section)
                    if "choice descriptions" in english:
                        entries = {}
                        for heading in _HEADING.finditer(section):
                            if len(heading[1]) == 4:
                                entries[heading[2]] = self.clean_text(
                                    extract_heading(section, heading[2])
                                )
                        choices[english] = entries
                if sections:
                    policy_text = "\n\n".join(sections.values()).strip()
                    full = {
                        "text": policy_text,
                        "content_sha256": digest(policy_text),
                        "instruction_ids": full["instruction_ids"],
                    }
                result[owner][language] = {**full, "sections": sections, "choices": choices}
        return result

    def compile(self) -> tuple[dict[str, Any], dict[str, bytes]]:
        nodes = {}
        skill_cards = {}
        for node_id in self.node_map:
            nodes[node_id] = {
                language: self.closure(
                    [self.node_path(node_id, language)], language, phase=_NODE_PHASE[node_id]
                )
                for language in LANGUAGES
            }
            for language in LANGUAGES:
                card = self.closure([self.node_path(node_id, language)], language, "documents")
                skill_cards[mirror(f"instructions/checkpoint.{node_id}.md", language)] = card[
                    "text"
                ]
        fragments = {}
        for fragment_id in self.fragment_map:
            fragments[fragment_id] = {}
            for language in LANGUAGES:
                phase = (
                    _EXTRA_FRAGMENTS[fragment_id][2]
                    if fragment_id in _EXTRA_FRAGMENTS
                    else _NODE_PHASE[self.fragment_map[fragment_id]["node_id"]]
                )
                item = self.closure(
                    self.fragment_roots(fragment_id, language),
                    language,
                    phase=phase,
                    include_hard_constraints=fragment_id not in _SHARED_FRAGMENTS,
                )
                if fragment_id in _SHARED_FRAGMENTS:
                    item["instruction_ids"] = sorted(set(item["instruction_ids"]) | {fragment_id})
                    shared_card = self.closure(
                        self.fragment_roots(fragment_id, language),
                        language,
                        "documents",
                        include_hard_constraints=False,
                    )
                    skill_cards[mirror(f"instructions/{fragment_id}.md", language)] = shared_card[
                        "text"
                    ]
                item["text_sha256"] = item.pop("content_sha256")
                fragments[fragment_id][language] = item
        routes = {}
        for route, prefix in (("single_agent", "SM"), ("multi_agent", "MM")):
            routes[route] = {}
            for language in LANGUAGES:
                route_name = (
                    "coding-single-agent" if route == "single_agent" else "coding-multi-agent"
                )
                route_path = mirror(
                    f"references/coding/layer-04-workflows/{route_name}.md", language
                )
                selector_path = mirror("workflows/coding.md", language)
                scheduler_roots = [selector_path, route_path]
                self.register_unit(selector_path)
                self.register_unit(route_path)
                entry = self.closure(scheduler_roots, language)
                route_card = self.closure(
                    scheduler_roots, language, "documents", document_route=prefix
                )
                skill_cards[mirror(f"routes/{route_name}.md", language)] = route_card["text"]
                stages = {}
                for number, (stage_id, module) in enumerate(_STAGES, 1):
                    if stage_id == "execution" and route == "multi_agent":
                        module = "delegated-execution"
                    path = mirror(
                        "references/coding/layer-04-workflows/modules/" + module + ".md", language
                    )
                    item = self.compile_stage(route, prefix, route_path, path, language, number)
                    stages[stage_id] = item
                    card = self.compile_stage(
                        route, prefix, route_path, path, language, number, "documents"
                    )
                    next_number = number + 1
                    continuation = (
                        (
                            "After this step's checks pass, continue to "
                            f"[{prefix}{next_number:02d}]({prefix}{next_number:02d}.md)."
                            if language == "en"
                            else "本步骤检查通过后，继续 "
                            f"[{prefix}{next_number:02d}]({prefix}{next_number:02d}_zh_cn.md)。"
                        )
                        if number < len(_STAGES)
                        else (
                            "Finish only after this step's Acceptance conditions pass."
                            if language == "en"
                            else "仅在本步骤验收条件通过后结束。"
                        )
                    )
                    skill_cards[mirror(f"steps/{prefix}{number:02d}.md", language)] = (
                        card["text"] + "\n\n" + continuation
                    )
                routes[route][language] = {"entry": entry, "stages": stages}
        registry = json.loads(json.dumps(self.registry))
        for node in registry["nodes"]:
            node["owner_path"] = f"compiled:{node['node_id']}:en"
            node["owner_section"] = "Compiled executable instructions"
            node["owner_mirrors"] = {
                "zh_cn": {
                    "path": f"compiled:{node['node_id']}:zh_cn",
                    "section": "编译后的可执行指令",
                }
            }
            node.pop("resource_paths", None)
        policies = self.policies()
        processed_units: set[str] = set()
        while set(self.units) - processed_units:
            unit_id = sorted(set(self.units) - processed_units)[0]
            path, node_id = self.units[unit_id]
            fragments[unit_id] = {}
            for language in LANGUAGES:
                source = mirror(path, language)
                item = self.closure([source], language)
                item["text_sha256"] = item.pop("content_sha256")
                fragments[unit_id][language] = item
                card = self.closure([source], language, "documents")
                skill_cards[mirror(f"instructions/{unit_id}.md", language)] = card["text"]
            self.index["fragments"].append(
                {
                    "fragment_id": unit_id,
                    "node_id": node_id,
                    "section_en": "Compiled instruction unit",
                    "section_zh_cn": "编译指令单元",
                }
            )
            processed_units.add(unit_id)
        body = {
            "schema_version": SCHEMA_VERSION,
            "compiler_version": COMPILER_VERSION,
            "registry": registry,
            "context_index": self.index,
            "nodes": nodes,
            "fragments": fragments,
            "policies": policies,
            "routes": routes,
            "document_units": {path: digest(text) for path, text in sorted(skill_cards.items())},
        }
        # Include actual entry delivery text in semantic identity. Its fixed
        # build placeholder avoids hashing the eventual build ID into itself.
        normalized_files = self.skill_files(skill_cards, "__BUILD_ID__")
        for entry in ("SKILL.md", "SKILL_zh_cn.md"):
            body["document_units"][entry] = digest(normalized_files[entry])
        self.resolve_budgets(body)
        body["build_id"] = digest(canonical(body))
        skill_files = self.skill_files(skill_cards, body["build_id"])
        body["skill_files"] = {
            path: digest(data)
            for path, data in sorted(skill_files.items())
            if path != "manifest.json"
        }
        return body, skill_files

    def resolve_budgets(self, body: dict[str, Any]) -> None:
        fragment_nodes = {item["fragment_id"]: item["node_id"] for item in self.index["fragments"]}
        budgets = {}
        for unit_id, localized in body["fragments"].items():
            for language, item in localized.items():
                required = (
                    len(item["text"])
                    + len(body["nodes"][fragment_nodes[unit_id]][language]["text"])
                    + 512
                )
                if required > 60000:
                    raise CompilationError(
                        f"instruction continuation exceeds tool bound: {unit_id}"
                    )
                budgets[f'"__BUDGET_{unit_id}_{language}__"'] = str(required)

        def resolve(value: Any) -> Any:
            if isinstance(value, str):
                if '"' + value + '"' in budgets:
                    return int(budgets['"' + value + '"'])
                for token, size in budgets.items():
                    value = value.replace(token, size)
                if "__BUDGET_" in value:
                    raise CompilationError("unresolved instruction continuation budget")
                return value
            if isinstance(value, list):
                return [resolve(item) for item in value]
            if isinstance(value, dict):
                result = {key: resolve(item) for key, item in value.items()}
                if "text" in result:
                    if "content_sha256" in result:
                        result["content_sha256"] = digest(result["text"])
                    if "text_sha256" in result:
                        result["text_sha256"] = digest(result["text"])
                return result
            return value

        resolved = resolve(body)
        unit_hashes = {
            f"__UNIT_HASH_{fragment_id}_{language}__": localized[language]["text_sha256"]
            for fragment_id, localized in resolved["fragments"].items()
            for language in LANGUAGES
        }

        def bind_hashes(value: Any) -> Any:
            if isinstance(value, str):
                for token, fingerprint in unit_hashes.items():
                    value = value.replace(token, fingerprint)
                if "__UNIT_HASH_" in value:
                    raise CompilationError("unresolved shared instruction identity")
                return value
            if isinstance(value, list):
                return [bind_hashes(item) for item in value]
            if isinstance(value, dict):
                return {key: bind_hashes(item) for key, item in value.items()}
            return value

        resolved = bind_hashes(resolved)
        body.clear()
        body.update(resolved)

    def skill_files(self, cards: dict[str, str], build_id: str) -> dict[str, bytes]:
        files: dict[str, bytes] = {}
        for path, text in cards.items():
            language = "zh_cn" if path.endswith("_zh_cn.md") else "en"
            peer = (
                path.removesuffix("_zh_cn.md") + ".md"
                if language == "zh_cn"
                else mirror(path, "zh_cn")
            )
            english_name = Path(peer if language == "zh_cn" else path).name
            chinese_name = Path(path if language == "zh_cn" else peer).name
            switch = f"[English]({english_name}) | [简体中文]({chinese_name})"
            files[path] = (f"# {Path(path).stem}\n\n{switch}\n\n{text}\n").encode()
        for language in LANGUAGES:
            name = "SKILL.md" if language == "en" else "SKILL_zh_cn.md"
            intro = (
                "This generated Skill delivers executable Coding instructions. "
                "Record the task goal, "
                "authorized effects, constraints and acceptance criteria; verify available "
                "capabilities; then confirm the conversation's released execution mode. "
                "Missing facts or permission block only dependent actions. "
                "Computer Use is forbidden. Never treat a compiled instruction or hash as "
                "authorization or completion evidence."
                "\n\nAfter these entry gates pass, consume Route Entry and open only the route "
                "identified by its authorized result below. "
                "Follow its seven steps in order; the next step is explicit, so do not search "
                "the author policy tree. Each step directly provides its current actions, "
                "guards, evidence and failure/return boundaries. Obtain and apply the "
                "same-build shared constraints before any action, and each exact independent "
                "instruction continuation when its condition applies; these units are not all "
                "inlined into the step. Persist the shared task plan before "
                "implementation; preserve plan history. A failed prerequisite resumes at the exact "
                "suspended action after current evidence is obtained. Verification checks actual "
                "current state; changed epochs return to verification. Optional operations require "
                "an explicit Not applicable reason when omitted."
                if language == "en"
                else "本生成 Skill 交付可执行的 Coding 指令。"
                "先记录任务目标、授权副作用、约束与验收标准，核实可用能力，"
                "再确认当前会话已释放的执行模式。缺事实或权限时停止依赖动作。"
                "禁止 Computer Use。编译指令或 hash 不代表授权或完成证据。"
                "\n\n入口条件通过后，先消费 Route Entry，只打开其授权结果所指明的下列路线，"
                "按七步依次执行。"
                "下一步明确给出，不查找作者政策树。每步直接提供当前动作、守卫、证据和失败返回边界；"
                "执行任何动作前先取得并应用同一构建的共享约束，独立政策条件触发时先消费其准确指令继续入口，"
                "这些单元并未全部内联到步骤正文。"
                "实施前持久化共享任务计划并保留历史；前置失败时取得当前证据后只恢复准确暂停动作。"
                "验证实际当前状态，状态代际变化后返回重验；"
                "未采用条件操作时记录明确 Not applicable 理由。"
            )
            lines = [
                "---",
                "name: token-io-decoupling",
                'description: "Execute Coding tasks with bounded, compiled instructions | '
                '使用有界编译指令执行 Coding 任务"',
                "---",
                "",
                "# Token I/O Decoupling",
                "",
                "[English](SKILL.md) | [简体中文](SKILL_zh_cn.md)",
                "",
                intro,
                "",
                self.closure(
                    [
                        mirror("SKILL.md", language)
                        + ("#Hard constraints" if language == "en" else "#硬约束")
                    ],
                    language,
                    "documents",
                    include_hard_constraints=False,
                )["text"]
                .partition("\n\n")[2]
                .replace("](../instructions/", "](instructions/"),
                "",
                f"Build: `{build_id}`",
                "",
                self.document_integrity_notice([name], language, "manifest.json"),
                "",
            ]
            contract_card = mirror("instructions/checkpoint.contract.md", language)
            mode_card = mirror("instructions/checkpoint.mode.md", language)
            environment_id, _ = self.register_unit(
                "references/coding/layer-02-workflow-concepts/entry-and-context/environment.md"
            )
            capabilities_id, _ = self.register_unit(
                "references/coding/layer-02-workflow-concepts/entry-and-context/environment-capability-inventory.md"
            )
            environment_card = mirror(f"instructions/{environment_id}.md", language)
            capabilities_card = mirror(f"instructions/{capabilities_id}.md", language)
            route_entry_id, _ = self.register_unit(
                "references/coding/layer-03-workflow-checkpoints/route-entry.md"
            )
            route_entry_card = mirror(f"instructions/{route_entry_id}.md", language)
            lines.append(
                f"Entry: [Contract]({contract_card}) → [Environment]({environment_card}) → "
                f"[Capability inventory]({capabilities_card}) → [Mode]({mode_card}) → "
                f"[Route Entry]({route_entry_card}). Only Route Entry's current result selects "
                "the authorized route; the menu and default remain owned by Mode."
                if language == "en"
                else f"入口：[Contract]({contract_card}) → [Environment]({environment_card}) → "
                f"[能力清单]({capabilities_card}) → [Mode]({mode_card}) → "
                f"[Route Entry]({route_entry_card})。仅按 Route Entry 的当前结果选择授权路线；"
                "菜单和默认值仍由 Mode 负责。"
            )
            lines.extend(
                [
                    "",
                    "MCP: local Codex CLI only. When this server is available and authorized, "
                    "prefer its public tools: start with `workflow_capabilities`, then "
                    "`rules_get_context` with `node_id=contract` and `context_version=2`. "
                    "Use `decide_decoupling_workflow` with an explicit `stage` and its required "
                    "locked-mode and current-fact inputs for bounded stage instructions. "
                    "Consume returned shared requirements and exact continuations before "
                    "dependent actions. Other Agents use this document-only Skill without "
                    "the server; follow the generated links and manifest checks below. "
                    "Neither path requires author sources."
                    if language == "en"
                    else "MCP 仅支持本地 Codex CLI。此 Server 可用且已获授权时，"
                    "优先使用其公开工具："
                    "先调用 `workflow_capabilities`，再以 `node_id=contract`、`context_version=2` "
                    "调用 `rules_get_context`；取得有界阶段指令时，使用明确 `stage` "
                    "以及其必需的已锁定模式和当前事实输入，调用 `decide_decoupling_workflow`。"
                    "依赖动作前先消费返回的共享要求及准确指令继续入口。"
                    "其它 Agent 不使用此 Server，而按下列生成链接与清单核对使用纯文档 Skill；"
                    "两种路径均不需要作者源。",
                    "",
                ]
            )
            for route, prefix in (("Single-Agent", "SM"), ("Multi-Agent", "MM")):
                lines.extend([f"## {route}", ""])
                route_name = "coding-single-agent" if prefix == "SM" else "coding-multi-agent"
                route_card = mirror(f"routes/{route_name}.md", language)
                lines.append(
                    f"Read the [complete route scheduling and return map]({route_card}) "
                    "before following its steps."
                    if language == "en"
                    else f"按步骤执行前，先消费[完整路线调度与返回映射]({route_card})。"
                )
                lines.append("")
                for number, (stage_id, _module) in enumerate(_STAGES, 1):
                    path = mirror(f"steps/{prefix}{number:02d}.md", language)
                    lines.append(f"{number}. [{prefix}{number:02d}: {stage_id}]({path})")
                lines.append("")
            files[name] = ("\n".join(lines).rstrip() + "\n").encode()
        files["agents/openai.yaml"] = (
            'interface:\n  display_name: "Token I/O Decoupling"\n'
            '  short_description: "Compiled Coding instructions | Coding 编译指令"\n'.encode()
        )
        manifest = {
            "schema_version": SCHEMA_VERSION,
            "build_id": build_id,
            "files": {path: digest(data) for path, data in sorted(files.items())},
        }
        files["manifest.json"] = json_bytes(manifest)
        return files


def deterministic_zip(files: dict[str, bytes]) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path, data in sorted(files.items()):
            info = zipfile.ZipInfo(path, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    return output.getvalue()


def compile_repository(
    root: Path, *, check: bool = False, max_chars: int = MAX_INSTRUCTION_CHARS
) -> dict[str, Any]:
    compiler = Compiler(root, max_chars=max_chars)
    body, skill_files = compiler.compile()
    resource = Path("mcp/packages/token_io_decoupling_core/src/token_io_decoupling_core/_resources")
    instructions = json_bytes(body)
    files = {
        resource / "instructions.json": instructions,
        resource / "manifest.json": json_bytes(
            {
                "schema_version": SCHEMA_VERSION,
                "build_id": body["build_id"],
                "files": {"instructions.json": digest(instructions)},
            }
        ),
        Path("instruction-compiler/build-report.json"): json_bytes(
            {"build_id": body["build_id"], **compiler.report}
        ),
    }
    skill_root = root / "skills/token-io-decoupling"
    export_present = skill_root.exists() or skill_root.is_symlink()
    if export_present and (skill_root.is_symlink() or not skill_root.is_dir()):
        raise CompilationError("optional Skill export must be a regular directory")
    if not check or export_present:
        files.update(
            {Path("skills/token-io-decoupling") / path: data for path, data in skill_files.items()}
        )
    files[Path("mcp/src/token_io_decoupling/_resources/skill_bundle.zip")] = deterministic_zip(
        skill_files
    )
    stale = [
        path.as_posix()
        for path, data in files.items()
        if not (root / path).is_file() or (root / path).read_bytes() != data
    ]
    if export_present:
        expected = {Path(path) for path in skill_files}
        stale.extend(
            (Path("skills/token-io-decoupling") / path.relative_to(skill_root)).as_posix()
            for path in skill_root.rglob("*")
            if path.is_file() and path.relative_to(skill_root) not in expected
        )
    if check and stale:
        raise CompilationError("generated instruction resources are stale: " + ", ".join(stale))
    if not check:
        for path, data in files.items():
            destination = root / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
    return {
        "build_id": body["build_id"],
        "generated_files": len(files),
        "resource_bytes": len(instructions),
        "instruction_characters": {
            key: {language: len(value[language]["text"]) for language in LANGUAGES}
            for key, value in body["nodes"].items()
        },
        "stage_characters": {
            route: {
                language: {
                    stage: len(value["text"])
                    for stage, value in localized[language]["stages"].items()
                }
                for language in LANGUAGES
            }
            for route, localized in body["routes"].items()
        },
    }


def main(argv: list[str] | None = None) -> int:
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

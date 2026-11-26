#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["jsonschema==4.26.0", "ruamel.yaml==0.19.1"]
# ///
"""从 rules 编译可浏览的 Skill 文档。"""

from __future__ import annotations

import argparse
import json
import posixpath
import re
import sys
import unicodedata
from collections.abc import Callable, Iterable, Iterator
from pathlib import Path, PurePosixPath
from tempfile import NamedTemporaryFile
from urllib.parse import unquote

from jsonschema import Draft202012Validator, ValidationError
from ruamel.yaml import YAML, YAMLError
from ruamel.yaml.tokens import AliasToken, AnchorToken

import document_rules as COMPLIANCE
from coding_dsl_templates import DOCUMENT_TYPES, document_type, load_templates, validate_coding_document
from hook_dsl_templates import HOOK_TYPES, hook_type, load_hook_templates, validate_hook_document
from local_skill import DEFAULT_HOST, DEFAULT_NAME, HOSTS, update_local_skill
from workflow_checkpoint_lookup import NUMBERED_BLOCKS, check_flowchart_references, locate_checkpoint
from workflow_module_contracts import ROUTE_MODULES, WORKFLOW_PATH, WORKFLOW_SELECTOR

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "rules"
REFERENCES = SOURCE / "references"
CODING = REFERENCES / "coding"
ROUTES = SOURCE / WORKFLOW_PATH
TEMPLATES = SOURCE / "templates/coding"
HOOK_SOURCE = SOURCE / "hooks"
HOOK_TEMPLATES = SOURCE / "templates/hooks"
HOOK_COVERAGE = "hooks/SOURCE_COVERAGE.md"
SKILL = ROOT / "skill"
RULE_INCLUDE = re.compile(r"^<!-- rule:([a-z][a-z0-9-]*)#([A-Za-z][A-Za-z0-9-]*) -->$")
FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
INLINE_LINK = re.compile(r"(`+)[^\n]*?\1|(!?\[[^\]\n]*\]\()(<[^>\n]+>|[^\s)]+)(?=[ \t]*(?:\)|[\"']))")
REFERENCE_LINK = re.compile(r"^( {0,3}\[[^\]\n]+\]:[ \t]*)(<[^>\n]+>|[^\s]+)(?=[ \t]|$)")
EXTERNAL_LINK = re.compile(r"^(?:[a-z][a-z0-9+.-]*:|//)", re.I)


def source_bytes(path: Path) -> bytes:
    if path.resolve() != path:
        raise ValueError(f"规则源不允许符号链接：{path.relative_to(ROOT)}")
    return path.read_bytes()


def read_rule(path: Path, text: str, validator: Draft202012Validator) -> dict:
    yaml = YAML(typ="safe", pure=True)
    if any(isinstance(token, (AliasToken, AnchorToken)) for token in yaml.scan(text)):
        raise ValueError(f"{path.name} 不允许 YAML 锚点或别名")
    document = yaml.load(text)
    try:
        validator.validate(document)
    except ValidationError as error:
        raise ValueError(f"{path.name} {error.json_path}: {error.message}") from error
    expected = path.relative_to(SOURCE).with_suffix(".md").as_posix()
    if document["markdown_path"] != expected:
        raise ValueError(f"{path.relative_to(ROOT)} 的 Markdown 路径应为 {expected}")
    return document


def heading_anchor(title: str, counts: dict[str, int]) -> str:
    label = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", title)
    label = re.sub(r"<[^>]*>", "", label).lower()
    base = "".join(char for char in label if char in "_-" or char.isspace() or unicodedata.category(char)[0] in "LNM")
    base = base.replace(" ", "-")
    count = counts.get(base, 0)
    counts[base] = count + 1
    return f"{base}-{count}" if count else base


def render_blocks(
    blocks: list[dict], level: int, seen: set[str], fragments: dict[str, str | None], heading_counts: dict[str, int],
    anchors: dict[str, str] | None = None,
) -> str:
    parts = []
    previous = None
    number = 0
    for entry in blocks:
        block_id, block = next(iter(entry.items()))
        if block_id in seen:
            raise ValueError(f"重复块 ID：{block_id}")
        seen.add(block_id)
        kind = block["kind"]
        if parts:
            default_gap = 0 if previous == kind and kind in NUMBERED_BLOCKS else 1
            parts.append("\n" * (1 + block.get("blank_lines_before", default_gap)))
        expose = kind in NUMBERED_BLOCKS or block.get("expose")
        if expose:
            fragments[block_id] = None
        if kind == "section":
            if level > 6:
                raise ValueError(f"标题层级超过 Markdown 上限：{block_id}")
            anchor = heading_anchor(block["title"], heading_counts)
            if expose:
                fragments[block_id] = anchor
            if anchors is not None:
                anchors[block_id] = anchor
            body = render_blocks(block["blocks"], level + 1, seen, fragments, heading_counts, anchors)
            parts.append(f"{'#' * level} {block['title']}\n\n{body}")
        elif kind == "rule_include":
            parts.append(f"<!-- rule:{block['document']}#{block['fragment']} -->")
        else:
            body = block["text"].rstrip("\n")
            if not body.strip():
                raise ValueError(f"正文为空：{block_id}")
            if kind in NUMBERED_BLOCKS:
                number = number + 1 if previous == kind else 1
                indent = " " * (len(str(number)) + 2)
                first, *rest = body.split("\n")
                parts.append(f"{number}. **{block_id} — {block['title']}** {first}")
                parts.extend(f"\n{indent}{line}" if line else "\n" for line in rest)
            else:
                parts.append(body)
        if kind == "route_step":
            hook = block["hook"]
            if f"](../hooks/{hook}.yaml)" not in body:
                raise ValueError(f"路线项 {block_id} 的 Hook 与 DSL 链接不一致：{hook}")
        previous = kind
    return "".join(parts)


def map_markdown_links(markdown: str, rewrite: Callable[[str], str]) -> str:
    def destination(prefix: str, href: str) -> str:
        if href.startswith("<"):
            return prefix + "<" + rewrite(href[1:-1]) + ">"
        return prefix + rewrite(href)

    lines = []
    fence = ""
    for line in markdown.split("\n"):
        marker = FENCE.match(line)
        if fence:
            if marker and marker[1][0] == fence[0] and len(marker[1]) >= len(fence) and not line[marker.end():].strip():
                fence = ""
        elif marker:
            fence = marker[1]
        else:
            line = INLINE_LINK.sub(lambda match: match[0] if match[1] else destination(match[2], match[3]), line)
            line = REFERENCE_LINK.sub(lambda match: destination(match[1], match[2]), line)
        lines.append(line)
    return "\n".join(lines)


def check_dsl_dependencies(path: str, markdown: str) -> None:
    source = PurePosixPath(path)
    for line, _, href in COMPLIANCE.links_in_markdown(markdown):
        if COMPLIANCE.reverse_dependency_target(source, href) is not None:
            raise ValueError(f"DSL 反向依赖：{path}:{line} -> {href}")


def render_dsl_links(path: str, markdown: str, targets: dict[str, dict[str, str]]) -> str:
    check_dsl_dependencies(path, markdown)

    def rewrite(href: str) -> str:
        if EXTERNAL_LINK.match(href):
            return href
        before_hash, has_fragment, fragment = href.partition("#")
        target, query_mark, query = before_hash.partition("?")
        resolved = posixpath.normpath(posixpath.join(posixpath.dirname(path), unquote(target)))
        if path.startswith("references/") and resolved.startswith("hooks/"):
            raise ValueError(f"参考规则不能引用 Hook：{path} -> {href}")
        rule_path = resolved.startswith(("references/", "hooks/", f"{WORKFLOW_PATH.as_posix()}/"))
        if (rule_path and resolved.endswith(".md")) or resolved == "SKILL.md":
            raise ValueError(f"DSL 内部引用须指向 YAML：{path} -> {href}")
        if not target.endswith(".yaml"):
            return href
        anchors = targets.get(resolved.removesuffix(".yaml") + ".md")
        if anchors is None:
            raise ValueError(f"DSL 引用目标不存在：{path} -> {href}")
        if has_fragment:
            anchor = anchors.get(unquote(fragment))
            if not anchor:
                raise ValueError(f"DSL 引用缺少可导出的章节：{path} -> {href}")
            fragment = anchor
        return target.removesuffix(".yaml") + ".md" + query_mark + query + has_fragment + fragment

    return map_markdown_links(markdown, rewrite)


def compile_hooks(
    fragment_ids: dict[str, set[str]], targets: dict[str, dict[str, str]], outputs: dict[Path, str],
    reference_layers: dict[str, str | None], source_documents: dict[Path, dict],
) -> None:
    markdown = {}
    bodies = {}
    targets[HOOK_COVERAGE] = {}
    for path, document in read_hook_documents():
        source_documents[path] = document
        target = document["markdown_path"]
        anchors: dict[str, str] = {}
        counts: dict[str, int] = {}
        heading_anchor(document["title"], counts)
        body = render_blocks(document["blocks"], 2, set(), {}, counts, anchors)
        if "\0" in body or "\0" in document["title"]:
            raise ValueError(f"Hook 文档包含 NUL：{path.name}")
        heading = f"# {document['title']}"
        gap = "\n" * document.get("blank_lines_after_title", 2)
        provenance = source_notice(path)
        markdown[target] = f"{heading}\n\n{provenance}{gap}{body}\n"
        targets[target] = anchors
        if f"hook-{document['id']}" in fragment_ids:
            raise ValueError(f"Hook 与参考规则的文档 ID 重复：{document['id']}")
        if document["document_type"] == "hook-contract":
            execution_blocks = [entry for entry in document["blocks"]
                                if next(iter(entry)) not in {"flowchart", "checkpoints", "sources"}]
            execution = render_blocks(execution_blocks, 2, set(), {}, {})
            bodies[target] = f"{heading}{gap}{execution}\n"
    for path, content in markdown.items():
        outputs[SKILL / path] = render_dsl_links(path, content, targets)
    for path, content in bodies.items():
        body = render_dsl_links(path, content, targets)
        for line in body.splitlines():
            if "<!-- rule:" not in line:
                continue
            include = RULE_INCLUDE.fullmatch(line)
            if not include:
                raise ValueError(f"无效的 Hook 规则引用：{path}: {line}")
            document, fragment = include.groups()
            if fragment not in fragment_ids.get(document, set()):
                raise ValueError(f"Hook 引用缺少 DSL 片段：{path} -> {document}#{fragment}")
            if COMPLIANCE.is_reverse_dependency("hook", reference_layers[document]):
                raise ValueError(f"Hook 执行引用存在反向依赖：{path} -> {document}#{fragment}")


def source_notice(path: Path) -> str:
    return f"<!-- 由 {path.relative_to(ROOT).as_posix()} 生成。请在 DSL 中维护正文。 -->"


def is_retired_index(path: Path, outputs: dict[Path, str]) -> bool:
    navigation_directory = (
        path.is_relative_to(SKILL / "references") or path.parent == SKILL / WORKFLOW_PATH
    )
    if (path.name != "INDEX.md" or not navigation_directory
            or path.resolve() != path or path.with_name("README.md") not in outputs):
        return False
    source = (SOURCE / path.relative_to(SKILL)).with_suffix(".yaml")
    try:
        return source_notice(source) in path.read_text(encoding="utf-8").splitlines()[:4]
    except FileNotFoundError:
        return True


def is_moved_route(path: Path) -> bool:
    old_directory = SKILL / "coding-workflows"
    if (
        path.parent != old_directory
        or path.stem not in {"README", *ROUTE_MODULES}
        or path.resolve() != path
    ):
        return False
    old_source = SOURCE / path.relative_to(SKILL).with_suffix(".yaml")
    return source_notice(old_source) in path.read_text(encoding="utf-8").splitlines()[:4]


def is_split_lsp_reference(path: Path, outputs: dict[Path, str]) -> bool:
    directory = SKILL / "references/coding/layer-01-fundamental-concepts/session-runtime"
    if path != directory / "LSP-MCP-Tools.md" or path.resolve() != path:
        return False
    replacements = {directory / "lsp-code-navigation.md", directory / "project-memory.md"}
    if not replacements.issubset(outputs):
        return False
    old_source = SOURCE / path.relative_to(SKILL).with_suffix(".yaml")
    return source_notice(old_source) in path.read_text(encoding="utf-8").splitlines()[:4]


def read_coverage() -> dict:
    schema = json.loads((SOURCE / "hook-coverage.schema.json").read_text(encoding="utf-8"))
    path = (SOURCE / HOOK_COVERAGE).with_suffix(".yaml")
    report = read_rule(path, source_bytes(path).decode("utf-8"), Draft202012Validator(schema))
    for row in report["rows"]:
        if COMPLIANCE.reverse_dependency_target(PurePosixPath(path.relative_to(ROOT)), row["source"]):
            raise ValueError(f"Hook 来源对照存在反向依赖：{row['source']}")
    return report


def render_coverage(outputs: dict[Path, str]) -> str:
    report = read_coverage()
    lines = [
        f"# {report['title']}", "",
        source_notice((SOURCE / HOOK_COVERAGE).with_suffix(".yaml")), "",
        "本表列出 Hook 消费的规则和导航。实质文章逐篇指向引用它的合同，各合同末尾列明主题落点。路线的阶段绑定由路线索引与静态检查核对。", "",
        "表中列出的路径和显式归属供审阅时定位条款。语义等价、授权和验收仍需逐条对照权威规则与当前证据。", "",
        "| 源文档（相对 Skill） | 类型 | 合同落点或导航归属 |", "| --- | --- | --- |",
    ]
    for row in report["rows"]:
        source = row["source"]
        relative = posixpath.normpath(posixpath.join("hooks", source)).removesuffix(".yaml") + ".md"
        if not source.endswith(".yaml") or SKILL / relative not in outputs:
            raise ValueError(f"Hook 来源没有可导出的 YAML 文档：{source}")
        label = "仅参考：" if row["kind"] == "reference" else "仅导航：" if not row["explicit"] else ""
        hooks = "、".join(f"[{hook}]({hook}.md#执行要求)" for hook in row["hooks"])
        lines.append(f"| [{relative}](../{relative}) | {row['kind']} | {label}{hooks} |")
    return "\n".join(lines) + "\n"


def rule_validator() -> Draft202012Validator:
    schema = json.loads((SOURCE / "reference.schema.json").read_text(encoding="utf-8"))
    return Draft202012Validator(schema)


def read_hook_documents() -> Iterator[tuple[Path, dict]]:
    validator = rule_validator()
    templates = load_hook_templates(HOOK_TEMPLATES, validator)
    for path in sorted(HOOK_SOURCE.glob("*.yaml")):
        if path.name == "SOURCE_COVERAGE.yaml":
            continue
        document = read_rule(path, source_bytes(path).decode("utf-8"), validator)
        validate_hook_document(path, document, templates[hook_type(path)])
        yield path, document


def read_rules(paths: Iterable[Path]) -> Iterator[tuple[Path, dict]]:
    validator = rule_validator()
    templates = load_templates(TEMPLATES, validator)
    ids = {"current-route"}
    for path in sorted(paths):
        source = source_bytes(path)
        document = read_rule(path, source.decode("utf-8"), validator)
        if document["id"] in ids:
            raise ValueError(f"重复或保留的文档 ID：{path.relative_to(ROOT)}#{document['id']}")
        ids.add(document["id"])
        relative = path.relative_to(SOURCE)
        if path.is_relative_to(CODING) or (
            path.is_relative_to(ROUTES) and relative != WORKFLOW_SELECTOR
        ):
            validate_coding_document(relative, document, templates[document_type(relative)])
        yield path, document


def compile_rules() -> dict[Path, str]:
    outputs: dict[Path, str] = {}
    targets: dict[str, dict[str, str]] = {}
    reference_layers: dict[str, str | None] = {}
    source_documents = {}
    fragment_ids: dict[str, set[str]] = {}
    sources = (*REFERENCES.rglob("*.yaml"), *ROUTES.rglob("*.yaml"), SOURCE / "SKILL.yaml")
    for source_path, document in read_rules(sources):
        source_documents[source_path] = document
        document_id = document["id"]
        markdown_path = SKILL / document["markdown_path"]
        fragments: dict[str, str | None] = {}
        heading_counts: dict[str, int] = {}
        heading_anchor(document["title"], heading_counts)
        body = render_blocks(document["blocks"], 2, set(), fragments, heading_counts)
        if "<!-- rule:" in body:
            raise ValueError(f"DSL 规则正文不包含 Hook 执行引用：{source_path.relative_to(ROOT)}")
        provenance = source_notice(source_path)
        title_gap = "\n" * document.get("blank_lines_after_title", 2)
        markdown = f"# {document['title']}\n\n{provenance}\n{title_gap}{body}\n"
        if "front_matter" in document:
            metadata = document["front_matter"]
            description = json.dumps(metadata["description"], ensure_ascii=False)
            markdown = f"---\nname: {metadata['name']}\ndescription: {description}\n---\n\n{markdown}"
        outputs[markdown_path] = markdown
        fragment_ids[document_id] = set(fragments)
        path = document["markdown_path"]
        targets[path] = {key: anchor for key, anchor in fragments.items() if anchor}
        reference_layers[document_id] = COMPLIANCE.path_layer(PurePosixPath(path))
    references = tuple(targets)
    compile_hooks(fragment_ids, targets, outputs, reference_layers, source_documents)
    check_flowchart_references(source_documents)
    for path in references:
        target = SKILL / path
        outputs[target] = render_dsl_links(path, outputs[target], targets)
    outputs[SKILL / HOOK_COVERAGE] = render_coverage(outputs)
    outputs[SKILL / "agents/openai.yaml"] = source_bytes(SOURCE / "agents/openai.yaml").decode("utf-8")
    return outputs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="只检查已生成的文件是否与 DSL 一致")
    mode.add_argument("--check-structure", action="store_true", help="按模板检查 Coding 与 Hook DSL 结构")
    mode.add_argument("--install-skill", action="store_true", help="编译并首次安装本地 Skill")
    mode.add_argument("--update-skill", action="store_true", help="编译并安装或更新本地 Skill")
    mode.add_argument("--template", choices=(*DOCUMENT_TYPES, *HOOK_TYPES), help="输出指定类型的 YAML 示例")
    mode.add_argument("--locate-checkpoint", metavar="ID", help="定位检查点 ID 或文档ID#块ID")
    parser.add_argument("--from", dest="origin", metavar="文档ID", help="在指定流程图中定位节点")
    parser.add_argument("--show", action="store_true", help="定位时同时输出对应的 YAML 块内容")
    parser.add_argument("--name", help=f"指定受管理的 Skill 名称，默认 {DEFAULT_NAME}")
    parser.add_argument("--host", choices=HOSTS, help=f"选择默认 Skill 根目录，默认 {DEFAULT_HOST}")
    destination = parser.add_mutually_exclusive_group()
    destination.add_argument("--skills-dir", type=Path, help="自定义 Skill 根目录，在其下使用 --name 作为子目录")
    destination.add_argument("--project-root", type=Path, help="Codex 项目绝对目录，使用其 .agents/skills")
    args = parser.parse_args()
    publishing = args.install_skill or args.update_skill
    if not publishing and any(
        value is not None for value in (args.name, args.host, args.skills_dir, args.project_root)
    ):
        parser.error("--name、--host、--skills-dir 和 --project-root 仅用于安装或更新 Skill")
    if args.locate_checkpoint is None and (args.origin or args.show):
        parser.error("--from 和 --show 须与 --locate-checkpoint 一起使用")
    if args.origin and "#" in args.locate_checkpoint:
        parser.error("使用 --from 时请指定流程图节点 ID")
    try:
        if args.locate_checkpoint is not None:
            location = locate_checkpoint(
                ROOT, REFERENCES, HOOK_SOURCE, args.locate_checkpoint, args.origin, args.show,
            )
            print(json.dumps(location, ensure_ascii=False, indent=2))
            return 0
        if args.template:
            validator = rule_validator()
            templates = (load_hook_templates(HOOK_TEMPLATES, validator) if args.template in HOOK_TYPES
                         else load_templates(TEMPLATES, validator))
            sample = templates[args.template]["document"]
            relative = Path(sample["markdown_path"])
            print(f"# yaml-language-server: $schema={'../' * len(relative.parent.parts)}reference.schema.json")
            yaml = YAML(typ="rt")
            yaml.indent(mapping=2, sequence=4, offset=2)
            yaml.width = 120
            yaml.dump(sample, sys.stdout)
            return 0
        if args.check_structure:
            sources = (*CODING.rglob("*.yaml"), *ROUTES.rglob("*.yaml"))
            coding = dict(read_rules(sources))
            hooks = dict(read_hook_documents())
            if not coding or not hooks:
                raise ValueError("没有可校验的 Coding 或 Hook DSL")
            for document in (*coding.values(), *hooks.values()):
                markdown = render_blocks(document["blocks"], 2, set(), {}, {})
                check_dsl_dependencies(document["markdown_path"], markdown)
            check_flowchart_references(coding | hooks)
            read_coverage()
            print(f"DSL 结构校验通过，共 {len(coding)} 份 Coding 文档、{len(hooks)} 份 Hook 源文档和 1 份来源对照。")
            return 0
        outputs = compile_rules()
        if publishing:
            installed = update_local_skill(
                {path.relative_to(SKILL): body for path, body in outputs.items()},
                name=args.name if args.name is not None else DEFAULT_NAME,
                host=args.host or DEFAULT_HOST,
                project_root=args.project_root,
                skills_dir=args.skills_dir,
                install_only=args.install_skill,
            )
            action = "安装" if args.install_skill else "更新"
            print(f"Skill 已{action}：{installed}")
            return 0
        for path in outputs:
            if path.resolve() != path:
                raise ValueError(f"生成目标不允许符号链接：{path.relative_to(ROOT)}")
        outdated = [path for path, body in outputs.items() if not path.is_file() or path.read_bytes() != body.encode("utf-8")]
        unexpected = set(SKILL.rglob("*.md")) - outputs.keys()
        retired = set() if args.check else {
            path for path in unexpected
            if is_retired_index(path, outputs) or is_moved_route(path) or is_split_lsp_reference(path, outputs)
        }
        unexpected -= retired
        if unexpected or (args.check and outdated):
            for path in sorted(unexpected):
                print(f"过时的 Skill 文档 {path.relative_to(ROOT)}", file=sys.stderr)
            if args.check:
                for path in outdated:
                    print(f"请重新生成 {path.relative_to(ROOT)}", file=sys.stderr)
            return 1
        for path in outdated:
            path.parent.mkdir(parents=True, exist_ok=True)
            with NamedTemporaryFile(dir=path.parent, delete=False) as output:
                temporary = Path(output.name)
                try:
                    output.write(outputs[path].encode("utf-8"))
                    output.close()
                    temporary.chmod(0o644)
                    temporary.replace(path)
                finally:
                    temporary.unlink(missing_ok=True)
        for path in retired:
            path.unlink(missing_ok=True)
    except (OSError, ValidationError, YAMLError, ValueError) as error:
        print(error, file=sys.stderr)
        return 1
    print(f"规则 DSL {'校验通过' if args.check else '导出完成'}，共 {len(outputs)} 个产物。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

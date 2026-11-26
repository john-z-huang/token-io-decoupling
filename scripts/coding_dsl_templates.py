"""从 Coding DSL 模板核对文档类型、块顺序和片段结构。"""

from __future__ import annotations

from collections.abc import Iterator
from itertools import groupby
from pathlib import Path

from jsonschema import Draft202012Validator
from ruamel.yaml import YAML

from workflow_flowcharts import parse_flowchart
from workflow_module_contracts import PHASES, ROUTE_HOOKS, TOP_PREFIXES, WORKFLOW_PATH

DOCUMENT_TYPES = ("directory-guide", "workflow-route")
HOOK_FLOWCHARTS = {"kind": "rule_include", "document": "coding-workflow-directory", "fragment": "hook-flowcharts"}


def document_type(path: Path) -> str:
    if path.parent != WORKFLOW_PATH:
        raise ValueError(f"{path} 所在目录没有对应的工作流模板")
    return "directory-guide" if path.stem == "README" else "workflow-route"


def block_entries(blocks: list[dict]) -> Iterator[tuple[str, dict]]:
    for entry in blocks:
        yield next(iter(entry.items()))


def validate_children(
    blocks: list[dict], path: Path, parent: str, expected: list[str] | None = None,
) -> None:
    kinds = [block["kind"] for _, block in block_entries(blocks)]
    if expected is None:
        if not set(kinds) <= {"markdown", "section"}:
            raise ValueError(f"{path}#{parent} 只能包含 Markdown 正文或子章节")
    elif [kind for kind, _ in groupby(kinds)] != expected:
        raise ValueError(f"{path}#{parent} 子块类型及顺序应为 {' → '.join(expected)}")
    for block_id, block in block_entries(blocks):
        if block["kind"] == "section":
            validate_children(block["blocks"], path, block_id)


def validate_coding_document(path: Path, document: dict, template: dict) -> None:
    expected_type = document_type(path)
    if document["document_type"] != expected_type:
        raise ValueError(f"{path} 的 document_type 应为 {expected_type}")
    blocks = dict(block_entries(document["blocks"]))
    order = list(blocks)
    if len(order) != len(document["blocks"]):
        raise ValueError(f"{path} 的顶层块 ID 有重复")
    layouts = template["layouts"]
    if order not in layouts:
        options = " 或 ".join(" → ".join(layout) for layout in layouts)
        raise ValueError(f"{path} 的 {expected_type} 块顺序应为 {options}")
    for block_id, block in blocks.items():
        rule = template["block_rules"][block_id]
        for field in ("kind", "expose"):
            if field in rule and block.get(field) != rule[field]:
                raise ValueError(f"{path}#{block_id} 的 {field} 应为 {rule[field]}")
        if block["kind"] == "section":
            validate_children(block["blocks"], path, block_id, rule.get("child_kinds"))

    if expected_type == "workflow-route":
        flowchart = blocks["flowchart"]["blocks"]
        if flowchart[-1].get("hook-details") != HOOK_FLOWCHARTS:
            raise ValueError(f"{path}#flowchart 须包含共用 Hook 子流程图")
        steps = list(block_entries(blocks["checkpoints"]["blocks"]))
        actual = [block["phase"] for _, block in steps if block["kind"] == "route_step"]
        if steps[0][0] != "preconditions" or actual != list(PHASES) or len(steps) != len(PHASES) + 1:
            raise ValueError(f"{path}#checkpoints 应先声明 preconditions，再依次列出 {' → '.join(PHASES)}")
        if path.stem in ROUTE_HOOKS:
            expected = tuple(
                (f"{TOP_PREFIXES[path.stem]}{index:02d}", hook)
                for index, hook in enumerate(ROUTE_HOOKS[path.stem], 1)
            )
            if tuple((block_id, block["hook"]) for block_id, block in steps[1:]) != expected:
                raise ValueError(f"{path}#checkpoints 的路线步骤 ID 或 Hook 顺序与工作流合同不一致")
        validate_route_diagram(path, flowchart, [name for name, _ in steps[1:]])


def validate_route_diagram(path: Path, blocks: list[dict], ids: list[str]) -> None:
    text = dict(block_entries(blocks))["flowchart-body"]["text"]
    nodes, edges = parse_flowchart(f"{path}#flowchart", text)
    sequence = ["START", *ids, "DONE", "END"]
    default_edges = [
        (start, end) for start, end, conditional in edges
        if not conditional and (end != "END" or start in sequence)
    ]
    if [node for node in nodes if node in sequence] != sequence or default_edges != list(zip(sequence, sequence[1:])):
        raise ValueError(f"{path}#flowchart 须按默认路线用实线从开始经各阶段和完成节点连至结束")
    if any(conditional and "DONE" in (start, end) for start, end, conditional in edges):
        raise ValueError(f"{path}#flowchart 的完成节点只能由交付阶段通过验收后进入")


def load_templates(directory: Path, validator: Draft202012Validator) -> dict[str, dict]:
    templates = {}
    for name in DOCUMENT_TYPES:
        path = directory / f"{name}.yaml"
        template = YAML(typ="rt").load(path)
        if {block_id for layout in template["layouts"] for block_id in layout} != set(template["block_rules"]):
            raise ValueError(f"{path.name} 的 layouts 和 block_rules 须声明相同的块 ID")
        sample = template["document"]
        sample_path = Path(sample["markdown_path"]).with_suffix(".yaml")
        if document_type(sample_path) != name:
            raise ValueError(f"{path.name} 的示例路径须对应 {name}")
        validator.validate(sample)
        validate_coding_document(sample_path, sample, template)
        templates[name] = template
    return templates

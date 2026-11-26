"""从 Coding DSL 模板核对文档类型、块顺序和片段结构。"""

from __future__ import annotations

from collections.abc import Iterator
from itertools import groupby
from pathlib import Path

from jsonschema import Draft202012Validator
from ruamel.yaml import YAML

from workflow_module_contracts import MODULE_HOOKS, ROUTE_MODULES, TOP_PREFIXES, WORKFLOW_PATH

LAYER_TYPES = {
    "layer-01-fundamental-concepts": "fundamental-concept",
    "layer-02-workflow-concepts": "workflow-concept",
    "layer-03-workflow-checkpoints": "workflow-checkpoint",
    WORKFLOW_PATH.as_posix(): "workflow-route",
}
DOCUMENT_TYPES = ("directory-guide", *LAYER_TYPES.values())


def document_type(path: Path) -> str:
    if path.stem == "README":
        return "directory-guide"
    layer = path.parts[2] if path.parts[:2] == ("references", "coding") else path.parts[0]
    if layer not in LAYER_TYPES:
        raise ValueError(f"{path} 所在目录没有对应的 Coding DSL 类型")
    return LAYER_TYPES[layer]


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
    if expected_type == "directory-guide":
        endings = {"classification", "owners"} if path.parts[0] == "references" else {"section-01"}
        layouts = [layout for layout in layouts if layout[-1] in endings]
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
        phases = template["phase_order"]
        steps = list(block_entries(blocks["checkpoints"]["blocks"]))
        actual = [block["phase"] for _, block in steps if block["kind"] == "route_step"]
        if steps[0][0] != "preconditions" or actual != phases or len(steps) != len(phases) + 1:
            raise ValueError(f"{path}#checkpoints 应先声明 preconditions，再依次列出 {' → '.join(phases)}")
        if path.stem in ROUTE_MODULES:
            expected = tuple(
                (f"{TOP_PREFIXES[path.stem]}{index:02d}", MODULE_HOOKS[module])
                for index, module in enumerate(ROUTE_MODULES[path.stem], 1)
            )
            if tuple((block_id, block["hook"]) for block_id, block in steps[1:]) != expected:
                raise ValueError(f"{path}#checkpoints 的路线步骤 ID 或 Hook 顺序与工作流合同不一致")


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

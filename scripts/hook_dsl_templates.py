"""依照 Hook 模板校验源文档与执行引用的位置。"""

from __future__ import annotations

import re
from pathlib import Path

from jsonschema import Draft202012Validator
from ruamel.yaml import YAML

from coding_dsl_templates import block_entries

HOOK_TYPES = ("hook-contract", "hook-directory")
HOOK_NAME = re.compile(r"[a-z][a-z0-9-]*")


def hook_type(path: Path) -> str:
    if path.name == "README.yaml":
        return "hook-directory"
    if HOOK_NAME.fullmatch(path.stem):
        return "hook-contract"
    raise ValueError(f"{path.name} 的文件名不符合 Hook DSL 模板")


def validate_hook_block(
    path: Path, name: str, block: dict, allow_include: bool, contract: bool,
) -> None:
    kind = block["kind"]
    if block.get("expose"):
        raise ValueError(f"{path.name}#{name} 不发布为参考规则片段")
    if kind == "section":
        for child_name, child in block_entries(block["blocks"]):
            validate_hook_block(path, child_name, child, allow_include, contract)
    elif kind == "markdown":
        if contract and "<!-- rule:" in block["text"]:
            raise ValueError(f"{path.name}#{name} 的执行引用须使用 rule_include 块")
    elif kind != "rule_include" or not allow_include:
        raise ValueError(f"{path.name}#{name} 无效的 Hook 块类型或引用位置：{kind}")


def validate_hook_document(path: Path, document: dict, template: dict) -> None:
    expected_type = hook_type(path)
    if document["document_type"] != expected_type:
        raise ValueError(f"{path.name} 的 document_type 应为 {expected_type}")
    if document["id"] != path.stem.lower():
        raise ValueError(f"{path.name} 的 Hook 文档 ID 应为 {path.stem.lower()}")
    blocks = list(block_entries(document["blocks"]))
    names = {name for name, _ in blocks}
    layout = list(block_entries(template["layout"]))
    expected = [(name, rule) for name, rule in layout if name in names or not rule.get("optional")]
    if [name for name, _ in blocks] != [name for name, _ in expected]:
        order = " → ".join(name for name, _ in expected)
        raise ValueError(f"{path.name} 的 Hook 章节顺序应为 {order}")
    contract = expected_type == "hook-contract"
    for (name, block), (_, rule) in zip(blocks, expected):
        if block["kind"] != rule["kind"] or ("title" in rule and block.get("title") != rule["title"]):
            raise ValueError(f"{path.name}#{name} 的块类型或标题不符合 Hook 模板")
        validate_hook_block(path, name, block, contract and name == "execution", contract)


def load_hook_templates(directory: Path, validator: Draft202012Validator) -> dict[str, dict]:
    templates = {}
    for name in HOOK_TYPES:
        path = directory / f"{name}.yaml"
        template = YAML(typ="rt").load(path)
        sample = template["document"]
        validator.validate(sample)
        sample_path = Path(sample["markdown_path"]).with_suffix(".yaml")
        if hook_type(sample_path) != name:
            raise ValueError(f"{path.name} 的示例路径须对应 {name}")
        validate_hook_document(sample_path, sample, template)
        templates[name] = template
    return templates

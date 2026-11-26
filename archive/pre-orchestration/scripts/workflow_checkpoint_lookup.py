"""定位 Coding DSL 中的检查点和流程图跨文件引用。"""

from __future__ import annotations

import re
from collections.abc import Iterator
from os.path import normpath
from pathlib import Path, PurePosixPath

from ruamel.yaml import YAML

import document_rules as COMPLIANCE
from workflow_module_contracts import WORKFLOW_PATH

NUMBERED_BLOCKS = {"checkpoint", "route_step"}


def walk_blocks(blocks: list[dict], prefix: str = "/blocks") -> Iterator[tuple[str, dict, dict]]:
    for index, entry in enumerate(blocks):
        name, block = next(iter(entry.items()))
        symbol = f"{prefix}/{index}/{name}"
        yield symbol, block, entry
        if block["kind"] == "section":
            yield from walk_blocks(block["blocks"], f"{symbol}/blocks")


def find_block(document: dict, name: str) -> tuple[str, dict, dict]:
    for symbol, block, entry in walk_blocks(document["blocks"]):
        if name in entry:
            return symbol, block, entry
    raise ValueError(f"{document['id']} 中找不到块 {name}")


def diagram_text(document: dict) -> str:
    symbol, block, _ = find_block(document, "flowchart-body")
    if symbol.rsplit("/", 3)[0].endswith("/flowchart") and block["kind"] == "markdown":
        return block["text"]
    raise ValueError(f"{document['id']} 缺少流程图正文块")


def resolve_reference(
    documents: dict[Path, dict], origin: Path, target: str,
) -> tuple[Path, tuple[str, dict, dict]]:
    file, _, name = target.partition("#")
    path = Path(normpath(origin.parent / file))
    if path not in documents:
        raise ValueError(f"{origin.name} 的流程图引用目标不存在：{target}")
    return path, find_block(documents[path], name)


def check_flowchart_references(documents: dict[Path, dict]) -> None:
    for path, document in documents.items():
        references = document.get("flowchart_references", {})
        if not references:
            continue
        diagram = diagram_text(document)
        local_ids = {
            next(iter(entry))
            for _, block, entry in walk_blocks(document["blocks"])
            if block["kind"] in NUMBERED_BLOCKS
        }
        for alias, target in references.items():
            if alias in local_ids:
                raise ValueError(f"{path.name} 的流程图引用 {alias} 与本地检查点重复")
            if not re.search(rf"(?m)^[ \t]*{re.escape(alias)}[ \t]*(?:\[|\(|\{{)", diagram):
                raise ValueError(f"{path.name} 的流程图未声明引用节点 {alias}")
            target_path, _ = resolve_reference(documents, path, target)
            if target_path == path:
                raise ValueError(f"{path.name} 的流程图引用 {alias} 须指向其他 DSL 文件")
            if COMPLIANCE.reverse_dependency_target(PurePosixPath(document["markdown_path"]), target):
                raise ValueError(f"{path.name} 的流程图节点 {alias} 存在反向依赖：{target}")


def locate_checkpoint(root: Path, references: Path, hooks: Path, selector: str, origin: str | None, show: bool) -> dict:
    # 保留 YAML 中的键位置，与 LSP 的列表索引对齐。
    yaml = YAML(typ="rt")
    routes = references.parent / WORKFLOW_PATH
    sources = [*(references / "coding").rglob("*.yaml"), *routes.rglob("*.yaml"), *hooks.glob("*.yaml")]
    documents = {path: yaml.load(path) for path in sorted(sources) if path.name != "SOURCE_COVERAGE.yaml"}
    def document_id(path: Path) -> str:
        name = documents[path]["id"]
        return f"hook-{name}" if path.parent == hooks else name

    by_id = {document_id(path): path for path in documents}
    wanted, separator, block_id = selector.partition("#")

    def describe(path: Path, match: tuple[str, dict, dict]) -> dict:
        symbol, block, entry = match
        name = next(iter(entry))
        result = dict(
            document_id=document_id(path),
            block_id=name,
            relative_path=path.relative_to(root).as_posix(),
            name_path=symbol,
            line=entry.lc.key(name)[0] + 1,
            kind=block["kind"],
            title=block.get("title"),
        )
        if show:
            result["block"] = block
        return result

    def result(path: Path, match: tuple[str, dict, dict]) -> dict:
        output = describe(path, match)
        _, block, _ = match
        if block["kind"] == "route_step":
            hook = hooks / f"{block['hook']}.yaml"
            if hook not in documents:
                raise ValueError(f"{path.name} 中的路线步骤引用了缺失的 Hook {block['hook']}")
            output["hook_entry"] = describe(hook, find_block(documents[hook], "trigger"))
        return output

    if separator or (not origin and wanted in by_id):
        path = by_id.get(wanted)
        if path is None:
            raise ValueError(f"找不到 Coding DSL 文档 {wanted}")
        if not separator and documents[path].get("document_type") == "workflow-checkpoint":
            block_id = "decision-and-result"
        if not block_id:
            raise ValueError(f"请用 {wanted}#块ID 指定 YAML 块")
        return result(path, find_block(documents[path], block_id))

    source = None
    if origin:
        source = by_id.get(origin)
        if source is None:
            raise ValueError(f"找不到流程图文档 {origin}")
        document = documents[source]
        if not re.search(rf"(?<![A-Za-z0-9_]){re.escape(wanted)}(?![A-Za-z0-9_])", diagram_text(document)):
            raise ValueError(f"{origin} 的流程图中找不到节点 {wanted}")
        target = document.get("flowchart_references", {}).get(wanted)
        if target:
            return result(*resolve_reference(documents, source, target))

    candidates = []
    for path, document in documents.items():
        if document.get("document_type") not in {"workflow-route", "hook-contract"}:
            continue
        for match in walk_blocks(document["blocks"]):
            _, block, entry = match
            if wanted in entry and block["kind"] in NUMBERED_BLOCKS:
                if path == source:
                    return result(path, match)
                candidates.append((path, match))
    if len(candidates) == 1:
        return result(*candidates[0])
    if candidates:
        files = "、".join(document_id(path) for path, _ in candidates)
        raise ValueError(f"检查点 {wanted} 存在多个定义（{files}），请用文档ID#块ID 查询")
    if origin:
        raise ValueError(f"{origin} 的图中节点 {wanted} 没有独立检查点或跨文件引用")
    raise ValueError(f"找不到检查点 {wanted}，查询图中别名时请加 --from 文档ID")

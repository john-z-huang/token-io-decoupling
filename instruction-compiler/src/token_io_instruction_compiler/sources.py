"""作者文件、Markdown 选择和显式静态指令依赖的完整性检查。"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from pathlib import Path
from urllib.parse import urlsplit

from .models import AuthorContextIndex, AuthorFragment, IndexNode, Instruction, SourceTrace

_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$", re.MULTILINE)


class CompilationError(ValueError):
    """作者源、契约或输出完整性不满足编译条件。"""


def canonical(value: object) -> bytes:
    """为构建身份生成稳定 JSON 字节；仅适用于可序列化的静态契约。"""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def digest(value: bytes | str) -> str:
    """统一按 UTF-8 文本或原始字节计算内容指纹，避免两种输入口径混用。"""
    return hashlib.sha256(value.encode() if isinstance(value, str) else value).hexdigest()


def json_bytes(value: object) -> bytes:
    """生成稳定、可人工审阅的 JSON 文件字节，包含唯一末尾换行。"""
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def safe_file(root: Path, relative: str) -> Path:
    """仅允许根目录内的普通作者文件，拒绝路径逃逸和中间符号链接。"""
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


def heading_entries(text: str) -> list[tuple[int, int, str]]:
    """列出真实标题的位置和级别，fenced 示例不参与选择。"""
    fence = None
    entries = []
    offset = 0
    for line in text.splitlines(keepends=True):
        position = offset
        offset += len(line)
        stripped = line.lstrip()
        if stripped.startswith(("```", "~~~")):
            marker = stripped[:3]
            fence = None if fence == marker else marker if fence is None else fence
            continue
        if fence is not None:
            continue
        match = _HEADING.fullmatch(line.rstrip("\r\n"))
        if match:
            entries.append((position, len(match[1]), match[2]))
    return entries


def extract_heading(text: str, heading: str) -> str:
    """返回唯一非空的标题区段，缺失或重复时拒绝编译。"""
    entries = heading_entries(text)
    selected = [entry for entry in entries if entry[2] == heading]
    if len(selected) != 1:
        raise CompilationError(f"missing or duplicate source heading: {heading}")
    start, level, _title = selected[0]
    end = next((entry[0] for entry in entries if entry[0] > start and entry[1] <= level), len(text))
    result = text[start:end].strip()
    if not result.partition("\n")[2].strip():
        raise CompilationError(f"empty source heading: {heading}")
    return result


def heading_sections(text: str, level: int) -> dict[str, str]:
    """将某一级真实子标题编为具名区段，供细粒度政策选项使用。"""
    result = {}
    for _position, heading_level, title in heading_entries(text):
        if heading_level == level:
            result[title] = extract_heading(text, title)
    return result


def _visit_dependency(
    key: str, lookup: dict[str, AuthorFragment], active: set[str], done: set[str]
) -> None:
    """校验显式静态依赖的存在性和无环性；已完成分支不会重复遍历。"""
    if key not in lookup:
        raise CompilationError(f"missing instruction dependency: {key}")
    if key in active:
        raise CompilationError(f"instruction dependency cycle: {key}")
    if key in done:
        return
    active.add(key)
    for dependency in lookup[key].get("dependencies", []):
        _visit_dependency(dependency, lookup, active, done)
    active.remove(key)
    done.add(key)


def _index_text(value: object) -> str:
    """在动态 JSON 边界拒绝非文本或空白标识，返回原文以保留真实来源。"""
    if not isinstance(value, str) or not value.strip():
        raise CompilationError("context-index identifiers must be nonblank text")
    return value


def _index_texts(value: object) -> list[str]:
    """仅接受文本数组；空数组允许表达没有依赖，不把字符串拆成字符列表。"""
    if not isinstance(value, list):
        raise CompilationError("context-index requirements must be string arrays")
    return [_index_text(item) for item in value]


def _validate_fragment(entry: object) -> AuthorFragment:
    """把实际 JSON 转为固定片段契约，拒绝旧语言字段和缺失的作者路径。"""
    required = {"fragment_id", "node_id", "source_path"}
    if not isinstance(entry, dict) or not required.issubset(entry):
        raise CompilationError("missing author fragment fields")
    if set(entry) - set(AuthorFragment.__annotations__):
        raise CompilationError("unsupported author fragment fields")
    fragment: AuthorFragment = {
        "fragment_id": _index_text(entry["fragment_id"]),
        "node_id": _index_text(entry["node_id"]),
        "source_path": _index_text(entry["source_path"]),
    }
    if "section" in entry:
        fragment["section"] = _index_text(entry["section"])
    if "dependencies" in entry:
        fragment["dependencies"] = _index_texts(entry["dependencies"])
    return fragment


def _validate_index_node(node: object) -> IndexNode:
    """校验静态查询 ID 与默认片段数组，不添加缺省运行步骤。"""
    if not isinstance(node, dict) or set(node) != set(IndexNode.__annotations__):
        raise CompilationError("unsupported author context-index node fields")
    return {
        "node_id": _index_text(node["node_id"]),
        "default_fragment_ids": _index_texts(node["default_fragment_ids"]),
    }


def validate_dependency_graph(value: object) -> AuthorContextIndex:
    """验证作者索引并返回固定契约；缺依赖、重复标识或依赖环均阻止编译。"""
    if not isinstance(value, dict) or set(value) != {"schema_version", "nodes", "fragments"}:
        raise CompilationError("unsupported author context-index fields")
    if type(value["schema_version"]) is not int or value["schema_version"] != 2:
        raise CompilationError("unsupported author context-index schema")
    if not isinstance(value["fragments"], list) or not isinstance(value["nodes"], list):
        raise CompilationError("context-index fragments and nodes must be arrays")
    index: AuthorContextIndex = {
        "schema_version": 2,
        "fragments": [_validate_fragment(entry) for entry in value["fragments"]],
        "nodes": [_validate_index_node(node) for node in value["nodes"]],
    }
    fragments = index["fragments"]
    lookup = {entry["fragment_id"]: entry for entry in fragments}
    if len(lookup) != len(fragments):
        raise CompilationError("duplicate author fragment identity")
    if len({node["node_id"] for node in index["nodes"]}) != len(index["nodes"]):
        raise CompilationError("duplicate author context-index node")
    active: set[str] = set()
    done: set[str] = set()
    for key in lookup:
        _visit_dependency(key, lookup, active, done)
    for node in index.get("nodes", []):
        for key in node["default_fragment_ids"]:
            _visit_dependency(key, lookup, active, done)
    return index


class AuthorSources:
    """管理单次编译的作者内容、显式选段和追溯，不管理业务运行状态。"""

    def __init__(
        self,
        root: Path,
        *,
        max_chars: int = 120_000,
        instruction_ids: Mapping[str, str] | None = None,
    ):
        """为一次编译创建独立缓存与追溯；预算按完整指令字符数计算。"""
        self.root = root
        self.max_chars = max_chars
        self.instruction_ids = dict(instruction_ids or {})
        self.trace: SourceTrace = {"closures": {}, "source_hashes": {}}
        self._content_cache: dict[str, str] = {}

    def read(self, path: str) -> str:
        """读取根内普通文件并记录源 Hash；读取失败不会生成替代内容。"""
        text = safe_file(self.root, path).read_text(encoding="utf-8")
        self.trace["source_hashes"][path] = digest(text)
        return text

    def select(self, path: str) -> str:
        """选择完整文档或唯一标题，去除前导元数据与导航地址，保留规范正文。"""
        if path not in self._content_cache:
            source, _separator, heading = path.partition("#")
            text = re.sub(r"\A---\n.*?\n---\n", "", self.read(source), flags=re.DOTALL).strip()
            selected = extract_heading(text, heading) if heading else text
            self._content_cache[path] = remove_navigation_targets(selected)
        return self._content_cache[path]

    def identity(self, path: str) -> str:
        """优先使用审核后的指令 ID，否则以完整路径和选段生成稳定身份。"""
        source, separator, section = path.partition("#")
        selection = source + ("#" + section if separator else "")
        return self.instruction_ids.get(selection, "unit." + digest(selection)[:16])

    def instruction(self, roots: list[str]) -> Instruction:
        """只组合显式来源；正文不完整或超预算时整体失败，不截断必需规则。"""
        unique = list(dict.fromkeys(roots))
        text = "\n\n".join(self.select(path) for path in unique)
        if not text or len(text) > self.max_chars:
            raise CompilationError(
                f"complete instruction exceeds approved bound for {roots}: "
                f"{len(text)} > {self.max_chars}"
            )
        self.trace["closures"][",".join(roots)] = {
            "sources": unique,
            "characters": len(text),
            "bytes": len(text.encode()),
            "navigation_expanded": False,
        }
        return {
            "text": text,
            "content_sha256": digest(text),
            "instruction_ids": sorted({self.identity(path) for path in unique}),
        }


def remove_navigation_targets(text: str) -> str:
    """运行正文只保留本地链接标签，避免导航被误解为必须继续读取的指令。"""

    def replace(match: re.Match[str]) -> str:
        target = urlsplit(match[2])
        return match[0] if target.scheme or target.netloc else match[1]

    return re.sub(r"\[([^\]]+)\]\(([^)]+)\)", replace, text)


def source_path(path: str) -> str:
    """将支持的作者路径归一到 Skill 相对地址，拒绝作者树外的路径约定。"""
    for prefix in ("instruction-compiler/sources/skill/", "docs/skill/"):
        if path.startswith(prefix):
            return path[len(prefix) :]
    if path in {"SKILL.md", "WORKFLOW_ARCHITECTURE.md"} or path.startswith(
        ("references/", "workflows/")
    ):
        return path
    raise CompilationError(f"source outside the author Skill: {path}")

"""Skill 文档的离线链接、依赖层级及章节检查。"""

from __future__ import annotations

import posixpath
import re
from collections.abc import Iterable, Mapping
from pathlib import PurePosixPath
from typing import Any
from urllib.parse import unquote


MAX_PATH_CHARS = 512
ZH_SUFFIX = "_zh_cn.md"
_HEADING_RE = re.compile(r"^## (.+?)\s*$")
_FENCE_RE = re.compile(r"^( {0,3})(`{3,}|~{3,})(.*)$")
_LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")
_INLINE_CODE_RE = re.compile(r"(`+)(.*?)\1")
_REFERENCE_LINK_RE = re.compile(r"^ {0,3}\[([^\]]+)\]:[ \t]*(<[^>]+>|[^\s]+)")
_EXTERNAL_LINK_RE = re.compile(r"^(?:[a-z][a-z0-9+.-]*:|//)", re.IGNORECASE)


def _advance_fence(line: str, fence_char: str = "", fence_width: int = 0) -> tuple[str, int]:
    """Update a CommonMark fenced-code state from one line."""
    match = _FENCE_RE.match(line.rstrip("\r\n"))
    if match is None:
        return fence_char, fence_width
    marker = match.group(2)
    info = match.group(3)
    char = marker[0]
    width = len(marker)
    if fence_char:
        if char == fence_char and width >= fence_width and not info.strip(" \t"):
            return "", 0
        return fence_char, fence_width
    if char == "`" and "`" in info:
        return "", 0
    return char, width


_LANGUAGE_SWITCH_LABELS = {"english", "简体中文"}
_SKILL_LAYERS = {
    ("references", "coding", "layer-01-fundamental-concepts"): "layer-01",
    ("references", "coding", "layer-02-workflow-concepts"): "layer-02",
    ("references", "coding", "layer-03-workflow-checkpoints"): "layer-03",
    ("hooks",): "hook",
    ("workflows",): "workflows",
}
_LAYER_RANK = {layer: index for index, layer in enumerate(_SKILL_LAYERS.values())}
_ROUTE_HOOKS = {
    "coding-single-agent": (
        "entry", "session", "planning", "execution", "verification", "documentation", "delivery",
    ),
    "coding-multi-agent": (
        "entry", "session", "planning", "delegation", "verification", "documentation", "delivery",
    ),
}
_SHARED_ROUTE_HOOKS = {"README", "foundation", "recovery", "repair"}


class ComplianceInputError(ValueError):
    """Raised when a caller-supplied candidate envelope exceeds its contract."""


def validate_relative_posix_path(value: Any) -> str:
    """Return a canonical repo-relative POSIX path or reject it without OS resolution."""
    if not isinstance(value, str) or not value or len(value) > MAX_PATH_CHARS:
        raise ComplianceInputError("candidate_path_invalid_length")
    if "\\" in value or "\x00" in value or value.startswith("/"):
        raise ComplianceInputError("candidate_path_not_relative_posix")
    parts = value.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise ComplianceInputError("candidate_path_not_canonical")
    path = PurePosixPath(value)
    if path.is_absolute() or path.as_posix() != value:
        raise ComplianceInputError("candidate_path_not_canonical")
    return value


def path_layer(path: PurePosixPath) -> str:
    parts = path.parts
    if parts and parts[0] in {"skill", "rules"}:
        parts = parts[1:]
    if len(parts) == 2 and parts[0] == "workflows" and parts[1] in {
        "coding.yaml", "coding.md", "coding_zh_cn.md",
    }:
        return "coding-selector"
    if parts[:2] == ("workflows", "checkpoint"):
        return "checkpoint"
    if parts[:2] == ("workflows", "exist-workflow"):
        return "exist-workflow"
    for prefix, layer in _SKILL_LAYERS.items():
        if parts[:len(prefix)] == prefix:
            return layer
    if parts[:2] == ("references", "share"):
        return "shared-protocols"
    if parts and parts[0] == "references":
        return "references"
    return "entry"


def is_reverse_dependency(source_layer: str, target_layer: str) -> bool:
    return (
        source_layer in _LAYER_RANK
        and target_layer in _LAYER_RANK
        and _LAYER_RANK[source_layer] < _LAYER_RANK[target_layer]
    )


def reverse_dependency_target(source: PurePosixPath, href: str) -> str | None:
    """识别跨层回链，包括目录链接和带转义的相对路径。"""
    if _EXTERNAL_LINK_RE.match(href):
        return None
    target = unquote(href.split("#", 1)[0].split("?", 1)[0])
    if not target:
        return None
    resolved = posixpath.normpath(posixpath.join(source.parent.as_posix(), target)).lstrip("/")
    if is_reverse_dependency(path_layer(source), path_layer(PurePosixPath(resolved))):
        return resolved
    return None


def path_language(path: PurePosixPath) -> str:
    return "zh"


def is_language_switch(label: str) -> bool:
    return label.strip().casefold() in _LANGUAGE_SWITCH_LABELS


def is_navigation_document(path: PurePosixPath) -> bool:
    return path.name in {"README.md", "README_zh_cn.md", "INDEX.md", "INDEX_zh_cn.md"}


def counterpart(path: PurePosixPath) -> PurePosixPath:
    if path.parts[:2] == ("docs", "zh-cn"):
        return PurePosixPath("docs", path.name)
    if path == PurePosixPath("docs/index.md"):
        return PurePosixPath("docs/zh-cn/index.md")
    if path.name.endswith(ZH_SUFFIX):
        return path.with_name(path.name.removesuffix(ZH_SUFFIX) + ".md")
    return path.with_name(path.stem + ZH_SUFFIX)


def allowed_link(
    source: str,
    target: str,
    is_navigation: bool,
    source_path: PurePosixPath | None = None,
    target_path: PurePosixPath | None = None,
) -> bool:
    if is_reverse_dependency(source, target):
        return False
    same_layer_navigation = is_navigation and source == target
    if source in {"references", "layer-01"}:
        return same_layer_navigation or target == "layer-01"
    if source in {"checkpoint", "layer-02"}:
        return same_layer_navigation or target in {"references", "layer-01"}
    if source in {"exist-workflow", "layer-03"}:
        return same_layer_navigation or target in {"shared-protocols", "layer-01", "layer-02"}
    if source == "workflows":
        if same_layer_navigation or target in {
            "shared-protocols",
            "layer-01",
            "layer-02",
            "layer-03",
        }:
            return True
        if target != "hook" or source_path is None or target_path is None:
            return False
        hook_root = PurePosixPath("skill/hooks")
        if target_path.parent != hook_root or target_path.suffix != ".md":
            return False
        route_root = PurePosixPath("skill/workflows")
        if source_path.parent != route_root:
            return False
        if is_navigation:
            return any(target_path.stem in hooks for hooks in _ROUTE_HOOKS.values())
        if source_path.suffix != ".md":
            return False
        route_name = source_path.stem.removesuffix("_zh_cn")
        route_hooks = _ROUTE_HOOKS.get(route_name)
        return route_hooks is not None and (
            target_path.stem in route_hooks or target_path.stem in _SHARED_ROUTE_HOOKS
        )
    if source == "hook":
        return target != "layer-04"
    if source == "layer-04":
        return same_layer_navigation or target in {
            "shared-protocols",
            "layer-01",
            "layer-02",
            "layer-03",
        }
    if source == "coding-selector":
        return is_navigation or target in {
            "exist-workflow",
            "layer-01",
            "layer-02",
            "layer-03",
            "layer-04",
            "workflows",
            "hook",
        }
    return True


def normalize_markdown_target(source: PurePosixPath, raw: str) -> str | None:
    target = raw.split("#", 1)[0].split("?", 1)[0]
    if (
        not target
        or "://" in target
        or target.startswith(("mailto:", "{{"))
        or not target.endswith(".md")
    ):
        return None
    if target.startswith("/") or "\\" in target or "\x00" in target:
        return ""
    normalized = posixpath.normpath(posixpath.join(source.parent.as_posix(), target))
    if normalized in {".", ".."} or normalized.startswith("../") or normalized.startswith("/"):
        return ""
    try:
        return validate_relative_posix_path(normalized)
    except ComplianceInputError:
        return ""


def links_in_markdown(content: str) -> Iterable[tuple[int, str, str]]:
    fence_char, fence_width = "", 0
    for line_number, line in enumerate(content.splitlines(), 1):
        previous = fence_char
        fence_char, fence_width = _advance_fence(line, fence_char, fence_width)
        if previous or fence_char:
            continue
        line = _INLINE_CODE_RE.sub("", line)
        links = _LINK_RE.findall(line)
        definition = _REFERENCE_LINK_RE.match(line)
        if definition:
            links.append(definition.groups())
        for label, raw in links:
            target = raw.strip()
            if target.startswith("<") and ">" in target:
                target = target[1:target.index(">")]
            elif target:
                target = target.split(maxsplit=1)[0]
            if target:
                yield line_number, label, target


def document_link_issues(documents: Mapping[str, str]) -> list[str]:
    """CLI-compatible messages for the full repository Markdown link validator."""
    present_paths = set(documents)
    issues: list[str] = []
    for path, content in sorted(documents.items()):
        source = PurePosixPath(path)
        source_layer = path_layer(source)
        source_language = path_language(source)
        for line_number, label, raw_target in links_in_markdown(content):
            reverse = reverse_dependency_target(source, raw_target)
            if reverse is not None:
                issues.append(f"layer violation: {path}:{line_number} -> {reverse} (反向依赖)")
                continue
            target_text = raw_target.split("#", 1)[0].split("?", 1)[0]
            if (
                not target_text
                or "://" in target_text
                or target_text.startswith(("mailto:", "{{"))
                or not target_text.endswith(".md")
            ):
                continue
            target = normalize_markdown_target(source, raw_target)
            if target == "":
                issues.append(f"target escapes repository: {path}:{line_number} -> {target_text}")
                continue
            assert target is not None
            if target not in present_paths:
                issues.append(f"missing local target: {path}:{line_number} -> {target}")
                continue
            target_path = PurePosixPath(target)
            target_language = path_language(target_path)
            is_mirror = target_path == counterpart(source)
            if target_language != source_language and not (is_language_switch(label) and is_mirror):
                issues.append(f"cross-language dependency: {path}:{line_number} -> {target}")
            target_layer = path_layer(target_path)
            is_navigation = (
                is_mirror
                or (target_path == source and is_language_switch(label))
                or is_navigation_document(source)
            )
            if not allowed_link(source_layer, target_layer, is_navigation, source, target_path):
                issues.append(
                    f"layer violation: {path}:{line_number} ({source_layer}) -> "
                    f"{target} ({target_layer})"
                )
    return issues


def top_level_sections(content: str) -> list[tuple[int, str, int]]:
    """Return line number, heading text, and content offset outside fenced code."""
    sections: list[tuple[int, str, int]] = []
    fence_char = ""
    fence_width = 0
    offset = 0
    for number, line in enumerate(content.splitlines(keepends=True), 1):
        previous_fence_char = fence_char
        fence_char, fence_width = _advance_fence(line, fence_char, fence_width)
        if previous_fence_char or fence_char:
            offset += len(line)
            continue
        if match := _HEADING_RE.match(line.rstrip("\r\n")):
            sections.append((number, match.group(1), offset))
        offset += len(line)
    return sections


def layer01_section_issues(path: str, content: str) -> list[str]:
    expected = ("通用规范", "运行时指引", "相关概念")
    sections = top_level_sections(content)
    errors: list[str] = []
    found = [heading for _line, heading, _offset in sections]
    if found != list(expected):
        errors.append(f"{path}: 二级标题必须唯一且按序为 " + " → ".join(expected))
    for index, (line, heading, offset) in enumerate(sections):
        start = content.find("\n", offset)
        start = len(content) if start < 0 else start + 1
        end = sections[index + 1][2] if index + 1 < len(sections) else len(content)
        if heading in expected and not content[start:end].strip():
            errors.append(f"{path}:{line}: 模块 `## {heading}` 为空")
    return errors

"""核对 Skill 文档的离线链接和依赖方向。"""

from __future__ import annotations

import posixpath
import re
from collections.abc import Iterable, Mapping
from pathlib import PurePosixPath
from typing import Any
from urllib.parse import unquote

from workflow_module_contracts import ROUTE_HOOKS


MAX_PATH_CHARS = 512
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


_SKILL_LAYERS = {
    ("references",): "references",
    ("hooks",): "hook",
    ("workflows",): "workflows",
}
_LAYER_RANK = {layer: index for index, layer in enumerate(_SKILL_LAYERS.values())}
_SHARED_ROUTE_HOOKS = {"README", "delegation", "execution", "recovery"}


class LinkPathError(ValueError):
    """本地链接路径不符合仓库相对 POSIX 路径要求。"""


def validate_relative_posix_path(value: Any) -> str:
    """Return a canonical repo-relative POSIX path or reject it without OS resolution."""
    if not isinstance(value, str) or not value or len(value) > MAX_PATH_CHARS:
        raise LinkPathError("link_path_invalid_length")
    if "\\" in value or "\x00" in value or value.startswith("/"):
        raise LinkPathError("link_path_not_relative_posix")
    parts = value.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise LinkPathError("link_path_not_canonical")
    path = PurePosixPath(value)
    if path.is_absolute() or path.as_posix() != value:
        raise LinkPathError("link_path_not_canonical")
    return value


def path_layer(path: PurePosixPath) -> str:
    parts = path.parts
    if parts and parts[0] in {"skill", "rules"}:
        parts = parts[1:]
    if parts in {("workflows", "coding.yaml"), ("workflows", "coding.md")}:
        return "coding-selector"
    for prefix, layer in _SKILL_LAYERS.items():
        if parts[:len(prefix)] == prefix:
            return layer
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


def allowed_link(
    source_path: PurePosixPath, target_path: PurePosixPath,
) -> bool:
    source, target = map(path_layer, (source_path, target_path))
    if is_reverse_dependency(source, target):
        return False
    if source == "workflows" and target == "hook":
        hooks = ROUTE_HOOKS.get(source_path.stem)
        if hooks is not None:
            return target_path.stem in hooks or target_path.stem in _SHARED_ROUTE_HOOKS
    return True


def normalize_markdown_target(source: PurePosixPath, raw: str) -> str | None:
    target = unquote(raw.split("#", 1)[0].split("?", 1)[0])
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
    except LinkPathError:
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
    """核对本地 Markdown 链接与 Skill 文档依赖方向。"""
    present_paths = set(documents)
    issues: list[str] = []
    for path, content in sorted(documents.items()):
        source = PurePosixPath(path)
        source_layer = path_layer(source)
        for line_number, _, raw_target in links_in_markdown(content):
            reverse = reverse_dependency_target(source, raw_target)
            if reverse is not None:
                issues.append(f"layer violation: {path}:{line_number} -> {reverse} (反向依赖)")
                continue
            target = normalize_markdown_target(source, raw_target)
            if target is None:
                continue
            if target == "":
                issues.append(f"target escapes repository: {path}:{line_number} -> {raw_target}")
                continue
            if target not in present_paths:
                issues.append(f"missing local target: {path}:{line_number} -> {target}")
                continue
            target_path = PurePosixPath(target)
            target_layer = path_layer(target_path)
            if not allowed_link(source, target_path):
                issues.append(
                    f"layer violation: {path}:{line_number} ({source_layer}) -> "
                    f"{target} ({target_layer})"
                )
    return issues

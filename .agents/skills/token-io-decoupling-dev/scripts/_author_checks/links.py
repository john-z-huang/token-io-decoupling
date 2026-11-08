"""Markdown 链接提取、规范化和直接依赖检查。"""

from __future__ import annotations

import posixpath
from collections.abc import Callable, Iterable, Mapping
from pathlib import PurePosixPath
from typing import Any

from .constants import _FENCE_RE, _INLINE_CODE_RE, _LINK_RE
from .findings import _finding
from .paths import (
    allowed_link,
    counterpart,
    is_language_switch,
    is_navigation_document,
    path_language,
    path_layer,
)
from .validation import ComplianceInputError, validate_relative_posix_path


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


def normalize_multilingual_target(source: PurePosixPath, raw: str) -> PurePosixPath | None:
    """Preserve the standalone multilingual validator's anchor/path interpretation."""
    target = raw.split("#", 1)[0].split("?", 1)[0]
    if not target or "://" in target or target.startswith("mailto:") or not target.endswith(".md"):
        return None
    return PurePosixPath(source.parent, target)


def links_in_markdown(content: str) -> Iterable[tuple[int, str, str]]:
    fenced = False
    for line_number, line in enumerate(content.splitlines(), 1):
        if line.strip().startswith("```"):
            fenced = not fenced
            continue
        if fenced:
            continue
        for label, raw_target in _LINK_RE.findall(_INLINE_CODE_RE.sub("", line)):
            yield line_number, label, raw_target


def document_link_findings(
    path: str,
    content: str,
    target_present: Callable[[str], bool | None],
) -> list[dict[str, Any]]:
    """Return bounded-by-caller local link findings for one source document."""
    source = PurePosixPath(path)
    source_layer = path_layer(source)
    source_language = path_language(source)
    findings: list[dict[str, Any]] = []
    for line_number, label, raw_target in links_in_markdown(content):
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
            findings.append(
                _finding(
                    "markdown_link_target",
                    "fail",
                    path,
                    line_number,
                    "link target escapes the trusted repository root or is not a canonical "
                    "relative path",
                )
            )
            continue
        assert target is not None
        target_path = PurePosixPath(target)
        target_language = path_language(target_path)
        is_mirror = target_path == counterpart(source)
        if target_language != source_language and not (is_language_switch(label) and is_mirror):
            findings.append(
                _finding(
                    "markdown_link_language",
                    "fail",
                    path,
                    line_number,
                    "cross-language Markdown link is not the visible language switch",
                    target_path=target,
                )
            )
        target_layer = path_layer(target_path)
        is_navigation = (
            is_mirror
            or (target_path == source and is_language_switch(label))
            or is_navigation_document(source)
        )
        if not allowed_link(source_layer, target_layer, is_navigation, source, target_path):
            findings.append(
                _finding(
                    "markdown_link_layer",
                    "fail",
                    path,
                    line_number,
                    f"layer dependency is not allowed from {source_layer} to {target_layer}",
                    target_path=target,
                )
            )
        present = target_present(target)
        if present is False:
            findings.append(
                _finding(
                    "markdown_link_target",
                    "fail",
                    path,
                    line_number,
                    "local Markdown link target does not exist in the candidate overlay or "
                    "trusted root",
                    target_path=target,
                )
            )
        elif present is None:
            findings.append(
                _finding(
                    "markdown_link_target",
                    "unknown",
                    path,
                    line_number,
                    "local Markdown link target could not be safely verified",
                    target_path=target,
                    evidence_missing=[
                        "safe UTF-8 read of the linked Markdown target within configured limits"
                    ],
                )
            )
    return findings


def _resolve_document_link(
    source: PurePosixPath,
    link: tuple[int, str, str],
    is_present: Callable[[str], bool],
) -> tuple[PurePosixPath | None, list[str]]:
    """按仓库边界解析本地链接；不存在、符号链接或越界目标都保留为可报告的问题。"""
    target_text = link[2].split("#", 1)[0].split("?", 1)[0]
    if (
        not target_text
        or "://" in target_text
        or target_text.startswith(("mailto:", "{{"))
        or not target_text.endswith(".md")
    ):
        return None, []
    target = normalize_markdown_target(source, link[2])
    if target == "":
        return None, [f"target escapes repository: {source}:{link[0]} -> {target_text}"]
    assert target is not None
    if not is_present(target):
        return None, [f"missing local target: {source}:{link[0]} -> {target}"]
    return PurePosixPath(target), []


def _document_dependency_issues(
    source: PurePosixPath,
    link: tuple[int, str, str],
    target: PurePosixPath,
    additional_allowed_link: Callable[[str, str], bool] | None,
) -> list[str]:
    """在目标已经安全解析后检查语言与分层关系，只允许调用方明确审核的额外边。"""
    issues = []
    line_number, label = link[0], link[1]
    is_mirror = target == counterpart(source)
    if path_language(target) != path_language(source) and not (
        is_language_switch(label) and is_mirror
    ):
        issues.append(f"cross-language dependency: {source}:{line_number} -> {target}")
    source_layer, target_layer = path_layer(source), path_layer(target)
    is_navigation = (
        is_mirror
        or (target == source and is_language_switch(label))
        or is_navigation_document(source)
    )
    permitted_extension = additional_allowed_link is not None and additional_allowed_link(
        source.as_posix(), target.as_posix()
    )
    if not permitted_extension and not allowed_link(
        source_layer, target_layer, is_navigation, source, target
    ):
        issues.append(
            f"layer violation: {source}:{line_number} ({source_layer}) -> {target} ({target_layer})"
        )
    return issues


def _single_document_link_issues(
    path: str,
    content: str,
    is_present: Callable[[str], bool],
    additional_allowed_link: Callable[[str, str], bool] | None,
) -> list[str]:
    """逐条检查一篇维护中文档的链接，将定位信息与依赖错误一起返回。"""
    source = PurePosixPath(path)
    issues = []
    for link in links_in_markdown(content):
        target, resolution_issues = _resolve_document_link(source, link, is_present)
        issues.extend(resolution_issues)
        if target is not None:
            issues.extend(
                _document_dependency_issues(source, link, target, additional_allowed_link)
            )
    return issues


def document_link_issues(
    documents: Mapping[str, str],
    *,
    target_present: Callable[[str], bool] | None = None,
    additional_allowed_link: Callable[[str, str], bool] | None = None,
) -> list[str]:
    """校验链接安全与分层；调用方只能额外指定精确的已审核依赖边。"""
    present_paths = set(documents)
    is_present = target_present or present_paths.__contains__
    issues: list[str] = []
    for path, content in sorted(documents.items()):
        issues.extend(
            _single_document_link_issues(path, content, is_present, additional_allowed_link)
        )
    return issues

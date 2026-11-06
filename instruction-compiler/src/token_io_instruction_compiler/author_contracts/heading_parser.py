"""Fence-aware extraction of one Markdown ATX heading body."""

from __future__ import annotations

import re


class HeadingNotFoundError(ValueError):
    """The requested heading does not occur outside fenced code blocks."""


class DuplicateHeadingError(ValueError):
    """The requested heading occurs more than once outside fenced code blocks."""


_FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
_ATX = re.compile(r"^ {0,3}(#{1,6})[ \t]+(.+?)(?:[ \t]+#+)?[ \t]*$")


def _headings(source: str) -> list[tuple[int, int, int, str]]:
    """Return (start, end, level, title) lines outside fenced code blocks."""
    result: list[tuple[int, int, int, str]] = []
    fence_char: str | None = None
    fence_length = 0
    offset = 0
    for line in source.splitlines(keepends=True):
        content = line.rstrip("\r\n")
        fence = _FENCE.match(content)
        if fence_char is not None:
            if (
                fence
                and fence.group(1)[0] == fence_char
                and len(fence.group(1)) >= fence_length
                and not fence.group(2).strip(" \t")
            ):
                fence_char = None
                fence_length = 0
            offset += len(line)
            continue
        if fence:
            marker = fence.group(1)
            # CommonMark backtick fences cannot contain backticks in the info string.
            if marker[0] != "`" or "`" not in fence.group(2):
                fence_char = marker[0]
                fence_length = len(marker)
            offset += len(line)
            continue
        heading = _ATX.match(content)
        if heading:
            title = heading.group(2).strip()
            result.append((offset, offset + len(line), len(heading.group(1)), title))
        offset += len(line)
    return result


def extract_heading(source: str, title: str) -> str:
    """Return the body of the unique exact ATX heading, ignoring fenced code."""
    target = title.strip()
    matches = [heading for heading in _headings(source) if heading[3] == target]
    if not matches:
        raise HeadingNotFoundError(f"heading {target!r} was not found outside fenced code")
    if len(matches) != 1:
        raise DuplicateHeadingError(f"heading {target!r} occurs {len(matches)} times")
    start, end, level, _ = matches[0]
    next_heading = next(
        (item for item in _headings(source) if item[0] >= end and item[2] <= level),
        None,
    )
    body_end = next_heading[0] if next_heading else len(source)
    body = source[end:body_end].strip()
    if not body:
        raise HeadingNotFoundError(f"heading {target!r} has an empty body")
    return body

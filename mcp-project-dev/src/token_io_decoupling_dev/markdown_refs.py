"""Small deterministic Markdown reference scanner for compiler source excerpts.

It recognizes inline and reference-style links, while excluding code examples,
language-switch rows, and Related concepts navigation blocks. It never fetches URLs.
"""

from __future__ import annotations

import html
import re
import string
from collections.abc import Mapping
from dataclasses import dataclass
from urllib.parse import urlsplit


@dataclass(frozen=True, slots=True)
class MarkdownLink:
    raw: str
    label: str
    destination: str | None
    occurrence: int


def _mask_fenced_code(text: str) -> str:
    lines = text.splitlines(keepends=True)
    result: list[str] = []
    fence_char: str | None = None
    fence_size = 0
    for line in lines:
        match = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line.rstrip("\r\n"))
        if fence_char is None and match:
            token = match.group(1)
            if token[0] == "`" and "`" in match.group(2):
                result.append(line)
                continue
            fence_char, fence_size = token[0], len(token)
            result.append(
                "".join("\n" if char == "\n" else "\r" if char == "\r" else " " for char in line)
            )
            continue
        if fence_char is not None:
            closing = re.match(
                rf"^ {{0,3}}{re.escape(fence_char)}{{{fence_size},}}\s*(?:\r?\n)?$", line
            )
            result.append(
                "".join("\n" if char == "\n" else "\r" if char == "\r" else " " for char in line)
            )
            if closing:
                fence_char = None
                fence_size = 0
            continue
        result.append(line)
    return "".join(result)


def _is_escaped(text: str, index: int) -> bool:
    count = 0
    while index > 0 and text[index - 1] == "\\":
        count += 1
        index -= 1
    return count % 2 == 1


def _mask_inline_code(text: str) -> str:
    chars = list(text)
    index = 0
    while index < len(text):
        if text[index] != "`" or _is_escaped(text, index):
            index += 1
            continue
        end = index + 1
        while end < len(text) and text[end] == "`":
            end += 1
        delimiter_size = end - index
        closing_run = next(
            (
                match
                for match in re.compile(r"`+").finditer(text, end)
                if len(match.group()) == delimiter_size
            ),
            None,
        )
        if closing_run is None:
            index = end
            continue
        close = closing_run.end()
        for position in range(index, close):
            if chars[position] not in "\r\n":
                chars[position] = " "
        index = close
    return "".join(chars)


def _mask_navigation_sections(text: str) -> str:
    # Navigation references still need classification. Only the standalone
    # bilingual switch is structural boilerplate rather than a policy link.
    return "".join(
        "".join("\n" if char == "\n" else "\r" if char == "\r" else " " for char in line)
        if _is_language_switch_row(line)
        else line
        for line in text.splitlines(keepends=True)
    )


def _is_language_switch_row(line: str) -> bool:
    """Match only a standalone English/Chinese language-switch link pair."""
    match = re.fullmatch(
        r"\s*\[English\]\(([^()\s]+)\)\s*\|\s*\[简体中文\]\(([^()\s]+)\)\s*\r?\n?",
        line,
        flags=re.IGNORECASE,
    )
    if not match:
        return False
    try:
        en, zh = (urlsplit(destination) for destination in match.groups())
    except ValueError:
        return False
    return (
        not en.scheme
        and not en.netloc
        and not zh.scheme
        and not zh.netloc
        and not en.path.startswith("/")
        and en.path.endswith(".md")
        and not en.path.endswith("_zh_cn.md")
        and zh.path == en.path.removesuffix(".md") + "_zh_cn.md"
    )


def markdown_heading_locations(text: str) -> list[tuple[int, int, int, str, str | None]]:
    """Return headings with offsets, levels, titles, and GitHub-style anchors.

    Offsets refer to the original text; masking fenced code preserves lengths.
    Duplicate generated anchors receive the same numeric disambiguation as
    document headings, including collisions with an existing numbered slug.
    """
    headings = []
    definitions, _ = _reference_definitions(_mask_fenced_code(text))
    used: set[str] = set()
    ambiguous_prior_anchor = False
    offset = 0
    previous: tuple[int, str] | None = None
    for line in _mask_fenced_code(text).splitlines(keepends=True):
        match = re.match(r"^ {0,3}(#{1,6})[ \t]+(.+?)(?:[ \t]+#+)?[ \t]*$", line.rstrip("\r\n"))
        underline = re.fullmatch(r" {0,3}(=+|-+)[ \t]*", line.rstrip("\r\n"))
        if match:
            title = match.group(2).strip()
            start, end, level = offset, offset + len(line), len(match.group(1))
        elif underline and previous:
            start, title = previous
            end = offset + len(line)
            level = 1 if underline.group(1).startswith("=") else 2
        else:
            title = ""
        if title:
            rendered = title
            links = extract_markdown_links(
                title, inherited_definitions=definitions, mask_language_switch=False
            )
            for link in links:
                if link.destination is None:
                    continue
                if link.raw.startswith("!["):
                    # Image rendering can change visible heading text; fail
                    # closed rather than manufacture an anchor or its suffixes.
                    ambiguous_prior_anchor = True
                    continue
                if link.raw.startswith("["):
                    label_end = _find_bracket_end(link.raw, 0)
                    if label_end is None:
                        ambiguous_prior_anchor = True
                        continue
                    label = link.raw[1:label_end]
                else:
                    label = link.label
                rendered = rendered.replace(link.raw, label, 1)
            anchor = None
            if not ambiguous_prior_anchor:
                rendered = html.unescape(re.sub(r"<[^>]*>", "", rendered))
                slug = re.sub(r"[^\w\- ]", "", rendered.lower()).replace(" ", "-")
                anchor = slug
                suffix = 0
                while anchor in used:
                    suffix += 1
                    anchor = f"{slug}-{suffix}"
                used.add(anchor)
            headings.append((start, end, level, title, anchor))
            previous = None
        elif (
            line.strip()
            and not line.startswith(("    ", "\t"))
            and not re.match(r" {0,3}(?:[>*+-](?:\s|$)|\d{1,9}[.)]\s|<)", line)
        ):
            previous = (offset, line.strip())
        else:
            previous = None
        offset += len(line)
    return headings


def _find_bracket_end(text: str, start: int) -> int | None:
    depth = 1
    index = start + 1
    while index < len(text):
        char = text[index]
        if char == "\\":
            index += 2
            continue
        if char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
            if depth == 0:
                return index
        index += 1
    return None


def _read_inline_destination(text: str, open_paren: int) -> tuple[int, str] | None:
    index = open_paren + 1
    while index < len(text) and text[index].isspace():
        index += 1
    if index >= len(text):
        return None
    if text[index] == "<":
        end = text.find(">", index + 1)
        if end < 0:
            return None
        destination = text[index + 1 : end]
        index = end + 1
    else:
        start = index
        nested = 0
        while index < len(text):
            char = text[index]
            if char == "\\":
                index += 2
                continue
            if char == "(":
                nested += 1
            elif char == ")":
                if nested == 0:
                    return index, text[start:index]
                nested -= 1
            elif char.isspace() and nested == 0:
                break
            index += 1
        destination = text[start:index]
    while index < len(text) and text[index].isspace():
        index += 1
    if index < len(text) and text[index] in "\"'":
        quote = text[index]
        index += 1
        while index < len(text):
            if text[index] == "\\":
                index += 2
                continue
            if text[index] == quote:
                index += 1
                break
            index += 1
        while index < len(text) and text[index].isspace():
            index += 1
    if index < len(text) and text[index] == ")":
        return index, destination
    return None


def _reference_definitions(text: str) -> tuple[dict[str, str], str]:
    definitions: dict[str, str] = {}
    masked = list(text)
    pattern = re.compile(
        r"""^ {0,3}\[([^\]]+)\]:[ \t]*(<[^>\r\n]*>|[^\s]+)"""
        r"""(?:[ \t]+(?:"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|\((?:\\.|[^)\\])*\)))?"""
        r"""[ \t]*(?:\r?\n|$)""",
        re.MULTILINE,
    )
    for match in pattern.finditer(text):
        target = match.group(2)
        if target.startswith("<") and target.endswith(">"):
            target = target[1:-1]
        definitions.setdefault(" ".join(match.group(1).casefold().split()), target)
        for position in range(match.start(), match.end()):
            if masked[position] not in "\r\n":
                masked[position] = " "
    return definitions, "".join(masked)


def _unescape(value: str) -> str:
    return html.unescape(re.sub(r"\\([" + re.escape(string.punctuation) + r"])", r"\1", value))


def extract_markdown_links(
    text: str,
    *,
    inherited_definitions: Mapping[str, str] | None = None,
    mask_language_switch: bool = True,
) -> list[MarkdownLink]:
    """Return every relevant local or external link in source order.

    The raw Markdown token and zero-based duplicate occurrence form a stable
    source selector. An unresolved reference-style link is returned with a
    missing destination so the compiler fails closed rather than dropping it.
    """
    visible = _mask_inline_code(_mask_fenced_code(text))
    if mask_language_switch:
        visible = _mask_navigation_sections(visible)
    definitions, visible = _reference_definitions(visible)
    for label, destination in (inherited_definitions or {}).items():
        definitions.setdefault(label, destination)
    links: list[tuple[str, str, str | None]] = []
    index = 0
    while index < len(visible):
        if visible[index] != "[" or _is_escaped(visible, index):
            if visible[index] == "<" and not _is_escaped(visible, index):
                close = visible.find(">", index + 1)
                if close >= 0:
                    destination = visible[index + 1 : close]
                    is_uri = re.fullmatch(r"[A-Za-z][A-Za-z0-9+.-]{1,31}:[^\s<>]*", destination)
                    is_email = re.fullmatch(r"[^\s<>@]+@[^\s<>@]+\.[^\s<>@]+", destination)
                    if is_uri or is_email:
                        raw = text[index : close + 1]
                        value = _unescape(destination)
                        links.append((raw, value, value))
                        index = close + 1
                        continue
            index += 1
            continue
        start = index - 1 if index > 0 and visible[index - 1] == "!" else index
        label_end = _find_bracket_end(visible, index)
        if label_end is None:
            index += 1
            continue
        label = visible[index + 1 : label_end]
        after = label_end + 1
        if after < len(visible) and visible[after] == "(":
            parsed = _read_inline_destination(visible, after)
            if parsed is None:
                index = label_end + 1
                continue
            close, destination = parsed
            raw = text[start : close + 1]
            links.append((raw, _unescape(label), _unescape(destination)))
            index = close + 1
            continue
        if after < len(visible) and visible[after] == "[":
            reference_end = _find_bracket_end(visible, after)
            if reference_end is None:
                index = after + 1
                continue
            reference = visible[after + 1 : reference_end] or label
            destination = definitions.get(" ".join(reference.casefold().split()))
            raw = text[start : reference_end + 1]
            links.append(
                (raw, _unescape(label), _unescape(destination) if destination is not None else None)
            )
            index = reference_end + 1
            continue
        normalized_label = " ".join(label.casefold().split())
        if normalized_label in definitions:
            destination = definitions[normalized_label]
            raw = text[start : label_end + 1]
            links.append((raw, _unescape(label), _unescape(destination)))
            index = label_end + 1
            continue
        index = label_end + 1

    counts: dict[str, int] = {}
    result: list[MarkdownLink] = []
    for raw, label, destination in links:
        occurrence = counts.get(raw, 0)
        counts[raw] = occurrence + 1
        result.append(MarkdownLink(raw, label, destination, occurrence))
    return result

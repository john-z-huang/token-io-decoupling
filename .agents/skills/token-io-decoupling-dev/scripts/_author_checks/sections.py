"""Layer-01 文档章节结构、顺序和内容校验。"""

from __future__ import annotations

from pathlib import PurePosixPath

from .constants import _HEADING_RE, LAYER01_HEADINGS, LAYER01_NAVIGATION, ZH_SUFFIX
from .links import _advance_fence


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


def _check_layer01_section_content(
    relative: str,
    content: str,
    sections: list[tuple[int, str, int]],
    expected: tuple[str, ...],
    errors: list[str],
) -> None:
    for heading in expected:
        match = next(
            (
                (index, offset)
                for index, (_, found, offset) in enumerate(sections)
                if found == heading
            ),
            None,
        )
        if match is None:
            continue
        index, offset = match
        line_end = content.find("\n", offset)
        start = line_end + 1 if line_end >= 0 else len(content)
        end = sections[index + 1][2] if index + 1 < len(sections) else len(content)
        if not content[start:end].strip():
            errors.append(
                f"{relative}:{sections[index][0]}: 模块 `## {heading}` 为空；"
                "无特别优化时也须明确写明没有"
            )


def layer01_section_issues(path: str, content: str) -> list[str]:
    relative = path
    language = "zh" if PurePosixPath(path).name.endswith(ZH_SUFFIX) else "en"
    expected = LAYER01_HEADINGS[language]
    sections = top_level_sections(content)
    errors: list[str] = []
    for heading in expected:
        occurrences = [(line, offset) for line, found, offset in sections if found == heading]
        if not occurrences:
            errors.append(f"{relative}: 缺少必需标题 `## {heading}`")
        elif len(occurrences) > 1:
            lines = ", ".join(str(line) for line, _ in occurrences)
            errors.append(f"{relative}: 标题 `## {heading}` 重复出现于第 {lines} 行")
    positions = [
        next((i for i, (_, found, _) in enumerate(sections) if found == heading), None)
        for heading in expected
    ]
    known_positions = [position for position in positions if position is not None]
    if len(known_positions) == len(positions) and known_positions != sorted(known_positions):
        errors.append(f"{relative}: 三个必需标题顺序错误；应为通用规范 → Codex → Claude Code")
    allowed = {*expected, LAYER01_NAVIGATION[language]}
    for line, heading, _offset in sections:
        if heading not in allowed:
            errors.append(
                f"{relative}:{line}: 非模块二级标题 `## {heading}`；概念子主题应使用 `###`"
            )
    _check_layer01_section_content(relative, content, sections, expected, errors)
    navigation = next(
        (
            index
            for index, (_, heading, _) in enumerate(sections)
            if heading == LAYER01_NAVIGATION[language]
        ),
        None,
    )
    if navigation is not None and positions[-1] is not None and navigation < positions[-1]:
        errors.append(f"{relative}: 导航章节必须位于三个内容模块之后")
    return errors


def is_layer01_path(path: str) -> bool:
    parts = PurePosixPath(path).parts
    if parts[:3] == ("instruction-compiler", "sources", "skill"):
        parts = parts[3:]
    return parts[:3] == ("references", "coding", "layer-01-fundamental-concepts")

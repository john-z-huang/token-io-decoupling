#!/usr/bin/env python3
"""Check the three required content modules in every bilingual Layer-01 document."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


LAYER_01 = Path("references/coding/layer-01-fundamental-concepts")
HEADINGS = {
    "en": (
        "General rules",
        "Codex CLI / ChatGPT Desktop optimizations",
        "Claude Code CLI / Claude Desktop optimizations",
    ),
    "zh": (
        "通用规范",
        "Codex CLI / ChatGPT Desktop 特别优化指令",
        "Claude Code CLI / Claude Desktop 特别优化指令",
    ),
}
NAVIGATION = {"en": "Related concepts", "zh": "相关概念"}
HEADING = re.compile(r"^## (.+?)\s*$")
FENCE = re.compile(r"^\s*(`{3,}|~{3,})")


def top_level_sections(content: str) -> list[tuple[int, str, int]]:
    """Return line number, heading text, and content offset outside code fences."""
    sections: list[tuple[int, str, int]] = []
    fence_char = ""
    fence_width = 0
    offset = 0
    for number, line in enumerate(content.splitlines(keepends=True), 1):
        marker = FENCE.match(line)
        if marker:
            run = marker.group(1)
            if not fence_char:
                fence_char, fence_width = run[0], len(run)
            elif run[0] == fence_char and len(run) >= fence_width:
                fence_char, fence_width = "", 0
        elif not fence_char and (match := HEADING.match(line.rstrip("\r\n"))):
            sections.append((number, match.group(1), offset))
        offset += len(line)
    return sections


def check_document(path: Path, root: Path) -> list[str]:
    relative = path.relative_to(root)
    language = "zh" if path.name.endswith("_zh_cn.md") else "en"
    expected = HEADINGS[language]
    content = path.read_text(encoding="utf-8")
    sections = top_level_sections(content)
    errors: list[str] = []

    for heading in expected:
        occurrences = [(line, offset) for line, found, offset in sections if found == heading]
        if not occurrences:
            errors.append(f"{relative}: 缺少必需标题 `## {heading}`")
        elif len(occurrences) > 1:
            lines = ", ".join(str(line) for line, _ in occurrences)
            errors.append(f"{relative}: 标题 `## {heading}` 重复出现于第 {lines} 行")

    positions = [next((i for i, (_, found, _) in enumerate(sections) if found == heading), None) for heading in expected]
    if all(position is not None for position in positions) and positions != sorted(positions):
        errors.append(f"{relative}: 三个必需标题顺序错误；应为通用规范 → Codex → Claude Code")

    allowed = {*expected, NAVIGATION[language]}
    for line, heading, _ in sections:
        if heading not in allowed:
            errors.append(f"{relative}:{line}: 非模块二级标题 `## {heading}`；概念子主题应使用 `###`")

    for heading in expected:
        match = next(((i, offset) for i, (_, found, offset) in enumerate(sections) if found == heading), None)
        if match is None:
            continue
        index, offset = match
        line_end = content.find("\n", offset)
        start = line_end + 1 if line_end >= 0 else len(content)
        end = sections[index + 1][2] if index + 1 < len(sections) else len(content)
        if not content[start:end].strip():
            errors.append(f"{relative}:{sections[index][0]}: 模块 `## {heading}` 为空；无特别优化时也须明确写明没有")

    navigation = next((i for i, (_, heading, _) in enumerate(sections) if heading == NAVIGATION[language]), None)
    if navigation is not None and positions[-1] is not None and navigation < positions[-1]:
        errors.append(f"{relative}: 导航章节必须位于三个内容模块之后")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root.resolve()
    directory = root / LAYER_01
    if not directory.is_dir():
        print(f"缺少 Layer-01 目录: {directory}")
        return 1
    documents = sorted(directory.glob("*.md"))
    if not documents:
        print(f"Layer-01 目录没有 Markdown 文档: {directory}")
        return 1
    errors = [error for path in documents for error in check_document(path, root)]
    if errors:
        print("Layer-01 三模块结构检查未通过:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"Layer-01 三模块结构检查通过（{len(documents)} 份 Markdown 文档）。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""核对维护中的 Markdown 本地链接和 Skill 依赖方向。"""

from __future__ import annotations

import sys
from pathlib import Path

from document_rules import document_link_issues
from markdown_discovery import discover_markdown

ROOT = Path(__file__).resolve().parents[1]


def main(root: Path | None = None) -> int:
    root = Path(root or ROOT).absolute()
    documents = {
        path.relative_to(root).as_posix(): path.read_text(encoding="utf-8")
        for path in discover_markdown(root)
    }
    errors = document_link_issues(documents)
    if errors:
        print("文档链接校验失败：", file=sys.stderr)
        print("\n".join(f"- {error}" for error in errors), file=sys.stderr)
        return 1
    print(f"文档链接校验通过，共 {len(documents)} 份 Markdown 文档。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

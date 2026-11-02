#!/usr/bin/env python3
"""Check the three required content modules in every bilingual Layer-01 document."""

from __future__ import annotations

import argparse
from pathlib import Path

from compliance_core_loader import load_compliance_core

_COMPLIANCE_CORE = load_compliance_core()

LAYER_01 = Path("docs/skill/references/coding/layer-01-fundamental-concepts")
HEADINGS = _COMPLIANCE_CORE.LAYER01_HEADINGS
NAVIGATION = _COMPLIANCE_CORE.LAYER01_NAVIGATION
top_level_sections = _COMPLIANCE_CORE.top_level_sections


def check_document(path: Path, root: Path) -> list[str]:
    content = path.read_text(encoding="utf-8")
    return _COMPLIANCE_CORE.layer01_section_issues(
        path.relative_to(root).as_posix(), content
    )


def is_navigation_file(path: Path) -> bool:
    """Navigation pages are validated separately and are never Layer-01 owners."""
    return path.name in {"README.md", "README_zh_cn.md", "INDEX.md", "INDEX_zh_cn.md"}


def discover_owner_documents(directory: Path) -> list[Path]:
    """Recursively discover content owners while excluding explicit navigation files."""
    return sorted(path for path in directory.rglob("*.md") if not is_navigation_file(path))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root.resolve()
    directory = root / LAYER_01
    if not directory.is_dir():
        print(f"缺少 Layer-01 目录: {directory}")
        return 1
    documents = discover_owner_documents(directory)
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

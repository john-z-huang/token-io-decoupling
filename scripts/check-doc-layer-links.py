#!/usr/bin/env python3
"""Validate Markdown dependency direction between Skill document layers."""

from __future__ import annotations

import posixpath
import re
import sys
from pathlib import Path, PurePosixPath

from markdown_discovery import discover_markdown

ROOT = Path(__file__).resolve().parents[1]
LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")
LANGUAGE_SWITCH_LABELS = {"english", "简体中文"}


def layer(path: PurePosixPath) -> str:
    parts = path.parts
    if parts[:3] == ("references", "coding", "layer-01-fundamental-concepts"):
        return "layer-01"
    if parts[:3] == ("references", "coding", "layer-02-workflow-concepts"):
        return "layer-02"
    if parts[:3] == ("references", "coding", "layer-03-workflow-checkpoints"):
        return "layer-03"
    if parts[:3] == ("references", "coding", "layer-04-workflows"):
        return "layer-04"
    if parts[:2] == ("references", "share"):
        return "shared-protocols"
    if parts and parts[0] == "references":
        return "references"
    if parts[:2] == ("workflows", "checkpoint"):
        return "checkpoint"
    if parts[:2] == ("workflows", "exist-workflow"):
        return "exist-workflow"
    if path in {
        PurePosixPath("workflows/coding.md"),
        PurePosixPath("workflows/coding_zh_cn.md"),
    }:
        return "coding-selector"
    return "entry"


def language(path: PurePosixPath) -> str:
    if path.parts[:2] == ("docs", "zh-cn") or path.name.endswith("_zh_cn.md"):
        return "zh"
    return "en"


def is_language_switch(label: str) -> bool:
    return label.strip().casefold() in LANGUAGE_SWITCH_LABELS


def is_navigation_document(path: PurePosixPath) -> bool:
    return path.name in {"README.md", "README_zh_cn.md", "INDEX.md", "INDEX_zh_cn.md"}


def counterpart(path: PurePosixPath) -> PurePosixPath:
    if path.parts[:2] == ("docs", "zh-cn"):
        return PurePosixPath("docs", path.name)
    if path == PurePosixPath("docs/index.md"):
        return PurePosixPath("docs/zh-cn/index.md")
    if path.name.endswith("_zh_cn.md"):
        return path.with_name(path.name.removesuffix("_zh_cn.md") + ".md")
    return path.with_name(path.stem + "_zh_cn.md")


def allowed(source: str, target: str, is_navigation: bool) -> bool:
    same_layer_navigation = is_navigation and source == target
    if source in {"references", "layer-01"}:
        return same_layer_navigation or target == "layer-01"
    if source in {"checkpoint", "layer-02"}:
        return same_layer_navigation or target in {"references", "layer-01"}
    if source in {"exist-workflow", "layer-03"}:
        return same_layer_navigation or target in {"shared-protocols", "layer-01", "layer-02"}
    if source == "layer-04":
        return same_layer_navigation or target in {"shared-protocols", "layer-01", "layer-02", "layer-03"}
    if source == "coding-selector":
        return is_navigation or target in {
            "exist-workflow",
            "layer-01",
            "layer-02",
            "layer-03",
            "layer-04",
        }
    return True


def iter_links(path: Path):
    fenced = False
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.strip().startswith("```"):
            fenced = not fenced
            continue
        if not fenced:
            yield line_number, from_line(line)


def from_line(line: str):
    return LINK_RE.findall(line)


def main(root: Path | None = None) -> int:
    root = Path(root or ROOT).absolute()
    errors: list[str] = []
    markdown_files = sorted(
        PurePosixPath(path.relative_to(root).as_posix()) for path in discover_markdown(root)
    )

    for source in markdown_files:
        source_path = root / source
        source_layer = layer(source)
        source_language = language(source)
        for line_number, links in iter_links(source_path):
            for label, raw_target in links:
                target_text = raw_target.split("#", 1)[0].split("?", 1)[0]
                if (
                    not target_text
                    or "://" in target_text
                    or target_text.startswith(("mailto:", "{{"))
                ):
                    continue
                if not target_text.endswith(".md"):
                    continue
                normalized = posixpath.normpath(str(PurePosixPath(source.parent, target_text)))
                target = PurePosixPath(normalized)
                if target.parts and target.parts[0] == "..":
                    errors.append(
                        f"target escapes repository: {source}:{line_number} -> {target_text}"
                    )
                    continue
                target_path = root / target
                if not target_path.exists():
                    errors.append(f"missing local target: {source}:{line_number} -> {target_text}")
                    continue

                target_language = language(target)
                mirror = target == counterpart(source)
                if source_language != target_language and not (
                    is_language_switch(label) and mirror
                ):
                    errors.append(
                        f"cross-language dependency: {source}:{line_number} -> {target_text}"
                    )
                    continue
                navigation = (
                    mirror
                    or (target == source and is_language_switch(label))
                    or is_navigation_document(source)
                )
                target_layer = layer(target)
                if not allowed(source_layer, target_layer, navigation):
                    errors.append(
                        f"layer violation: {source}:{line_number} ({source_layer}) -> "
                        f"{target} ({target_layer})"
                    )

    if errors:
        print("Document layer validation failed:", file=sys.stderr)
        print("\n".join(f"- {error}" for error in errors), file=sys.stderr)
        return 1
    print(f"Document layer validation passed ({len(markdown_files)} Markdown files).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

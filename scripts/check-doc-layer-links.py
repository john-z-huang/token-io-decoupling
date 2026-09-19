#!/usr/bin/env python3
"""Validate Markdown dependency direction between Skill document layers."""

from __future__ import annotations

import re
import posixpath
import sys
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")
LANGUAGE_SWITCH_LABELS = {"english", "简体中文"}


def layer(path: PurePosixPath) -> str:
    parts = path.parts
    if parts[:3] == ("references", "coding", "layer-01-fundamental-concepts"):
        return "layer-01"
    if parts[:3] == ("references", "coding", "layer-02-workflow-concepts"):
        return "layer-02"
    if parts[:3] == ("references", "coding", "layer-03-workflows"):
        return "layer-03"
    if parts and parts[0] == "references":
        return "references"
    if parts[:2] == ("workflows", "checkpoint"):
        return "checkpoint"
    if parts[:2] == ("workflows", "exist-workflow"):
        return "exist-workflow"
    if path in {PurePosixPath("workflows/coding.md"), PurePosixPath("workflows/coding_zh_cn.md")}:
        return "coding-selector"
    return "entry"


def language(path: PurePosixPath) -> str:
    if path.parts[:2] == ("docs", "zh-cn") or path.name.endswith("_zh_cn.md"):
        return "zh"
    return "en"


def is_language_switch(label: str) -> bool:
    return label.strip().casefold() in LANGUAGE_SWITCH_LABELS


def counterpart(path: PurePosixPath) -> PurePosixPath:
    if path.parts[:2] == ("docs", "zh-cn"):
        return PurePosixPath("docs", path.name)
    if path == PurePosixPath("docs/index.md"):
        return PurePosixPath("docs/zh-cn/index.md")
    if path.name.endswith("_zh_cn.md"):
        return path.with_name(path.name.removesuffix("_zh_cn.md") + ".md")
    return path.with_name(path.stem + "_zh_cn.md")


def allowed(source: str, target: str, is_navigation: bool) -> bool:
    if source in {"references", "layer-01"}:
        return is_navigation
    if source in {"checkpoint", "layer-02"}:
        return is_navigation or target in {"references", "layer-01"}
    if source in {"exist-workflow", "layer-03"}:
        return is_navigation or target in {"references", "layer-01", "layer-02"}
    if source == "coding-selector":
        return is_navigation or target in {"exist-workflow", "layer-01", "layer-02", "layer-03"}
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


def main() -> int:
    errors: list[str] = []
    markdown_files = sorted(
        PurePosixPath(path.relative_to(ROOT).as_posix())
        for path in ROOT.rglob("*.md")
        if ".git" not in path.parts
    )

    for source in markdown_files:
        source_path = ROOT / source
        source_layer = layer(source)
        source_language = language(source)
        for line_number, links in iter_links(source_path):
            for label, raw_target in links:
                target_text = raw_target.split("#", 1)[0].split("?", 1)[0]
                if not target_text or "://" in target_text or target_text.startswith(("mailto:", "{{")):
                    continue
                if not target_text.endswith(".md"):
                    continue
                normalized = posixpath.normpath(str(PurePosixPath(source.parent, target_text)))
                target = PurePosixPath(normalized)
                if target.parts and target.parts[0] == "..":
                    errors.append(f"target escapes repository: {source}:{line_number} -> {target_text}")
                    continue
                target_path = ROOT / target
                if not target_path.exists():
                    errors.append(f"missing local target: {source}:{line_number} -> {target_text}")
                    continue

                target_language = language(target)
                mirror = target == counterpart(source)
                if source_language != target_language and not (is_language_switch(label) and mirror):
                    errors.append(f"cross-language dependency: {source}:{line_number} -> {target_text}")
                    continue
                navigation = mirror or (target == source and is_language_switch(label))
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

#!/usr/bin/env python3
"""Validate historical owner moves and current bilingual Layer-01/02 navigation."""

from __future__ import annotations

import json
import posixpath
import re
import sys
from pathlib import Path, PurePosixPath


MAP = Path("docs/coding-document-migration.json")
LAYERS = ("layer-01-fundamental-concepts", "layer-02-workflow-concepts")
NAVIGATION = {"README.md", "README_zh_cn.md", "INDEX.md", "INDEX_zh_cn.md"}
MARKDOWN_LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")


def _link_target(source: Path, raw_target: str, root: Path) -> str | None:
    target_text = raw_target.strip().split("#", 1)[0].split("?", 1)[0]
    if not target_text or "://" in target_text or target_text.startswith(("mailto:", "{{")):
        return None
    resolved = posixpath.normpath(posixpath.join(source.parent.as_posix(), target_text))
    try:
        return Path(resolved).relative_to(root).as_posix()
    except ValueError:
        return resolved


def _targets(path: Path, root: Path) -> list[str]:
    if not path.is_file():
        return []
    text = path.read_text(encoding="utf-8")
    return [target for raw in MARKDOWN_LINK.findall(text) if (target := _link_target(path, raw, root))]


def _is_safe_relative(raw: str) -> bool:
    path = PurePosixPath(raw)
    return bool(path.parts) and not path.is_absolute() and ".." not in path.parts and "\\" not in raw


def _owner_files(directory: Path) -> list[Path]:
    return sorted(path for path in directory.glob("*.md") if path.name not in NAVIGATION)


def _check_navigation(directory: Path, root: Path, errors: list[str]) -> None:
    for name, mirror_name in (("README.md", "README_zh_cn.md"), ("INDEX.md", "INDEX_zh_cn.md")):
        english, chinese = directory / name, directory / mirror_name
        for path in (english, chinese):
            if not path.is_file():
                errors.append(f"navigation file missing: {path.relative_to(root)}")
        if not english.is_file() or not chinese.is_file():
            continue
        switch = f"[English]({name}) | [简体中文]({mirror_name})"
        if switch not in english.read_text(encoding="utf-8"):
            errors.append(f"incorrect or missing English language switch: {english.relative_to(root)}")
        if switch not in chinese.read_text(encoding="utf-8"):
            errors.append(f"incorrect or missing Chinese language switch: {chinese.relative_to(root)}")

    for filename, target_name in (("README.md", "INDEX.md"), ("README_zh_cn.md", "INDEX_zh_cn.md")):
        path = directory / filename
        if path.is_file():
            targets = _targets(path, root)
            expected = (directory / target_name).relative_to(root).as_posix()
            if targets.count(expected) != 1:
                errors.append(f"README must link exactly once to its same-language index: {path.relative_to(root)}")

    english_index, chinese_index = directory / "INDEX.md", directory / "INDEX_zh_cn.md"
    direct_children = sorted(path for path in directory.iterdir() if path.is_dir())
    for index, suffix in ((english_index, ""), (chinese_index, "_zh_cn")):
        if not index.is_file():
            continue
        targets = _targets(index, root)
        expected_targets = []
        for owner in _owner_files(directory):
            if owner.name.endswith("_zh_cn.md") != bool(suffix):
                continue
            expected_targets.append(owner.relative_to(root).as_posix())
            if expected_targets[-1] not in targets:
                errors.append(f"index omits direct owner {owner.relative_to(root)}")
        for child in direct_children:
            expected_targets.append((child / f"INDEX{suffix}.md").relative_to(root).as_posix())
            if expected_targets[-1] not in targets:
                errors.append(f"index omits direct child directory {child.relative_to(root)}")
        for expected in expected_targets:
            occurrences = targets.count(expected)
            if occurrences > 1:
                errors.append(f"index repeats target {expected}: {index.relative_to(root)}")


def validate(root: Path) -> list[str]:
    errors: list[str] = []
    try:
        migration = json.loads((root / MAP).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"invalid or unreadable migration map: {exc}"]
    if not isinstance(migration, dict) or migration.get("schema_version") != 1:
        errors.append("migration map schema_version must be 1")
    moves = migration.get("document_moves") if isinstance(migration, dict) else None
    if not isinstance(moves, list):
        return errors + ["document_moves must be a list"]

    seen_old: set[str] = set()
    seen_new: set[str] = set()
    for item in moves:
        if not isinstance(item, dict) or not isinstance(item.get("from"), str) or not isinstance(item.get("to"), str):
            errors.append("each migration entry must contain string from/to paths")
            continue
        old, new = item["from"], item["to"]
        old_path, new_path = PurePosixPath(old), PurePosixPath(new)
        if old in seen_old or new in seen_new:
            errors.append(f"duplicate migration mapping: {old} -> {new}")
        seen_old.add(old)
        seen_new.add(new)
        if not _is_safe_relative(old) or not _is_safe_relative(new):
            errors.append(f"unsafe migration mapping: {old} -> {new}")
            continue
        old_layer = old_path.parts[2] if len(old_path.parts) > 2 else None
        if len(old_path.parts) != 4 or old_path.parts[:2] != ("references", "coding") or old_layer not in LAYERS:
            errors.append(f"migration source is not a former Layer-01/02 root owner: {old}")
        if new_path.parts[:3] != ("references", "coding", old_layer) or len(new_path.parts) < 5:
            errors.append(f"migration target is not nested under the same layer: {old} -> {new}")
        if old_path.name != new_path.name or old_path.suffix != ".md":
            errors.append(f"migration changed owner filename: {old} -> {new}")
        if new_path.name in NAVIGATION:
            errors.append(f"migration target is a navigation file: {new}")
        if not (root / new).is_file():
            errors.append(f"mapped target is missing: {new}")
        if (root / old).exists():
            errors.append(f"old owner path still exists: {old}")

    for layer in LAYERS:
        base = root / "references" / "coding" / layer
        if not base.is_dir():
            errors.append(f"layer directory missing: {base.relative_to(root)}")
            continue
        directories = [base, *(path for path in base.rglob("*") if path.is_dir())]
        for directory in sorted(directories):
            _check_navigation(directory, root, errors)
            for owner in _owner_files(directory):
                mirror = owner.with_name(owner.stem + "_zh_cn.md") if not owner.name.endswith("_zh_cn.md") else owner.with_name(owner.name.removesuffix("_zh_cn.md") + ".md")
                if not mirror.is_file():
                    errors.append(f"owner is missing language pair: {owner.relative_to(root)}")

    return errors


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    errors = validate(root)
    if errors:
        print("Coding document migration validation failed:", file=sys.stderr)
        print("\n".join(f"- {error}" for error in errors), file=sys.stderr)
        return 1
    print("Coding document migration validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

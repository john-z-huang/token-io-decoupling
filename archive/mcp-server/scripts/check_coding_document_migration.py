#!/usr/bin/env python3
"""校验历史规则迁移和 Coding 参考目录的 README 导航。"""

from __future__ import annotations

import json
import posixpath
import re
import sys
from pathlib import Path, PurePosixPath


MAP = Path("docs/migrations/coding-document-migration.json")
LAYERS = ("layer-01-fundamental-concepts", "layer-02-workflow-concepts")
NAVIGATION_LAYERS = (*LAYERS, "layer-03-workflow-checkpoints")
NAVIGATION = {"README.md", "INDEX.md"}
MARKDOWN_LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")
# Issue #164 broadens this owner from opt-in planning to the default task plan.
# Keep the exact bilingual migration explicit; unrelated moves retain basename checks.
OWNER_RENAMES = {
    f"skill/references/coding/layer-01-fundamental-concepts/planning-intent-plan-memory-lifecycle{suffix}.md":
    f"skill/references/coding/layer-01-fundamental-concepts/execution-planning/task-plan-memory-lifecycle{suffix}.md"
    for suffix in ("",)
}
OWNER_RENAMES.update({
    f"skill/references/coding/layer-01-fundamental-concepts/enhanced-rule-context{suffix}.md":
    f"skill/references/coding/layer-01-fundamental-concepts/workflow-navigation/rule-context{suffix}.md"
    for suffix in ("", "_zh_cn")
})
OWNER_RENAMES.update({
    f"skill/references/coding/layer-01-fundamental-concepts/enhanced-workflow-availability{suffix}.md":
    f"skill/references/coding/layer-01-fundamental-concepts/workflow-navigation/navigation-availability{suffix}.md"
    for suffix in ("", "_zh_cn")
})


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
    readme = directory / "README.md"
    if (directory / "INDEX.md").exists():
        errors.append(f"移除已并入 README 的索引：{(directory / 'INDEX.md').relative_to(root)}")
    if not readme.is_file():
        errors.append(f"缺少目录导航：{readme.relative_to(root)}")
        return

    # Git 不保留空目录，导航校验也跳过它们。
    direct_children = sorted(path for path in directory.iterdir() if path.is_dir() and any(path.iterdir()))
    targets = _targets(readme, root)
    expected = [*_owner_files(directory), *(child / "README.md" for child in direct_children)]
    for path in expected:
        target = path.relative_to(root).as_posix()
        if targets.count(target) != 1:
            errors.append(f"{readme.relative_to(root)} 应恰好引用一次 {target}")


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
    moves_by_old: dict[str, dict[str, str]] = {}
    for item in moves:
        if not isinstance(item, dict) or not isinstance(item.get("from"), str) or not isinstance(item.get("to"), str):
            errors.append("each migration entry must contain string from/to paths")
            continue
        old, new = item["from"], item["to"]
        moves_by_old[old] = item
        status = item.get("status", "active")
        if status not in {"active", "retired"}:
            errors.append(f"migration status must be active or retired: {old} -> {new}")
            continue
        if status == "retired" and not (isinstance(item.get("reason"), str) and item["reason"].strip()):
            errors.append(f"retired migration must explain why no current target exists: {old} -> {new}")
        old_path, new_path = PurePosixPath(old), PurePosixPath(new)
        if old in seen_old or new in seen_new:
            errors.append(f"duplicate migration mapping: {old} -> {new}")
        seen_old.add(old)
        seen_new.add(new)
        if not _is_safe_relative(old) or not _is_safe_relative(new):
            errors.append(f"unsafe migration mapping: {old} -> {new}")
            continue
        old_layer = old_path.parts[3] if len(old_path.parts) > 3 else None
        if len(old_path.parts) != 5 or old_path.parts[:3] != ("skill", "references", "coding") or old_layer not in LAYERS:
            errors.append(f"migration source is not a former Layer-01/02 root owner: {old}")
        if new_path.parts[:4] != ("skill", "references", "coding", old_layer) or len(new_path.parts) < 6:
            errors.append(f"migration target is not nested under the same layer: {old} -> {new}")
        if (old_path.name != new_path.name and OWNER_RENAMES.get(old) != new) or old_path.suffix != ".md":
            errors.append(f"migration changed owner filename: {old} -> {new}")
        if new_path.name in NAVIGATION:
            errors.append(f"migration target is a navigation file: {new}")
        if status == "active" and not (root / new).is_file():
            errors.append(f"mapped target is missing: {new}")
        if status == "retired" and (root / new).exists():
            errors.append(f"retired migration unexpectedly has a current target: {new}")
        if (root / old).exists():
            errors.append(f"old owner path still exists: {old}")

    for layer in NAVIGATION_LAYERS:
        base = root / "skill/references" / "coding" / layer
        if not base.is_dir():
            errors.append(f"layer directory missing: {base.relative_to(root)}")
            continue
        directories = [base, *(path for path in base.rglob("*") if path.is_dir() and any(path.iterdir()))]
        for directory in sorted(directories):
            _check_navigation(directory, root, errors)

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

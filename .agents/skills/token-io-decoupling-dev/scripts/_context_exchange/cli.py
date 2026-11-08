"""Validate the ignored Context Exchange directory and optional bootstrap capsule."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .capsule import validate_capsule
from .coordination import check_ignore_policy, validate_hierarchy


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[5])
    parser.add_argument(
        "--allow-stale",
        action="store_true",
        help="report, but do not reject, snapshot drift while inspecting a capsule during refresh",
    )
    args = parser.parse_args()
    root = args.root.resolve()
    errors: list[str] = []
    warnings: list[str] = []
    try:
        hierarchy_safe = validate_hierarchy(root, errors)
        if hierarchy_safe:
            validate_capsule(root, errors, warnings, not args.allow_stale)
        # 完成目录、胶囊及来源路径的 lstat 检查后，才能创建探针文件。
        check_ignore_policy(root, errors, write_sentinel=hierarchy_safe and not errors)
    except (OSError, UnicodeError, RuntimeError) as exc:
        errors.append(str(exc))

    for warning in warnings:
        print(f"Warning: {warning}", file=sys.stderr)
    if errors:
        print("Context Exchange validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("Context Exchange validation passed.")
    return 0

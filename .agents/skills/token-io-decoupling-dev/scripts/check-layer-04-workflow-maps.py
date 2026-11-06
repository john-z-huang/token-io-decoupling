#!/usr/bin/env python3
"""保留既有校验入口，验证短 workflow 与 Hook 契约而非执行拓扑。"""

from __future__ import annotations

import argparse
from pathlib import Path

from workflow_checks.contracts import ROOT, main
from workflow_checks.sources import validate_source_map


def validate_migration_manifest(root: Path, errors: list[str]) -> dict:
    """旧检查入口复用当前来源验证，仍检查历史覆盖和真实替代 Hook。"""
    return validate_source_map(root, errors)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    raise SystemExit(main(args.root.resolve()))

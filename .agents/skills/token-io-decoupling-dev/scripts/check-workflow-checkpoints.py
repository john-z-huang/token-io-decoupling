#!/usr/bin/env python3
"""检查事件 Hook 的文档契约与来源整合，不再强制编号阶段。"""

from __future__ import annotations

import argparse
from pathlib import Path

from workflow_checks.contracts import ROOT, main

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    raise SystemExit(main(args.root.resolve()))

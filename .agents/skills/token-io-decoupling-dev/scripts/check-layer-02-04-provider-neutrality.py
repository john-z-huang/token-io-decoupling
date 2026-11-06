#!/usr/bin/env python3
"""校验当前 Hook 契约及完整历史来源，不再要求已退役的分层目录。"""

import argparse
from pathlib import Path

from workflow_checks.contracts import ROOT, main

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    raise SystemExit(main(args.root.resolve()))

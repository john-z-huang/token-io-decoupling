#!/usr/bin/env python3
"""检查中文单源文档、入口、链接与产品中立边界。"""

import argparse
from pathlib import Path

from workflow_checks.chinese import ROOT, main

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    raise SystemExit(main(args.root))

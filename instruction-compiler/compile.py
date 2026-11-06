#!/usr/bin/env python3
"""Run the private compiler without installing it into the product environment."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from token_io_instruction_compiler.compiler import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())

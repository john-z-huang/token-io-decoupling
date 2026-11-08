"""将审核后的作者指令编译为同批静态资源，不实现业务流程执行器。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from token_io_instruction_compiler.sources import (
    CompilationError,
)

from .pipeline import MAX_INSTRUCTION_CHARS, compile_repository


def main(argv: list[str] | None = None) -> int:
    """解析开发 CLI 参数，成功输出构建摘要，已知编译故障以非零状态结束。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", nargs="?", choices=["compile"], default="compile")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[4])
    parser.add_argument("--max-chars", type=int, default=MAX_INSTRUCTION_CHARS)
    args = parser.parse_args(argv)
    try:
        result = compile_repository(args.root, check=args.check, max_chars=args.max_chars)
    except (CompilationError, OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"instruction compilation failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0

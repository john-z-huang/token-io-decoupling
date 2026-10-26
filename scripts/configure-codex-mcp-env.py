#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["tomlkit>=0.15,<1"]
# ///
"""Merge environment variable names into selected existing Codex MCP servers."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mcp" / "src"))

from token_io_decoupling.codex_env import (  # noqa: E402
    DEFAULT_ENV_VARS,
    CodexEnvError,
    config_path,
    merge_env_vars,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, help="Codex config.toml path")
    parser.add_argument(
        "--server", action="append", required=True, metavar="NAME", help="existing stdio server"
    )
    parser.add_argument(
        "--env-var",
        action="append",
        metavar="NAME",
        help="environment variable name to forward (default: OPENAI_API_KEY and OPENAI_BASE_URL)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="show proposed names without writing"
    )
    args = parser.parse_args()
    path = config_path(args.config)
    names = tuple(args.env_var) if args.env_var else DEFAULT_ENV_VARS
    try:
        changed = merge_env_vars(path, tuple(args.server), names, dry_run=args.dry_run)
    except CodexEnvError as exc:
        print(f"configure-codex-mcp-env: {exc}", file=sys.stderr)
        return 2
    if args.dry_run:
        print(f"Would merge env_vars {list(names)!r} into: {', '.join(args.server)}")
    elif changed:
        print(f"Updated env_vars in: {', '.join(changed)}")
    else:
        print("No changes needed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

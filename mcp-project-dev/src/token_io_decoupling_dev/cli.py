"""Command-line entry point for the development MCP server."""

from __future__ import annotations

import argparse
from pathlib import Path

from token_io_decoupling_dev import __version__
from token_io_decoupling_dev.compiler import CompileError
from token_io_decoupling_dev.server import create_server


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="token-io-decoupling-dev",
        description=(
            "Run the standalone development MCP server over stdio. Supply an absolute "
            "--project-root at startup to enable fixed-path compiler tools; without it only "
            "capability discovery is available."
        ),
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        help="absolute trusted repository root, pinned for this server process",
    )
    parser.add_argument(
        "--stdio",
        action="store_true",
        help="use stdio transport (the default and only supported transport)",
    )
    parser.add_argument("--version", action="version", version=__version__)
    return parser


def main() -> None:
    """Run the MCP server using its only supported transport."""
    parser = build_parser()
    args = parser.parse_args()
    try:
        server = create_server(args.project_root)
    except (CompileError, OSError) as exc:
        parser.error(str(exc))
    server.run(transport="stdio")

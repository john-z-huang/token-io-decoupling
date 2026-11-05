"""Command-line entry point for the development MCP server."""

from __future__ import annotations

import argparse

from token_io_decoupling_dev import __version__
from token_io_decoupling_dev.server import create_server


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="token-io-decoupling-dev",
        description=(
            "Run the standalone development MCP server over stdio. The server currently "
            "provides read-only capability discovery only."
        ),
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
    build_parser().parse_args()
    create_server().run(transport="stdio")

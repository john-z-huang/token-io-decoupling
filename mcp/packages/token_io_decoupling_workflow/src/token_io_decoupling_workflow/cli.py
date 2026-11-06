"""Independent workflow stdio and registration entrypoint."""

from __future__ import annotations

import argparse
import sys
from importlib.metadata import PackageNotFoundError, version

from token_io_decoupling_workflow.server import create_workflow_server


def run(prog: str, argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog=prog, description="Start the workflow MCP server.")
    try:
        package_version = version("token-io-decoupling-workflow")
    except PackageNotFoundError:
        package_version = "0.1.0"
    parser.add_argument("--version", action="version", version=f"{prog} {package_version}")
    parser.parse_args(argv)
    try:
        create_workflow_server().run(transport="stdio")
    except Exception:
        print(f"{prog}: server startup failed", file=sys.stderr)
        return 2
    return 0


def main() -> int:
    if sys.argv[1:3] == ["setup", "codex"]:
        from token_io_decoupling_transport.setup_codex import dispatch_setup

        return dispatch_setup("workflow", sys.argv[3:])
    return run("token-io-decoupling-workflow", sys.argv[1:])

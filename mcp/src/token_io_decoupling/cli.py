"""Administrative CLI and lazy compatibility entrypoints."""

from __future__ import annotations

import sys

from token_io_decoupling.cli_commands import dispatch_command


def main() -> int:
    return dispatch_command("token-io-decoupling", sys.argv[1:])


def _run_workflow(prog: str, argv: list[str]) -> int:
    from token_io_decoupling_workflow.cli import run

    return run(prog, argv)


def _run_tools(prog: str, argv: list[str]) -> int:
    from token_io_decoupling_tools.cli import run

    return run(prog, argv)


def workflow_main() -> int:
    return _run_workflow("token-io-decoupling-workflow", sys.argv[1:])


def tools_main() -> int:
    return _run_tools("token-io-decoupling-tools", sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())

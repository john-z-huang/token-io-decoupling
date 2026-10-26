"""Command parser and setup dispatch for the unified executable."""

from __future__ import annotations

import argparse
import sys
from importlib.metadata import PackageNotFoundError, version
from typing import Any, cast

from token_io_decoupling_core.profiles import PROFILE_SERVER_NAMES

from token_io_decoupling.setup_codex import SetupError, setup_codex


def dispatch_command(
    prog: str, default_profile: str | None, argv: list[str]
) -> argparse.Namespace | int:
    """Return parsed startup options, or an exit code for admin commands."""
    parser = argparse.ArgumentParser(
        prog=prog,
        description="Start a profile-scoped MCP server or configure Codex CLI.",
        epilog=(
            "Commands: start-mcp-server [--profile PROFILE] (also the default); "
            "setup codex [--profile PROFILE] [--dry-run] [--replace]."
        ),
    )
    try:
        package_version = version("token-io-decoupling")
    except PackageNotFoundError:
        package_version = "0.1.0"
    parser.add_argument("--version", action="version", version=f"{prog} {package_version}")
    _add_runtime_options(parser, default_profile=default_profile)
    commands = parser.add_subparsers(dest="command")
    start = commands.add_parser("start-mcp-server", help="start the stdio MCP server")
    _add_runtime_options(start, default_profile=default_profile, subparser=True)
    start.add_argument("--version", action="version", version=f"{prog} {package_version}")
    start.add_argument("--profile", choices=tuple(PROFILE_SERVER_NAMES), default=default_profile)
    setup = commands.add_parser("setup", help="configure an MCP client")
    targets = setup.add_subparsers(dest="target", required=True)
    codex = targets.add_parser("codex", help="register profiles with Codex CLI")
    codex.add_argument("--profile", choices=tuple(PROFILE_SERVER_NAMES))
    codex.add_argument("--all", action="store_true", help="explicitly configure all profiles")
    codex.add_argument("--dry-run", action="store_true")
    codex.add_argument("--replace", action="store_true")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 2
    if args.command == "setup":
        if args.host_fd is not None or args.codex_context:
            print(f"{prog}: host binding options cannot be used with setup", file=sys.stderr)
            return 2
        if args.profile and args.all:
            print(f"{prog}: --profile cannot be combined with --all", file=sys.stderr)
            return 2
        try:
            return setup_codex(
                profile=args.profile,
                all_profiles=args.all or args.profile is None,
                dry_run=args.dry_run,
                replace=args.replace,
            )
        except SetupError as exc:
            print(f"{prog}: {exc}", file=sys.stderr)
            return 2
    if args.profile is None and default_profile is None:
        # Legacy module invocation remains public-only when no explicit profile is selected.
        args.profile = None
    elif args.profile is None:
        args.profile = default_profile
    return args


def _add_runtime_options(
    parser: argparse.ArgumentParser, *, default_profile: str | None, subparser: bool = False
) -> None:
    suppressed = cast(Any, argparse.SUPPRESS)
    parser.add_argument(
        "--host-fd",
        type=int,
        metavar="INTEGER",
        default=suppressed if subparser else None,
    )
    parser.add_argument(
        "--codex-context",
        action="store_true",
        default=suppressed if subparser else False,
    )
    if not subparser:
        parser.set_defaults(profile=default_profile)

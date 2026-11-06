"""Command parser and setup dispatch for the unified executable."""

from __future__ import annotations

import argparse
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from token_io_decoupling_transport.codex_env import (
    DEFAULT_ENV_VARS,
    CodexEnvError,
    config_path,
    merge_env_vars,
)
from token_io_decoupling_transport.setup_codex import SetupError, setup_codex


def dispatch_command(prog: str, argv: list[str]) -> int:
    """Run only administrative commands; MCP servers have separate fixed entry points."""
    parser = argparse.ArgumentParser(
        prog=prog,
        description="Configure the local MCP servers or manage the bundled Skill.",
    )
    try:
        package_version = version("token-io-decoupling")
    except PackageNotFoundError:
        package_version = "0.1.0"
    parser.add_argument("--version", action="version", version=f"{prog} {package_version}")
    commands = parser.add_subparsers(dest="command", required=True)

    setup = commands.add_parser("setup", help="configure a Codex MCP service")
    targets = setup.add_subparsers(dest="target", required=True)
    codex = targets.add_parser("codex", help="register both local MCP servers")
    codex.add_argument("--dry-run", action="store_true")
    codex.add_argument("--server", choices=("tools", "workflow", "both"), default="both")
    codex_env = targets.add_parser(
        "codex-env", help="merge environment variable names into existing Codex servers"
    )
    codex_env.add_argument("--config", type=Path)
    codex_env.add_argument("--server", action="append", required=True, metavar="NAME")
    codex_env.add_argument("--env-var", action="append", metavar="NAME")
    codex_env.add_argument("--dry-run", action="store_true")

    skills = commands.add_parser("skills", help="install or update the bundled Skill")
    actions = skills.add_subparsers(dest="skill_action", required=True)
    for action in ("install", "update"):
        command = actions.add_parser(action)
        command.add_argument("--name", default="token-io-decoupling-skill")

    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 2

    if args.command == "skills":
        from token_io_decoupling.skills import install_skill

        try:
            target = install_skill(name=args.name, update=args.skill_action == "update")
        except (OSError, ValueError) as exc:
            print(f"{prog}: {exc}", file=sys.stderr)
            return 2
        print(f"Skill {args.skill_action}: {target}")
        return 0

    if args.target == "codex-env":
        try:
            names = tuple(args.env_var) if args.env_var else DEFAULT_ENV_VARS
            changed = merge_env_vars(
                config_path(args.config), tuple(args.server), names, dry_run=args.dry_run
            )
        except CodexEnvError as exc:
            print(f"{prog}: {exc}", file=sys.stderr)
            return 2
        if args.dry_run:
            print(f"Would merge env_vars {list(names)!r} into: {', '.join(args.server)}")
        elif changed:
            print("updated environment forwarding: " + ", ".join(changed))
        else:
            print("environment forwarding already configured: " + ", ".join(args.server))
        return 0

    try:
        return setup_codex(dry_run=args.dry_run, server=args.server)
    except SetupError as exc:
        print(f"{prog}: {exc}", file=sys.stderr)
        return 2

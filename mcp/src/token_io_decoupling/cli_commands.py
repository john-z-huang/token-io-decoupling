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
    """仅派发安装管理命令；MCP 服务各有独立固定入口。"""
    parser = argparse.ArgumentParser(
        prog=prog,
        description="配置本地 MCP 服务或管理包内 Skill。",
    )
    try:
        package_version = version("token-io-decoupling")
    except PackageNotFoundError:
        package_version = "0.1.0"
    parser.add_argument("--version", action="version", version=f"{prog} {package_version}")
    commands = parser.add_subparsers(dest="command", required=True)

    setup = commands.add_parser("setup", help="配置 Codex MCP 服务")
    targets = setup.add_subparsers(dest="target", required=True)
    codex = targets.add_parser("codex", help="注册两个本地 MCP 服务")
    codex.add_argument("--dry-run", action="store_true")
    codex.add_argument("--server", choices=("tools", "workflow", "both"), default="both")
    codex_env = targets.add_parser("codex-env", help="将环境变量名称合并到已有 Codex 服务配置")
    codex_env.add_argument("--config", type=Path)
    codex_env.add_argument("--server", action="append", required=True, metavar="NAME")
    codex_env.add_argument("--env-var", action="append", metavar="NAME")
    codex_env.add_argument("--dry-run", action="store_true")

    skills = commands.add_parser("skills", help="安装或更新包内 Skill")
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

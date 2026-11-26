"""Skill 管理命令；与 stdio 共用唯一可执行入口。"""

from __future__ import annotations

import argparse
import sys

from token_io_decoupling import skills


def dispatch_command(prog: str, argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog=prog)
    commands = parser.add_subparsers(dest="command", required=True)
    skill_parser = commands.add_parser("skills", help="安装或更新 Pi Skill")
    actions = skill_parser.add_subparsers(dest="skill_action", required=True)
    for action in ("install", "update"):
        actions.add_parser(action).add_argument("--name", default=skills.DEFAULT_NAME)
    args = parser.parse_args(argv)
    try:
        target = skills.install_skill(name=args.name, update=args.skill_action == "update")
    except (OSError, ValueError) as exc:
        print(f"{prog}: {exc}", file=sys.stderr)
        return 2
    print(f"Skill {args.skill_action}: {target}")
    return 0

"""默认处理一次原生事件；setup 只负责显式注册。"""

from __future__ import annotations

import argparse
import json
import sys
import sysconfig
from importlib.metadata import version
from pathlib import Path

from token_io_decoupling_hooks.registration import default_hooks_path, register_hooks


def _setup(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="注册 token-io-decoupling 的 Codex Hooks。")
    parser.add_argument("client", choices=("codex",))
    parser.add_argument("--hooks-file", type=Path, default=default_hooks_path())
    parser.add_argument("--dry-run", action="store_true")
    options = parser.parse_args(argv)
    executable = Path(sysconfig.get_path("scripts")) / "token-io-decoupling-hooks"
    try:
        result = register_hooks(options.hooks_file, executable, dry_run=options.dry_run)
    except (OSError, ValueError):
        print("无法注册 Hooks；请检查配置格式、路径与写入权限。", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


def main(argv: list[str] | None = None) -> int:
    """复用 workflow 的有界协议，保留所有显式选项与非阻塞故障语义。"""
    arguments = sys.argv[1:] if argv is None else argv
    if arguments[:1] == ["setup"]:
        try:
            return _setup(arguments[1:])
        except SystemExit as exc:
            return 0 if exc.code == 0 else 1
    if arguments == ["--version"]:
        print(f"token-io-decoupling-hooks {version('token-io-decoupling-hooks')}")
        return 0
    from token_io_decoupling_workflow.events.cli import run_hook

    return run_hook("token-io-decoupling-hooks", arguments)

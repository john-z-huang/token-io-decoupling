"""Independent workflow stdio and registration entrypoint."""

from __future__ import annotations

import argparse
import sys
from importlib.metadata import PackageNotFoundError, version

from token_io_decoupling_workflow.advisory.models import DecisionsRuntimeConfig
from token_io_decoupling_workflow.server import create_workflow_server


def run(prog: str, argv: list[str]) -> int:
    """装配独立 workflow 服务；事件建议必须通过专用启动开关启用。"""
    if argv[:1] == ["hook"]:
        from token_io_decoupling_workflow.events.cli import run_hook

        return run_hook(prog + " hook", argv[1:])
    parser = argparse.ArgumentParser(prog=prog, description="启动 workflow MCP 服务。")
    try:
        package_version = version("token-io-decoupling-workflow")
    except PackageNotFoundError:
        package_version = "0.1.0"
    parser.add_argument("--version", action="version", version=f"{prog} {package_version}")
    parser.add_argument(
        "--enable-event-advice",
        action="store_true",
        help="启用可选事件建议；每次请求仍须获得数据外发许可。",
    )
    options = parser.parse_args(argv)
    try:
        event_config = DecisionsRuntimeConfig(
            enabled=options.enable_event_advice,
            outbound_data_permitted=options.enable_event_advice,
        )
        create_workflow_server(event_advice_config=event_config).run(transport="stdio")
    except Exception:
        print(f"{prog}: server startup failed", file=sys.stderr)
        return 2
    return 0


def main() -> int:
    if sys.argv[1:3] == ["setup", "codex"]:
        from token_io_decoupling_transport.setup_codex import dispatch_setup

        return dispatch_setup("workflow", sys.argv[3:])
    return run("token-io-decoupling-workflow", sys.argv[1:])

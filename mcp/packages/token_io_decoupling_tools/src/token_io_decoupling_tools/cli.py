"""Independent tools stdio and registration entrypoint."""

from __future__ import annotations

import argparse
import sys
from importlib.metadata import PackageNotFoundError, version

from token_io_decoupling_tools.compliance_factory import (
    ComplianceFactoryError,
    load_compliance_service,
)
from token_io_decoupling_tools.output_materializer_factory import (
    OutputMaterializerFactoryError,
    load_output_materializer_config,
)
from token_io_decoupling_tools.server import create_tools_server
from token_io_decoupling_tools.task_plan_factory import TaskPlanFactoryError, load_task_plan_service


def run(prog: str, argv: list[str]) -> int:
    """按明确 factory 配置启动 tools 服务，并在退出时释放本次创建的资源。"""
    parser = argparse.ArgumentParser(prog=prog, description="启动聚合 tools MCP 服务。")
    try:
        package_version = version("token-io-decoupling-tools")
    except PackageNotFoundError:
        package_version = "0.1.0"
    parser.add_argument("--version", action="version", version=f"{prog} {package_version}")
    parser.add_argument("--task-plan-factory", metavar="MODULE:CALLABLE")
    parser.add_argument(
        "--compliance-factory",
        metavar="MODULE:CALLABLE",
        help="明确加载可信操作者代码，返回只读合规检查服务",
    )
    parser.add_argument(
        "--output-materializer-factory",
        metavar="MODULE:CALLABLE",
        help=("明确加载可信操作者代码，返回有界输出物化配置"),
    )
    args = parser.parse_args(argv)

    compliance_service = None
    server = None
    try:
        try:
            task_plan_service = load_task_plan_service(args.task_plan_factory)
        except TaskPlanFactoryError as exc:
            print(f"{prog}: task-plan startup factory failed ({exc.reason})", file=sys.stderr)
            return 2
        try:
            compliance_service = load_compliance_service(args.compliance_factory)
        except ComplianceFactoryError as exc:
            print(f"{prog}: compliance startup factory failed ({exc.reason})", file=sys.stderr)
            return 2
        try:
            output_materializer_config = load_output_materializer_config(
                args.output_materializer_factory
            )
        except OutputMaterializerFactoryError as exc:
            print(
                f"{prog}: output-materializer startup factory failed ({exc.reason})",
                file=sys.stderr,
            )
            return 2
        server = create_tools_server(
            task_plan_service=task_plan_service,
            compliance_service=compliance_service,
            output_materializer_config=output_materializer_config,
        )
        server.run(transport="stdio")
    except Exception:
        print(f"{prog}: server startup failed", file=sys.stderr)
        return 2
    finally:
        output_materializer = getattr(server, "_output_materializer", None)
        close_materializer = getattr(output_materializer, "close", None)
        if callable(close_materializer):
            close_materializer()
        if compliance_service is not None:
            compliance_service.close()
    return 0


def main() -> int:
    if sys.argv[1:3] == ["setup", "codex"]:
        from token_io_decoupling_transport.setup_codex import dispatch_setup

        return dispatch_setup("tools", sys.argv[3:])
    return run("token-io-decoupling-tools", sys.argv[1:])

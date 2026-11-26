"""唯一 tools stdio 入口及 Pi Skill 管理命令。"""

from __future__ import annotations

import argparse
import sys
from importlib.metadata import PackageNotFoundError, version

from token_io_decoupling.cli_commands import dispatch_command
from token_io_decoupling.compliance_factory import (
    ComplianceFactoryError,
    load_compliance_service,
)
from token_io_decoupling.output_materializer_factory import (
    OutputMaterializerFactoryError,
    load_output_materializer_config,
)
from token_io_decoupling.server import create_tools_server


def _run_tools(prog: str, argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog=prog, description="Start the aggregate tools MCP server.")
    try:
        package_version = version("token-io-decoupling")
    except PackageNotFoundError:
        package_version = "0.1.0"
    parser.add_argument("--version", action="version", version=f"{prog} {package_version}")
    parser.add_argument(
        "--compliance-factory",
        metavar="MODULE:CALLABLE",
        help="explicitly load trusted operator code that returns a read-only compliance service",
    )
    parser.add_argument(
        "--output-materializer-factory",
        metavar="MODULE:CALLABLE",
        help=(
            "explicitly load trusted operator code that returns a bounded output-materializer "
            "configuration"
        ),
    )
    args = parser.parse_args(argv)

    compliance_service = None
    server = None
    try:
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


def tools_main() -> int:
    argv = sys.argv[1:]
    if argv and argv[0] == "skills":
        return dispatch_command("token-io-decoupling-tools", argv)
    return _run_tools("token-io-decoupling-tools", argv)


if __name__ == "__main__":
    raise SystemExit(tools_main())

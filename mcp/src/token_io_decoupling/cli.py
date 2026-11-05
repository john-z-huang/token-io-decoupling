"""Unified installed CLI for the Token I/O MCP role profiles."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from token_io_decoupling_core.binding import BindingError
from token_io_decoupling_core.profiles import PROFILE_SERVER_NAMES

from token_io_decoupling.cli_commands import dispatch_command
from token_io_decoupling.compliance_factory import (
    ComplianceFactoryError,
    load_compliance_service,
)
from token_io_decoupling.output_materializer_factory import (
    OutputMaterializerFactoryError,
    load_output_materializer_config,
)
from token_io_decoupling.server import create_server
from token_io_decoupling.task_plan_factory import (
    TaskPlanFactoryError,
    load_task_plan_service,
)


def _trusted_state_root() -> Path:
    """Resolve canonical state under the CLI process's OS account, never caller HOME."""
    try:
        import pwd

        effective_uid = getattr(os, "geteuid", None)
        if effective_uid is None:
            raise ValueError("effective UID is unavailable")
        home = Path(pwd.getpwuid(effective_uid()).pw_dir)
        if not home.is_absolute():
            raise ValueError("OS account home is not absolute")
        return home / ".local" / "state" / "token-io-decoupling"
    except (AttributeError, ImportError, KeyError, OSError, TypeError, ValueError) as exc:
        raise BindingError("trusted OS account state location is unavailable") from exc


def _run(*, prog: str, default_profile: str | None) -> int:
    result = dispatch_command(prog, default_profile, sys.argv[1:])
    if isinstance(result, int):
        return result
    args = result
    profile = args.profile
    compliance_service = None
    output_materializer_config = None
    server = None
    try:
        try:
            task_plan_service = load_task_plan_service(args.task_plan_factory)
        except TaskPlanFactoryError as exc:
            print(
                f"{prog}: task-plan startup factory failed ({exc.reason})",
                file=sys.stderr,
            )
            return 2
        try:
            compliance_service = load_compliance_service(args.compliance_factory)
        except ComplianceFactoryError as exc:
            print(
                f"{prog}: compliance startup factory failed ({exc.reason})",
                file=sys.stderr,
            )
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
        server = create_server(
            state_root=_trusted_state_root(),
            task_plan_service=task_plan_service,
            compliance_service=compliance_service,
            output_materializer_config=output_materializer_config,
            profile=profile,
            server_name=(PROFILE_SERVER_NAMES[profile] if profile is not None else None),
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
    return _run(prog="token-io-decoupling", default_profile="workflow")


def legacy_main() -> int:
    """Preserve the historical module CLI's public-only default server."""
    return _run(prog="token-io-mcp", default_profile=None)


if __name__ == "__main__":
    raise SystemExit(legacy_main())

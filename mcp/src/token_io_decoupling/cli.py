"""Unified installed CLI for the Token I/O MCP role profiles."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from token_io_decoupling_core.binding import BindingError
from token_io_decoupling_core.host_binding import HostChannelBindingProvider
from token_io_decoupling_core.profiles import PROFILE_SERVER_NAMES

from token_io_decoupling.cli_commands import dispatch_command
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
    if args.codex_context and args.host_fd is None:
        print(f"{prog}: --codex-context requires --host-fd", file=sys.stderr)
        return 2
    provider = None
    if args.host_fd is not None:
        try:
            provider = HostChannelBindingProvider.from_fd(args.host_fd)
        except (BindingError, OSError, ValueError):
            print(f"{prog}: authenticated host channel unavailable", file=sys.stderr)
            return 2
    try:
        try:
            task_plan_service = load_task_plan_service(args.task_plan_factory)
        except TaskPlanFactoryError as exc:
            print(
                f"{prog}: task-plan startup factory failed ({exc.reason})",
                file=sys.stderr,
            )
            return 2
        server = create_server(
            provider,
            require_bound=provider is not None,
            require_codex_context=args.codex_context,
            state_root=_trusted_state_root() if provider is not None else None,
            task_plan_service=task_plan_service,
            profile=profile,
            server_name=(PROFILE_SERVER_NAMES[profile] if profile is not None else None),
        )
        server.run(transport="stdio")
    except Exception:
        print(f"{prog}: server startup failed", file=sys.stderr)
        return 2
    finally:
        if provider is not None:
            provider.close()
    return 0


def main() -> int:
    return _run(prog="token-io-decoupling", default_profile="workflow")


def legacy_main() -> int:
    """Preserve the historical module CLI's public-only default server."""
    return _run(prog="token-io-mcp", default_profile=None)


if __name__ == "__main__":
    raise SystemExit(legacy_main())

"""Test-only subprocess harness; never imported or exposed by the production CLI."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import cast

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from token_io_decoupling_core.binding import BindingProvider
from token_io_decoupling_core.workflow_models import (
    BindingIdentity,
    HostCapability,
    HostGuard,
    SessionRole,
)

from token_io_decoupling.server import create_tools_server


class TestOnlyBindingProvider:
    """Synthetic test identity; it is not evidence of a real host binding."""

    def __init__(self, role: SessionRole) -> None:
        self.role = role
        self.identity = BindingIdentity(
            project_id="test-project",
            root_session_id="root-session",
            current_session_id=(
                "stdio-test-worker" if role is SessionRole.WORKER else "root-session"
            ),
            role=role,
            capabilities=frozenset(HostCapability),
            guards=frozenset(HostGuard),
            parent_session_id=("root-session" if role is SessionRole.WORKER else None),
        )

    def current_binding(self) -> BindingIdentity:
        return self.identity


def main() -> None:
    if len(sys.argv) != 3 or sys.argv[1] not in {"root", "worker"}:
        raise SystemExit("usage is private to tests")
    role = SessionRole.PARENT if sys.argv[1] == "root" else SessionRole.WORKER
    server = create_tools_server(cast(BindingProvider, TestOnlyBindingProvider(role)))
    server.run(transport="stdio")


if __name__ == "__main__":
    main()

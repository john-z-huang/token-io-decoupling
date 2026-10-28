"""Test-only subprocess harness; never imported or exposed by the production CLI."""

from __future__ import annotations

import socket
import sys
import threading
from pathlib import Path
from typing import cast

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from token_io_decoupling_core import host_binding
from token_io_decoupling_core.binding import BindingError, BindingProvider
from token_io_decoupling_core.host_binding import serve_host_binding_channel
from token_io_decoupling_core.state_models import (
    BindingIdentity,
    HostCapability,
    HostGuard,
    SessionRole,
    VerifiedChildBinding,
)

from token_io_decoupling import cli
from token_io_decoupling.server import create_server


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

    def verify_child_binding(
        self, parent: BindingIdentity, child_session_id: str
    ) -> VerifiedChildBinding:
        del parent
        if self.role is not SessionRole.PARENT or child_session_id != "stdio-test-worker":
            raise BindingError("test harness has no matching child identity")
        return VerifiedChildBinding(
            project_id="test-project",
            root_session_id="root-session",
            parent_session_id="root-session",
            child_session_id=child_session_id,
            capabilities=frozenset(HostCapability),
            guards=frozenset(HostGuard),
        )


def main() -> None:
    if (
        len(sys.argv) == 4
        and sys.argv[1] in {"bridge", "bridge-codex"}
        and sys.argv[2] in {"root", "worker"}
    ):
        require_codex_context = sys.argv[1] == "bridge-codex"
        role = SessionRole.PARENT if sys.argv[2] == "root" else SessionRole.WORKER
        provider = TestOnlyBindingProvider(role)
        client_socket, host_socket = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)

        # Synthetic kernel-auth bypass exists only inside this explicitly test-only process.
        def synthetic_peer_uid(_sock: socket.socket) -> int:
            return 0

        host_binding.__dict__["_peer_uid"] = synthetic_peer_uid
        host_thread = threading.Thread(
            target=serve_host_binding_channel,
            args=(host_socket, provider),
            daemon=True,
        )
        host_thread.start()
        temporary_state_root = Path(sys.argv[3])
        original_create_server = cli.create_server

        def test_only_server(
            binding_provider,
            *,
            require_bound=False,
            require_codex_context=False,
            state_root=None,
            profile=None,
            server_name=None,
        ):
            del state_root
            return original_create_server(
                binding_provider,
                require_bound=require_bound,
                require_codex_context=require_codex_context,
                state_root=temporary_state_root,
                profile=profile,
                server_name=server_name,
            )

        cli.__dict__["create_server"] = test_only_server
        client_fd = client_socket.detach()
        sys.argv = ["token-io-mcp", "--host-fd", str(client_fd)]
        if require_codex_context:
            sys.argv.append("--codex-context")
        exit_code = cli.legacy_main()
        host_thread.join(timeout=1)
        raise SystemExit(exit_code)
    if len(sys.argv) != 3 or sys.argv[1] not in {"root", "worker"}:
        raise SystemExit("usage is private to tests")
    role = SessionRole.PARENT if sys.argv[1] == "root" else SessionRole.WORKER
    server = create_server(
        cast(BindingProvider, TestOnlyBindingProvider(role)), state_root=Path(sys.argv[2])
    )
    server.run(transport="stdio")


if __name__ == "__main__":
    main()

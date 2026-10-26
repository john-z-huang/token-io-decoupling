from __future__ import annotations

import os
import socket
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest

from token_io_mcp import cli
from token_io_mcp.binding import BindingError
from token_io_mcp.server import create_server


def test_no_arguments_keeps_public_server(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(sys, "argv", ["token-io-mcp"])
    monkeypatch.setattr(
        cli,
        "create_server",
        lambda provider=None: SimpleNamespace(
            run=lambda **kwargs: calls.append((provider, kwargs))
        ),
    )
    assert cli.main() == 0
    assert calls == [(None, {"transport": "stdio"})]


def test_cli_rejects_identity_assertions(monkeypatch, capsys) -> None:
    monkeypatch.setattr(sys, "argv", ["token-io-mcp", "--session-id", "claimed"])
    assert cli.main() == 2
    assert "unrecognized arguments" in capsys.readouterr().err


def test_invalid_host_fd_fails_before_server_start(monkeypatch, capsys) -> None:
    monkeypatch.setattr(sys, "argv", ["token-io-mcp", "--host-fd", "-1"])

    def unexpected_server(*_args):
        raise AssertionError("server must not start")

    monkeypatch.setattr(cli, "create_server", unexpected_server)
    assert cli.main() == 2
    assert "authenticated host channel unavailable" in capsys.readouterr().err


def test_authenticated_but_insufficient_binding_fails_before_stdio(monkeypatch, capsys) -> None:
    class InsufficientProvider:
        def current_binding(self):
            raise BindingError("unavailable")

        def verify_child_binding(self, _parent, _child_id):
            raise BindingError("unavailable")

        def close(self):
            pass

    provider = InsufficientProvider()
    monkeypatch.setattr(sys, "argv", ["token-io-mcp", "--host-fd", "3"])
    monkeypatch.setattr(
        cli.HostChannelBindingProvider,
        "from_fd",
        staticmethod(lambda _fd: provider),
    )
    monkeypatch.setattr(cli, "create_server", create_server)
    assert cli.main() == 2
    assert "server startup failed" in capsys.readouterr().err


def test_host_binding_uses_os_account_home_not_home_environment(monkeypatch) -> None:
    class Provider:
        closed = False

        def close(self):
            self.closed = True

    provider = Provider()
    calls = []
    monkeypatch.setattr(sys, "argv", ["token-io-mcp", "--host-fd", "3", "--codex-context"])
    monkeypatch.setenv("HOME", "/poisoned/caller/home")
    monkeypatch.setattr("pwd.getpwuid", lambda _uid: SimpleNamespace(pw_dir="/trusted/os-home"))
    monkeypatch.setattr(
        cli.HostChannelBindingProvider,
        "from_fd",
        staticmethod(lambda _fd: provider),
    )

    def build_server(binding_provider, *, require_bound, require_codex_context, state_root):
        calls.append((binding_provider, require_bound, require_codex_context, state_root))
        return SimpleNamespace(run=lambda **_kwargs: None)

    monkeypatch.setattr(cli, "create_server", build_server)
    assert cli.main() == 0
    assert calls == [
        (
            provider,
            True,
            True,
            Path("/trusted/os-home/.local/state/token-io-decoupling"),
        )
    ]
    assert provider.closed


def test_missing_os_account_mapping_fails_safely(monkeypatch, capsys) -> None:
    class Provider:
        closed = False

        def close(self):
            self.closed = True

    provider = Provider()
    monkeypatch.setattr(sys, "argv", ["token-io-mcp", "--host-fd", "3"])
    monkeypatch.setattr(
        cli.HostChannelBindingProvider,
        "from_fd",
        staticmethod(lambda _fd: provider),
    )
    monkeypatch.setattr("pwd.getpwuid", lambda _uid: (_ for _ in ()).throw(KeyError("no entry")))

    def unexpected_server(*_args, **_kwargs):
        raise AssertionError("server must not start")

    monkeypatch.setattr(cli, "create_server", unexpected_server)
    assert cli.main() == 2
    assert capsys.readouterr().err == "token-io-mcp: server startup failed\n"
    assert provider.closed


def test_codex_context_flag_requires_host_descriptor(monkeypatch, capsys) -> None:
    monkeypatch.setattr(sys, "argv", ["token-io-mcp", "--codex-context"])

    def unexpected_server(*_args, **_kwargs):
        raise AssertionError("server must not start")

    monkeypatch.setattr(cli, "create_server", unexpected_server)
    assert cli.main() == 2
    assert capsys.readouterr().err == "token-io-mcp: --codex-context requires --host-fd\n"


def test_production_subprocess_rejects_same_uid_host_peer() -> None:
    if os.geteuid() == 0:
        cast(Any, pytest.skip)(
            "requires an unprivileged test process to exercise production peer rejection"
        )
    client_socket, peer_socket = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        project_root = __file__.rsplit("/tests/", 1)[0]
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "token_io_mcp.cli",
                "--host-fd",
                str(client_socket.fileno()),
            ],
            cwd=project_root,
            pass_fds=(client_socket.fileno(),),
            capture_output=True,
            check=False,
            timeout=10,
        )
        assert result.returncode == 2
        assert result.stdout == b""
        assert result.stderr == b"token-io-mcp: authenticated host channel unavailable\n"
    finally:
        client_socket.close()
        peer_socket.close()

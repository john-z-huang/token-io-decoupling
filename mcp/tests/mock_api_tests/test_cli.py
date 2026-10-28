from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from token_io_decoupling_core.profiles import PROFILE_SERVER_NAMES

from token_io_decoupling import cli


def test_default_command_starts_workflow_profile(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(sys, "argv", ["token-io-decoupling"])
    monkeypatch.setattr(
        cli,
        "create_server",
        lambda *args, **kwargs: (
            calls.append((args, kwargs)) or SimpleNamespace(run=lambda **_kwargs: None)
        ),
    )
    assert cli.main() == 0
    assert calls[0][1]["profile"] == "workflow"
    assert calls[0][1]["server_name"] == PROFILE_SERVER_NAMES["workflow"]


@pytest.mark.parametrize("profile", ["workflow", "root", "worker", "share"])
def test_profile_is_selected_through_unified_start_command(monkeypatch, profile) -> None:
    calls = []
    monkeypatch.setattr(
        sys,
        "argv",
        ["token-io-decoupling", "start-mcp-server", "--profile", profile],
    )
    monkeypatch.setattr(
        cli,
        "create_server",
        lambda *args, **kwargs: (
            calls.append((args, kwargs)) or SimpleNamespace(run=lambda **_kwargs: None)
        ),
    )
    assert cli.main() == 0
    assert calls[0][1]["profile"] == profile
    assert calls[0][1]["server_name"] == PROFILE_SERVER_NAMES[profile]


@pytest.mark.parametrize(
    "argv",
    [
        ["token-io-decoupling", "--host-fd", "3", "--codex-context", "start-mcp-server"],
        ["token-io-decoupling", "start-mcp-server", "--host-fd", "3", "--codex-context"],
    ],
)
def test_start_subcommand_preserves_host_options_in_both_positions(monkeypatch, argv) -> None:
    class Provider:
        def close(self):
            pass

    provider = Provider()
    calls = []
    monkeypatch.setattr(sys, "argv", argv)
    monkeypatch.setattr(
        cli.HostChannelBindingProvider, "from_fd", staticmethod(lambda _fd: provider)
    )
    monkeypatch.setattr(cli, "_trusted_state_root", lambda: Path("/trusted/state"))
    monkeypatch.setattr(
        cli,
        "create_server",
        lambda *args, **kwargs: (
            calls.append((args, kwargs)) or SimpleNamespace(run=lambda **_kwargs: None)
        ),
    )
    assert cli.main() == 0
    assert calls[0][0] == (provider,)
    assert calls[0][1]["require_bound"] is True
    assert calls[0][1]["require_codex_context"] is True


def test_setup_rejects_host_binding_options(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        ["token-io-decoupling", "--host-fd", "3", "setup", "codex", "--dry-run"],
    )
    assert cli.main() == 2
    assert "cannot be used with setup" in capsys.readouterr().err


def test_setup_rejects_profile_and_all_together(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        ["token-io-decoupling", "setup", "codex", "--profile", "workflow", "--all"],
    )
    assert cli.main() == 2
    assert "cannot be combined" in capsys.readouterr().err


def test_codex_env_command_merges_selected_existing_server(monkeypatch, tmp_path, capsys) -> None:
    config = tmp_path / "config.toml"
    config.write_text('[mcp_servers.only]\ncommand = "runner"\n', encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "token-io-decoupling",
            "setup",
            "codex-env",
            "--config",
            str(config),
            "--server",
            "only",
        ],
    )
    assert cli.main() == 0
    assert "updated environment forwarding: only" in capsys.readouterr().out
    assert "OPENAI_API_KEY" in config.read_text(encoding="utf-8")


def test_codex_env_command_requires_server_selection(monkeypatch, capsys) -> None:
    monkeypatch.setattr(sys, "argv", ["token-io-decoupling", "setup", "codex-env"])
    assert cli.main() == 2
    assert "--server" in capsys.readouterr().err


def test_legacy_module_cli_keeps_public_only_default(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(sys, "argv", ["token-io-mcp"])
    monkeypatch.setattr(
        cli,
        "create_server",
        lambda provider=None, **kwargs: (
            calls.append((provider, kwargs)) or SimpleNamespace(run=lambda **_kwargs: None)
        ),
    )
    assert cli.legacy_main() == 0
    assert calls[0][1]["profile"] is None


def test_invalid_host_fd_fails_before_server_start(monkeypatch, capsys) -> None:
    monkeypatch.setattr(sys, "argv", ["token-io-decoupling", "--host-fd", "-1"])

    def unexpected_server(*_args, **_kwargs):
        raise AssertionError("server must not start")

    monkeypatch.setattr(cli, "create_server", unexpected_server)
    assert cli.main() == 2
    assert "authenticated host channel unavailable" in capsys.readouterr().err


def test_codex_context_requires_host_fd(monkeypatch, capsys) -> None:
    monkeypatch.setattr(sys, "argv", ["token-io-decoupling", "--codex-context"])
    assert cli.main() == 2
    assert "requires --host-fd" in capsys.readouterr().err


def test_unknown_profile_is_rejected(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        sys, "argv", ["token-io-decoupling", "start-mcp-server", "--profile", "unknown"]
    )
    assert cli.main() == 2
    assert "invalid choice" in capsys.readouterr().err

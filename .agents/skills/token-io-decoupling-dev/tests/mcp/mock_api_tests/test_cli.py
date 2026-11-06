from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest

from token_io_decoupling import cli, cli_commands
from token_io_decoupling_tools import cli as tools_cli
from token_io_decoupling_workflow import cli as workflow_cli


def test_admin_entrypoint_only_dispatches_management_commands(monkeypatch, capsys) -> None:
    monkeypatch.setattr(sys, "argv", ["token-io-decoupling"])
    assert cli.main() == 2
    assert "the following arguments are required" in capsys.readouterr().err


def test_setup_codex_dispatches_the_two_server_registration(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(
        cli_commands,
        "setup_codex",
        lambda **kwargs: calls.append(kwargs) or 0,
    )
    monkeypatch.setattr(sys, "argv", ["token-io-decoupling", "setup", "codex", "--dry-run"])
    assert cli.main() == 0
    assert calls == [{"dry_run": True, "server": "both"}]


@pytest.mark.parametrize("flag", ["--profile", "--all", "--replace", "--migrate-tools"])
def test_removed_setup_selection_and_override_flags_are_rejected(monkeypatch, capsys, flag) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        ["token-io-decoupling", "setup", "codex", flag],
    )
    assert cli.main() == 2
    assert "unrecognized arguments" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("module", "factory_name"),
    ((workflow_cli, "create_workflow_server"), (tools_cli, "create_tools_server")),
)
def test_fixed_server_entrypoints_start_with_no_arguments(
    monkeypatch, tmp_path, module, factory_name
) -> None:
    """两个固定服务以无参数入口启动，发现结果必须符合当前工具清单。"""
    calls = []
    monkeypatch.setattr(
        module,
        factory_name,
        lambda **kwargs: (
            calls.append(kwargs)
            or SimpleNamespace(run=lambda **run_kwargs: calls.append(run_kwargs))
        ),
    )
    if module is tools_cli:
        monkeypatch.setattr(module, "load_task_plan_service", lambda _factory: None)
        monkeypatch.setattr(module, "load_compliance_service", lambda _factory: None)
        monkeypatch.setattr(module, "load_output_materializer_config", lambda _factory: None)
    monkeypatch.setattr(sys, "argv", ["server"])

    assert module.main() == 0
    expected_server_args = (
        {"event_advice_config": module.DecisionsRuntimeConfig()}
        if module is workflow_cli
        else {
            "task_plan_service": None,
            "compliance_service": None,
            "output_materializer_config": None,
        }
    )
    assert calls[0] == expected_server_args
    assert calls[1] == {"transport": "stdio"}


@pytest.mark.parametrize("flag", ["--host-fd", "--codex-context"])
def test_removed_privileged_host_options_are_not_supported(monkeypatch, capsys, flag) -> None:
    monkeypatch.setattr(sys, "argv", ["token-io-decoupling", "setup", "codex", flag])
    assert cli.main() == 2
    assert "unrecognized arguments" in capsys.readouterr().err


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


@pytest.mark.parametrize(
    "flag", ["--task-plan-factory", "--compliance-factory", "--output-materializer-factory"]
)
def test_workflow_rejects_migrated_backend_options(monkeypatch, flag) -> None:
    monkeypatch.setattr(sys, "argv", ["workflow", flag, "operator:build"])
    with pytest.raises(SystemExit) as error:
        workflow_cli.main()
    assert error.value.code == 2

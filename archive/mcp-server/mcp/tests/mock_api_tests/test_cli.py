from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest

from token_io_decoupling import cli, skills


def test_tools_entrypoint_starts_stdio_with_no_arguments(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(cli, "create_tools_server", lambda **kwargs: (
        calls.append(kwargs) or SimpleNamespace(run=lambda **options: calls.append(options))
    ))
    monkeypatch.setattr(cli, "load_compliance_service", lambda _spec: None)
    monkeypatch.setattr(cli, "load_output_materializer_config", lambda _spec: None)
    monkeypatch.setattr(sys, "argv", ["token-io-decoupling-tools"])
    assert cli.tools_main() == 0
    assert calls == [
        {"compliance_service": None, "output_materializer_config": None},
        {"transport": "stdio"},
    ]


@pytest.mark.parametrize("action", ["install", "update"])
def test_tools_entrypoint_dispatches_skills(monkeypatch, tmp_path, action) -> None:
    calls = []
    target = tmp_path / ".pi/agent/skills/token-io-decoupling-skill"
    monkeypatch.setattr(skills, "install_skill", lambda **kwargs: calls.append(kwargs) or target)
    monkeypatch.setattr(sys, "argv", ["token-io-decoupling-tools", "skills", action])
    assert cli.tools_main() == 0
    assert calls == [{"name": skills.DEFAULT_NAME, "update": action == "update"}]


@pytest.mark.parametrize("arguments", [
    ["workflow"], ["--host-fd", "3"], ["--task-plan-factory", "operator:build"],
    ["skills", "install", "--destination", "/tmp/escape"],
])
def test_removed_commands_and_unsafe_destination_are_rejected(monkeypatch, arguments) -> None:
    monkeypatch.setattr(sys, "argv", ["token-io-decoupling-tools", *arguments])
    try:
        result = cli.tools_main()
    except SystemExit as exc:
        result = exc.code
    assert result == 2

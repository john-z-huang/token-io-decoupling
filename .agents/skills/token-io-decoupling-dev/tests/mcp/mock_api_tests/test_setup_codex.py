from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
import tomlkit

from token_io_decoupling_core.server_tools import (
    TOOLS_SERVER_NAME,
    TOOLS_SERVER_TOOLS,
    WORKFLOW_SERVER_NAME,
    WORKFLOW_TOOLS,
)
from token_io_decoupling_transport import setup_codex
from token_io_decoupling_transport.codex_env import DEFAULT_ENV_VARS, TOOLS_ENV_VARS
from token_io_decoupling_transport.setup_codex import SetupError

_ENTRY_POINTS = {
    "token-io-decoupling-workflow": "token_io_decoupling_workflow.cli:main",
    "token-io-decoupling-tools": "token_io_decoupling_tools.cli:main",
}
_UNRELATED_SERVERS = (
    "token-io-decoupling",
    "token-io-decoupling-root-agent-tools",
    "token-io-decoupling-worker-agent-tools",
    "token-io-decoupling-share-tools",
)


def _install_metadata(monkeypatch, tmp_path: Path) -> dict[str, Path]:
    scripts = tmp_path / "bin"
    scripts.mkdir(exist_ok=True)
    paths = {}
    for name in _ENTRY_POINTS:
        path = scripts / name
        path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        path.chmod(0o755)
        paths[name] = path.resolve()

    class EntryPoint:
        group = "console_scripts"

        def __init__(self, name: str, value: str) -> None:
            self.name = name
            self.value = value

    class Distribution:
        entry_points = [EntryPoint(name, value) for name, value in _ENTRY_POINTS.items()]

    monkeypatch.setattr(setup_codex.metadata, "distribution", lambda _name: Distribution())
    monkeypatch.setattr(setup_codex.sysconfig, "get_path", lambda _name: str(scripts))
    return paths


def _current_config() -> str:
    return (
        "# preserve this comment\n"
        '[unrelated]\nvalue = "keep"\n\n'
        '[mcp_servers."token-io-decoupling-workflow"]\n'
        'command = "/old/workflow"\nargs = ["old-arg"]\ncwd = "/keep/workflow"\n'
        'env = { EXISTING = "SYNTHETIC_SECRET_SENTINEL" }\nenv_vars = ["KEEP_WORKFLOW"]\n'
        'enabled_tools = ["workflow_capabilities"]\n'
        'default_tools_approval_mode = "writes"\nstartup_timeout_sec = 31\n'
        "tool_timeout_sec = 42\n\n"
        '[mcp_servers."token-io-decoupling-tools"]\n'
        'command = "/old/tools"\nargs = ["old-arg"]\nenv_vars = ["KEEP_TOOLS"]\n'
        'enabled = true\ncwd = "/keep/tools"\n'
        'disabled_tools = ["check_api_input"]\n'
        '\n[mcp_servers."token-io-decoupling"]\n'
        'command = "/old/admin-launcher"\nargs = ["start-mcp-server"]\n'
        '\n[mcp_servers."token-io-decoupling-root-agent-tools"]\n'
        'command = "/old/root"\nargs = ["start-mcp-server", "--profile", "root"]\n'
        'env_vars = ["ROOT_KEEP"]\n'
        '\n[mcp_servers."token-io-decoupling-worker-agent-tools"]\n'
        'command = "/old/worker"\nargs = ["start-mcp-server", "--profile", "worker"]\n'
        'env_vars = ["WORKER_KEEP"]\n'
        '\n[mcp_servers."token-io-decoupling-share-tools"]\n'
        'command = "/old/share"\nargs = ["start-mcp-server", "--profile", "share"]\n'
        'env_vars = ["SHARE_KEEP"]\n'
    )


def _setup(monkeypatch, tmp_path: Path, content: str | None = None):
    paths = _install_metadata(monkeypatch, tmp_path)
    config = tmp_path / "config.toml"
    if content is not None:
        config.write_text(content, encoding="utf-8")
    monkeypatch.setattr(setup_codex, "config_path", lambda: config)
    discoveries = []
    monkeypatch.setattr(
        setup_codex,
        "_validate_installed_discovery",
        lambda paths: discoveries.append(dict(paths)),
    )
    return paths, config, discoveries


def test_dry_run_previews_two_current_servers_without_discovery_or_write(
    monkeypatch, tmp_path, capsys
) -> None:
    paths, config, _ = _setup(monkeypatch, tmp_path, _current_config())
    before = config.read_bytes()

    def forbidden(*_args):
        raise AssertionError("preview must not start an MCP process or write configuration")

    monkeypatch.setattr(setup_codex, "_validate_installed_discovery", forbidden)
    monkeypatch.setattr(setup_codex, "atomic_write_config", forbidden)
    assert setup_codex.setup_codex(dry_run=True) == 0
    output = capsys.readouterr().out
    assert "Would configure token-io-decoupling-workflow" in output
    assert "Would configure token-io-decoupling-tools" in output
    assert "args=[]" in output
    assert "OPENAI_TIMEOUT_MAX_RETRIES" in output
    assert "SYNTHETIC_SECRET_SENTINEL" not in output
    assert all(path.is_absolute() for path in paths.values())
    assert config.read_bytes() == before


def test_setup_updates_only_current_servers_and_preserves_settings(monkeypatch, tmp_path) -> None:
    paths, config, discoveries = _setup(monkeypatch, tmp_path, _current_config())
    before_servers = tomlkit.parse(config.read_text(encoding="utf-8"))["mcp_servers"]
    unrelated_before = {name: before_servers[name] for name in _UNRELATED_SERVERS}
    assert setup_codex.setup_codex() == 0
    assert len(discoveries) == 1
    document = tomlkit.parse(config.read_text(encoding="utf-8"))
    servers = document["mcp_servers"]
    assert set(servers) == {WORKFLOW_SERVER_NAME, TOOLS_SERVER_NAME, *_UNRELATED_SERVERS}
    workflow = servers[WORKFLOW_SERVER_NAME]
    tools = servers[TOOLS_SERVER_NAME]
    assert workflow["command"] == str(paths["token-io-decoupling-workflow"])
    assert workflow["args"] == []
    assert workflow["cwd"] == "/keep/workflow"
    assert workflow["env"] == {"EXISTING": "SYNTHETIC_SECRET_SENTINEL"}
    assert workflow["enabled_tools"] == ["workflow_capabilities"]
    assert workflow["default_tools_approval_mode"] == "writes"
    assert workflow["startup_timeout_sec"] == 31
    assert workflow["tool_timeout_sec"] == 42
    assert workflow["env_vars"] == ["KEEP_WORKFLOW", *DEFAULT_ENV_VARS]
    assert "OPENAI_TIMEOUT_MAX_RETRIES" not in workflow["env_vars"]
    assert tools["command"] == str(paths["token-io-decoupling-tools"])
    assert tools["args"] == []
    assert tools["disabled_tools"] == ["check_api_input"]
    assert tools["env_vars"] == ["KEEP_TOOLS", *TOOLS_ENV_VARS]
    assert "OPENAI_TIMEOUT_MAX_RETRIES" in tools["env_vars"]
    assert {name: servers[name] for name in _UNRELATED_SERVERS} == unrelated_before
    raw = config.read_text(encoding="utf-8")
    assert "preserve this comment" in raw
    assert "[unrelated]" in raw and 'value = "keep"' in raw


def test_fractional_timeout_values_are_accepted_and_preserved(monkeypatch, tmp_path) -> None:
    content = (
        _current_config()
        .replace("startup_timeout_sec = 31", "startup_timeout_sec = 12.5")
        .replace("tool_timeout_sec = 42", "tool_timeout_sec = 60.25")
    )
    _paths, config, discoveries = _setup(monkeypatch, tmp_path, content)

    assert setup_codex.setup_codex() == 0
    assert len(discoveries) == 1
    workflow = tomlkit.parse(config.read_text(encoding="utf-8"))["mcp_servers"][
        WORKFLOW_SERVER_NAME
    ]
    assert workflow["startup_timeout_sec"] == 12.5
    assert workflow["tool_timeout_sec"] == 60.25


def test_new_config_and_repeat_setup_are_idempotent(monkeypatch, tmp_path) -> None:
    _paths, config, _discoveries = _setup(monkeypatch, tmp_path)
    assert setup_codex.setup_codex() == 0
    first = config.read_bytes()
    mtime = config.stat().st_mtime_ns
    assert set(tomlkit.parse(first.decode())["mcp_servers"]) == {
        WORKFLOW_SERVER_NAME,
        TOOLS_SERVER_NAME,
    }
    assert setup_codex.setup_codex() == 0
    assert config.read_bytes() == first
    assert config.stat().st_mtime_ns == mtime


def test_malformed_current_target_fails_closed(monkeypatch, tmp_path) -> None:
    content = _current_config().replace('command = "/old/tools"', 'url = "https://example.invalid"')
    _paths, config, discoveries = _setup(monkeypatch, tmp_path, content)
    before = config.read_bytes()
    with pytest.raises(SetupError, match="not a supported stdio"):
        setup_codex.setup_codex()
    assert discoveries == []
    assert config.read_bytes() == before


@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        ('command = "/old/tools"', "command = 3", "stdio command is invalid"),
        ('args = ["old-arg"]', "args = [3]", "args must contain strings"),
        ("enabled = true", 'enabled = "yes"', "enabled state is invalid"),
        ('cwd = "/keep/tools"', "cwd = 3", "cwd is invalid"),
        (
            'env = { EXISTING = "SYNTHETIC_SECRET_SENTINEL" }',
            'env = "bad"',
            "Codex env is invalid",
        ),
        (
            'enabled_tools = ["workflow_capabilities"]',
            'enabled_tools = "bad"',
            "enabled_tools must contain strings",
        ),
        (
            "startup_timeout_sec = 31",
            'startup_timeout_sec = "31"',
            "startup_timeout_sec is invalid",
        ),
        (
            "startup_timeout_sec = 31",
            "startup_timeout_sec = true",
            "startup_timeout_sec is invalid",
        ),
        (
            "tool_timeout_sec = 42",
            'tool_timeout_sec = "42"',
            "tool_timeout_sec is invalid",
        ),
        (
            "tool_timeout_sec = 42",
            "tool_timeout_sec = true",
            "tool_timeout_sec is invalid",
        ),
        (
            'default_tools_approval_mode = "writes"',
            "default_tools_approval_mode = false",
            "default tools approval mode is invalid",
        ),
        ('env_vars = ["KEEP_TOOLS"]', 'env_vars = "bad"', "env_vars must be an array"),
        (
            'env_vars = ["KEEP_TOOLS"]',
            'env_vars = [{ name = "OPENAI_API_KEY", source = "remote" }]',
            "env_vars source conflict",
        ),
    ],
)
def test_malformed_current_settings_fail_before_discovery_or_write(
    monkeypatch, tmp_path, old, new, message
) -> None:
    body = _current_config().replace(old, new)
    _paths, config, discoveries = _setup(monkeypatch, tmp_path, body)
    before = config.read_bytes()
    with pytest.raises(SetupError, match=message):
        setup_codex.setup_codex()
    assert discoveries == []
    assert config.read_bytes() == before


def test_dry_run_with_missing_config_does_not_create_it(monkeypatch, tmp_path, capsys) -> None:
    _paths, config, _discoveries = _setup(monkeypatch, tmp_path)
    assert setup_codex.setup_codex(dry_run=True) == 0
    assert "Would configure" in capsys.readouterr().out
    assert not config.exists()


def test_symlink_config_is_rejected_without_changing_target(monkeypatch, tmp_path) -> None:
    paths = _install_metadata(monkeypatch, tmp_path)
    target = tmp_path / "target.toml"
    target.write_text(_current_config(), encoding="utf-8")
    config = tmp_path / "config.toml"
    config.symlink_to(target)
    monkeypatch.setattr(setup_codex, "config_path", lambda: config)
    before = target.read_bytes()
    with pytest.raises(SetupError, match="regular, non-symlink"):
        setup_codex.setup_codex()
    assert target.read_bytes() == before
    assert config.is_symlink()
    assert paths


def test_non_regular_config_is_rejected(monkeypatch, tmp_path) -> None:
    _install_metadata(monkeypatch, tmp_path)
    config = tmp_path / "config.toml"
    config.mkdir()
    monkeypatch.setattr(setup_codex, "config_path", lambda: config)
    with pytest.raises(SetupError, match="regular, non-symlink"):
        setup_codex.setup_codex()


def test_unrepresentable_config_format_fails_before_discovery_or_write(
    monkeypatch, tmp_path
) -> None:
    prefix = (
        '[[fruit]]\nname = "apple"\n\n[unrelated]\nflag = true\n\n'
        "[fruit.texture]\nsmooth = true\n\n"
    )
    body = prefix + '[mcp_servers."token-io-decoupling-workflow"]\ncommand = "old"\n'
    assert tomlkit.dumps(tomlkit.parse(body)) != body
    _paths, config, discoveries = _setup(monkeypatch, tmp_path, body)
    before = config.read_bytes()
    with pytest.raises(SetupError, match="cannot be safely rewritten"):
        setup_codex.setup_codex()
    assert discoveries == []
    assert config.read_bytes() == before


def test_concurrent_config_change_is_not_overwritten(monkeypatch, tmp_path) -> None:
    _paths, config, _discoveries = _setup(monkeypatch, tmp_path, _current_config())
    before = config.read_bytes()
    original = setup_codex.atomic_write_config

    def race(path: Path, snapshot, rendered: bytes) -> None:
        path.write_bytes(before + b"# concurrent change\n")
        original(path, snapshot, rendered)

    monkeypatch.setattr(setup_codex, "atomic_write_config", race)
    with pytest.raises(SetupError, match="config update failed"):
        setup_codex.setup_codex()
    assert config.read_bytes() == before + b"# concurrent change\n"


def test_installed_discovery_checks_both_distinct_no_argument_programs(
    monkeypatch, tmp_path
) -> None:
    paths = _install_metadata(monkeypatch, tmp_path)
    executables = setup_codex._installed_servers()
    assert executables == paths
    assert len(WORKFLOW_TOOLS) == 11
    assert len(TOOLS_SERVER_TOOLS) == 41
    calls = []
    expected_by_path = {
        str(paths["token-io-decoupling-workflow"]): WORKFLOW_TOOLS,
        str(paths["token-io-decoupling-tools"]): TOOLS_SERVER_TOOLS,
    }

    class FakeClient:
        def __init__(self, parameters, mode):
            self.command = parameters.command
            calls.append((parameters.command, parameters.args, mode))

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def list_tools(self):
            expected = expected_by_path[self.command]
            return SimpleNamespace(tools=[SimpleNamespace(name=name) for name in expected])

    monkeypatch.setattr(setup_codex, "Client", FakeClient)
    setup_codex._validate_installed_discovery(executables)
    assert calls == [
        (str(paths["token-io-decoupling-workflow"]), [], "auto"),
        (str(paths["token-io-decoupling-tools"]), [], "auto"),
    ]


@pytest.mark.parametrize("selection", ["tools", "workflow"])
def test_selected_setup_ignores_uninstalled_and_malformed_sibling(
    monkeypatch, tmp_path, selection
) -> None:
    selected = f"token-io-decoupling-{selection}"
    sibling = "token-io-decoupling-" + ("workflow" if selection == "tools" else "tools")
    content = (
        f'[mcp_servers."{selected}"]\ncommand = "/old"\nenabled = false\n'
        f'[mcp_servers."{sibling}"]\ncommand = ["malformed but unselected"]\n'
    )
    paths, config, discoveries = _setup(monkeypatch, tmp_path, content)
    original = setup_codex.metadata.distribution
    looked_up = []

    def only_selected(name):
        looked_up.append(name)
        assert name == selected
        return original(name)

    monkeypatch.setattr(setup_codex.metadata, "distribution", only_selected)
    assert setup_codex.setup_codex(server=selection) == 0
    parsed = tomlkit.parse(config.read_text())["mcp_servers"]
    assert looked_up == [selected]
    assert discoveries == [{selected: paths[selected]}]
    assert parsed[selected]["enabled"] is False
    assert parsed[sibling]["command"] == ["malformed but unselected"]


def test_installed_metadata_requires_expected_console_script_targets(monkeypatch, tmp_path) -> None:
    _install_metadata(monkeypatch, tmp_path)
    monkeypatch.setattr(
        setup_codex.metadata,
        "distribution",
        lambda _name: SimpleNamespace(
            entry_points=[
                SimpleNamespace(
                    group="console_scripts",
                    name="token-io-decoupling-workflow",
                    value="token_io_decoupling.cli:wrong_workflow_main",
                ),
                SimpleNamespace(
                    group="console_scripts",
                    name="token-io-decoupling-tools",
                    value="token_io_decoupling_tools.cli:main",
                ),
            ]
        ),
    )
    with pytest.raises(SetupError, match="installed executable metadata is invalid"):
        setup_codex._installed_servers()


@pytest.mark.parametrize("fault", ["missing", "extra", "duplicate"])
def test_discovery_rejects_any_non_exact_inventory(monkeypatch, tmp_path, fault) -> None:
    paths = _install_metadata(monkeypatch, tmp_path)
    expected_by_path = {
        str(paths["token-io-decoupling-workflow"]): list(WORKFLOW_TOOLS),
        str(paths["token-io-decoupling-tools"]): list(TOOLS_SERVER_TOOLS),
    }

    class FakeClient:
        def __init__(self, parameters, mode):
            self.command = parameters.command

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def list_tools(self):
            names = expected_by_path[self.command]
            if fault == "missing":
                names = names[:-1]
            elif fault == "extra":
                names = [*names, "unexpected_tool"]
            else:
                names = [*names, names[0]]
            return SimpleNamespace(tools=[SimpleNamespace(name=name) for name in names])

    monkeypatch.setattr(setup_codex, "Client", FakeClient)
    with pytest.raises(SetupError, match="inventory is invalid"):
        setup_codex._validate_installed_discovery(
            {
                WORKFLOW_SERVER_NAME: paths["token-io-decoupling-workflow"],
                TOOLS_SERVER_NAME: paths["token-io-decoupling-tools"],
            }
        )


def test_discovery_failure_does_not_write_planned_config(monkeypatch, tmp_path) -> None:
    _paths, config, _discoveries = _setup(monkeypatch, tmp_path, _current_config())
    before = config.read_bytes()

    def fail(_paths):
        raise SetupError("synthetic inventory failure")

    monkeypatch.setattr(setup_codex, "_validate_installed_discovery", fail)
    with pytest.raises(SetupError, match="synthetic inventory failure"):
        setup_codex.setup_codex()
    assert config.read_bytes() == before

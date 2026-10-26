from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import tomlkit
from token_io_decoupling_core.profiles import PROFILE_SERVER_NAMES

from token_io_decoupling import setup_codex
from token_io_decoupling.setup_codex import SetupError


def _install_launcher(monkeypatch, tmp_path: Path) -> Path:
    scripts = tmp_path / "bin"
    scripts.mkdir()
    executable = scripts / "token-io-decoupling"
    executable.touch()
    executable.chmod(0o755)

    class EntryPoint:
        group = "console_scripts"
        name = "token-io-decoupling"
        value = "token_io_decoupling.cli:main"

    class Distribution:
        entry_points = [EntryPoint()]

    monkeypatch.setattr(setup_codex.metadata, "distribution", lambda _name: Distribution())
    monkeypatch.setattr(setup_codex.sysconfig, "get_path", lambda _name: str(scripts))
    return executable


def test_one_installed_launcher_is_used_for_each_profile(monkeypatch, tmp_path, capsys) -> None:
    executable = _install_launcher(monkeypatch, tmp_path)

    def unexpected_subprocess(*_args, **_kwargs):
        raise AssertionError("dry-run must not call subprocess")

    monkeypatch.setattr(subprocess, "run", unexpected_subprocess)
    assert setup_codex.setup_codex(all_profiles=True, dry_run=True) == 0
    output = capsys.readouterr().out
    assert output.count(str(executable.resolve())) == 4
    for profile, name in PROFILE_SERVER_NAMES.items():
        assert name in output
        assert f'"{profile}"' in output
        assert '"start-mcp-server"' in output


def test_profile_setup_uses_same_unified_executable(monkeypatch, tmp_path, capsys) -> None:
    executable = _install_launcher(monkeypatch, tmp_path)
    assert setup_codex.setup_codex(profile="worker", dry_run=True) == 0
    output = capsys.readouterr().out
    assert str(executable.resolve()) in output
    assert PROFILE_SERVER_NAMES["worker"] in output
    assert '"--profile", "worker"' in output


def test_setup_rejects_missing_launcher_metadata(monkeypatch) -> None:
    def missing(_name):
        raise setup_codex.metadata.PackageNotFoundError("missing")

    monkeypatch.setattr(setup_codex.metadata, "distribution", missing)
    with pytest.raises(SetupError, match="installation metadata"):
        setup_codex.setup_codex(profile="workflow", dry_run=True)


def test_setup_rejects_unknown_profile(monkeypatch, tmp_path) -> None:
    _install_launcher(monkeypatch, tmp_path)
    with pytest.raises(SetupError, match="unknown server profile"):
        setup_codex.setup_codex(profile="unknown", dry_run=True)


def test_setup_preflight_detects_conflicting_stdio_registration(monkeypatch, tmp_path) -> None:
    executable = _install_launcher(monkeypatch, tmp_path)
    monkeypatch.setattr(setup_codex.shutil, "which", lambda _name: "/opt/codex")
    calls = []

    def run(argv, **_kwargs):
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 0, stdout="ok", stderr="")

    monkeypatch.setattr(subprocess, "run", run)
    monkeypatch.setattr(
        setup_codex,
        "_json_output",
        lambda argv: (
            [{"name": PROFILE_SERVER_NAMES["workflow"]}]
            if argv[1:3] == ["mcp", "list"]
            else {
                "name": PROFILE_SERVER_NAMES["workflow"],
                "enabled": True,
                "transport": {"type": "stdio", "command": "/different", "args": []},
            }
        ),
    )
    with pytest.raises(SetupError, match="conflicting configuration"):
        setup_codex.setup_codex(profile="workflow")
    assert not any(argv[1:3] == ["mcp", "add"] for argv in calls)
    assert executable.is_file()


def test_setup_repairs_forwarding_for_matching_profile(monkeypatch, tmp_path, capsys) -> None:
    executable = _install_launcher(monkeypatch, tmp_path)
    config = tmp_path / "config.toml"
    name = PROFILE_SERVER_NAMES["worker"]
    config.write_text(
        f'[mcp_servers."{name}"]\ncommand = "{executable.resolve()}"\n'
        'args = ["start-mcp-server", "--profile", "worker"]\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(setup_codex, "config_path", lambda: config)
    monkeypatch.setattr(setup_codex.shutil, "which", lambda _name: "/opt/codex")
    calls = []
    monkeypatch.setattr(
        setup_codex,
        "_run",
        lambda argv: calls.append(argv) or subprocess.CompletedProcess(argv, 0, "", ""),
    )
    monkeypatch.setattr(
        setup_codex,
        "_json_output",
        lambda argv: (
            [{"name": name}]
            if argv[1:3] == ["mcp", "list"]
            else {
                "name": name,
                "enabled": True,
                "transport": {
                    "type": "stdio",
                    "command": str(executable.resolve()),
                    "args": ["start-mcp-server", "--profile", "worker"],
                },
            }
        ),
    )
    assert setup_codex.setup_codex(profile="worker") == 0
    assert not any(argv[1:3] == ["mcp", "add"] for argv in calls)
    assert tomlkit.parse(config.read_text())["mcp_servers"][name]["env_vars"] == [
        "OPENAI_API_KEY",
        "OPENAI_BASE_URL",
    ]
    assert "updated environment forwarding" in capsys.readouterr().out


def test_setup_new_registration_adds_forwarding_after_registration(monkeypatch, tmp_path) -> None:
    executable = _install_launcher(monkeypatch, tmp_path)
    config = tmp_path / "config.toml"
    config.write_text("# retain this comment\n[unrelated]\nvalue = 1\n", encoding="utf-8")
    monkeypatch.setattr(setup_codex, "config_path", lambda: config)
    monkeypatch.setattr(setup_codex.shutil, "which", lambda _name: "/opt/codex")

    def run(argv):
        if argv[1:3] == ["mcp", "add"]:
            name = argv[3]
            profile = argv[-1]
            with config.open("a", encoding="utf-8") as stream:
                stream.write(
                    f'\n[mcp_servers."{name}"]\ncommand = "{executable.resolve()}"\n'
                    f'args = ["start-mcp-server", "--profile", "{profile}"]\n'
                )
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(setup_codex, "_run", run)
    monkeypatch.setattr(
        setup_codex,
        "_json_output",
        lambda argv: [] if argv[1:3] == ["mcp", "list"] else None,
    )
    assert setup_codex.setup_codex(profile="share") == 0
    name = PROFILE_SERVER_NAMES["share"]
    parsed = tomlkit.parse(config.read_text(encoding="utf-8"))
    assert parsed["mcp_servers"][name]["env_vars"] == ["OPENAI_API_KEY", "OPENAI_BASE_URL"]
    assert "# retain this comment" in config.read_text(encoding="utf-8")


def test_setup_replace_repairs_conflicting_http_registration(monkeypatch, tmp_path) -> None:
    executable = _install_launcher(monkeypatch, tmp_path)
    config = tmp_path / "config.toml"
    name = PROFILE_SERVER_NAMES["share"]
    config.write_text(
        f'[mcp_servers."{name}"]\nurl = "https://example.invalid"\n'
        'bearer_token_env_var = "OLD_HTTP_TOKEN"\n'
        'default_tools_approval_mode = "writes"\n'
        'tools = ["keep-tool"]\nstartup_timeout_sec = 31\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(setup_codex, "config_path", lambda: config)
    monkeypatch.setattr(setup_codex.shutil, "which", lambda _name: "/opt/codex")

    def run(argv):
        if argv[1:3] == ["mcp", "add"]:
            doc = tomlkit.parse(config.read_text(encoding="utf-8"))
            del doc["mcp_servers"][name]
            server = tomlkit.table()
            server.add("command", str(executable.resolve()))
            server.add("args", ["start-mcp-server", "--profile", "share"])
            server.add("enabled", True)
            doc["mcp_servers"].add(name, server)
            config.write_text(tomlkit.dumps(doc), encoding="utf-8")
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(setup_codex, "_run", run)
    monkeypatch.setattr(
        setup_codex,
        "_json_output",
        lambda argv: (
            [{"name": name}]
            if argv[1:3] == ["mcp", "list"]
            else {"name": name, "enabled": True, "transport": {"type": "http"}}
        ),
    )
    assert setup_codex.setup_codex(profile="share", replace=True) == 0
    parsed = tomlkit.parse(config.read_text(encoding="utf-8"))
    assert parsed["mcp_servers"][name]["args"] == ["start-mcp-server", "--profile", "share"]
    assert parsed["mcp_servers"][name]["env_vars"] == ["OPENAI_API_KEY", "OPENAI_BASE_URL"]
    assert parsed["mcp_servers"][name]["default_tools_approval_mode"] == "writes"
    assert parsed["mcp_servers"][name]["tools"] == ["keep-tool"]
    assert parsed["mcp_servers"][name]["startup_timeout_sec"] == 31
    assert "url" not in parsed["mcp_servers"][name]
    assert "bearer_token_env_var" not in parsed["mcp_servers"][name]


def test_setup_stdio_replace_restores_extra_settings_and_env_vars(monkeypatch, tmp_path) -> None:
    executable = _install_launcher(monkeypatch, tmp_path)
    config = tmp_path / "config.toml"
    name = PROFILE_SERVER_NAMES["workflow"]
    config.write_text(
        f'[mcp_servers."{name}"]\ncommand = "/old/launcher"\nargs = []\n'
        'env_vars = ["KEEP"]\nenv = { EXISTING = "kept" }\n'
        'default_tools_approval_mode = "writes"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(setup_codex, "config_path", lambda: config)
    monkeypatch.setattr(setup_codex.shutil, "which", lambda _name: "/opt/codex")

    def run(argv):
        if argv[1:3] == ["mcp", "add"]:
            doc = tomlkit.parse(config.read_text(encoding="utf-8"))
            del doc["mcp_servers"][name]
            replacement = tomlkit.table()
            replacement.add("command", str(executable.resolve()))
            replacement.add("args", ["start-mcp-server", "--profile", "workflow"])
            replacement.add("enabled", True)
            doc["mcp_servers"].add(name, replacement)
            config.write_text(tomlkit.dumps(doc), encoding="utf-8")
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(setup_codex, "_run", run)
    monkeypatch.setattr(
        setup_codex,
        "_json_output",
        lambda argv: (
            [{"name": name}]
            if argv[1:3] == ["mcp", "list"]
            else {
                "name": name,
                "enabled": True,
                "transport": {"type": "stdio", "command": "/old/launcher", "args": []},
            }
        ),
    )
    assert setup_codex.setup_codex(profile="workflow", replace=True) == 0
    server = tomlkit.parse(config.read_text(encoding="utf-8"))["mcp_servers"][name]
    assert server["command"] == str(executable.resolve())
    assert server["args"] == ["start-mcp-server", "--profile", "workflow"]
    assert server["enabled"] is True
    assert server["env_vars"] == ["KEEP", "OPENAI_API_KEY", "OPENAI_BASE_URL"]
    assert server["env"] == {"EXISTING": "kept"}
    assert server["default_tools_approval_mode"] == "writes"


def test_setup_partial_registration_keeps_prior_settings_restored(monkeypatch, tmp_path) -> None:
    executable = _install_launcher(monkeypatch, tmp_path)
    config = tmp_path / "config.toml"
    workflow_name = PROFILE_SERVER_NAMES["workflow"]
    root_name = PROFILE_SERVER_NAMES["root"]
    config.write_text(
        f'[mcp_servers."{workflow_name}"]\ncommand = "/old/workflow"\nargs = []\n'
        'env_vars = ["KEEP"]\ndefault_tools_approval_mode = "writes"\n\n'
        f'[mcp_servers."{root_name}"]\ncommand = "/old/root"\nargs = []\n'
        'env_vars = ["ROOT_KEEP"]\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(setup_codex, "config_path", lambda: config)
    monkeypatch.setattr(setup_codex.shutil, "which", lambda _name: "/opt/codex")

    def run(argv):
        if argv[1:3] == ["mcp", "add"] and argv[3] == workflow_name:
            doc = tomlkit.parse(config.read_text(encoding="utf-8"))
            del doc["mcp_servers"][workflow_name]
            replacement = tomlkit.table()
            replacement.add("command", str(executable.resolve()))
            replacement.add("args", ["start-mcp-server", "--profile", "workflow"])
            doc["mcp_servers"].add(workflow_name, replacement)
            config.write_text(tomlkit.dumps(doc), encoding="utf-8")
            return subprocess.CompletedProcess(argv, 0, "", "")
        if argv[1:3] == ["mcp", "add"] and argv[3] == root_name:
            raise SetupError("synthetic second registration failure")
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(setup_codex, "_run", run)

    def json_output(argv):
        if argv[1:3] == ["mcp", "list"]:
            return [{"name": workflow_name}, {"name": root_name}]
        name = argv[3]
        return {
            "name": name,
            "enabled": True,
            "transport": {"type": "stdio", "command": "/old/launcher", "args": []},
        }

    monkeypatch.setattr(setup_codex, "_json_output", json_output)
    with pytest.raises(SetupError, match="environment forwarding completed for"):
        setup_codex.setup_codex(all_profiles=True, replace=True)
    parsed = tomlkit.parse(config.read_text(encoding="utf-8"))
    workflow = parsed["mcp_servers"][workflow_name]
    assert workflow["env_vars"] == ["KEEP", "OPENAI_API_KEY", "OPENAI_BASE_URL"]
    assert workflow["default_tools_approval_mode"] == "writes"
    assert parsed["mcp_servers"][root_name]["env_vars"] == ["ROOT_KEEP"]


def test_setup_config_symlink_preflight_prevents_registration_write(monkeypatch, tmp_path) -> None:
    _install_launcher(monkeypatch, tmp_path)
    target = tmp_path / "target.toml"
    target.write_text("", encoding="utf-8")
    config = tmp_path / "config.toml"
    config.symlink_to(target)
    monkeypatch.setattr(setup_codex, "config_path", lambda: config)
    monkeypatch.setattr(setup_codex.shutil, "which", lambda _name: "/opt/codex")
    calls = []
    monkeypatch.setattr(
        setup_codex,
        "_run",
        lambda argv: calls.append(argv) or subprocess.CompletedProcess(argv, 0, "", ""),
    )
    monkeypatch.setattr(setup_codex, "_json_output", lambda _argv: [])
    with pytest.raises(SetupError, match="regular, non-symlink"):
        setup_codex.setup_codex(profile="workflow")
    assert not any(argv[1:3] == ["mcp", "add"] for argv in calls)


def test_setup_rejects_non_roundtripping_config_before_registration_write(
    monkeypatch, tmp_path
) -> None:
    _install_launcher(monkeypatch, tmp_path)
    config = tmp_path / "config.toml"
    config.write_text(
        '[[fruit]]\nname = "apple"\n\n[unrelated]\nflag = true\n\n[fruit.texture]\nsmooth = true\n',
        encoding="utf-8",
    )
    before = config.read_bytes()
    monkeypatch.setattr(setup_codex, "config_path", lambda: config)
    monkeypatch.setattr(setup_codex.shutil, "which", lambda _name: "/opt/codex")
    calls = []
    monkeypatch.setattr(
        setup_codex,
        "_run",
        lambda argv: calls.append(argv) or subprocess.CompletedProcess(argv, 0, "", ""),
    )
    monkeypatch.setattr(setup_codex, "_json_output", lambda _argv: [])
    with pytest.raises(SetupError, match="cannot be safely rewritten"):
        setup_codex.setup_codex(profile="workflow")
    assert not any(argv[1:3] == ["mcp", "add"] for argv in calls)
    assert config.read_bytes() == before

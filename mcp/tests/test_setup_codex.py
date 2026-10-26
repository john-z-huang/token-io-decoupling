from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
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

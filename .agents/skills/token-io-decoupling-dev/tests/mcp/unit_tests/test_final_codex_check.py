from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

SUPPORT = Path(__file__).resolve().parents[1] / "support"
sys.path.insert(0, str(SUPPORT))
spec = importlib.util.spec_from_file_location("final_codex_check", SUPPORT / "final_codex_check.py")
assert spec and spec.loader
coordinator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(coordinator)


def test_sdk_only_follows_all_checks_and_tool_update():
    trace = []
    result = coordinator.run_final(
        [("unit", [], Path("/tmp")), ("package", [], Path("/tmp"))],
        lambda label, *_: trace.append(label),
        lambda: trace.append("uv tool update") or Path("/tmp/installed"),
        lambda installed: trace.append("new SDK CLI") or {"passed": True},
    )
    assert trace == ["unit", "package", "uv tool update", "new SDK CLI"]
    assert result == {"passed": True}


@pytest.mark.parametrize("phase", ["checks", "install"])
def test_failure_prevents_sdk_launch(phase):
    trace = []

    def run(*_):
        trace.append("checks")
        if phase == "checks":
            raise RuntimeError("failed check")

    def install():
        trace.append("install")
        raise RuntimeError("failed install")

    with pytest.raises(RuntimeError):
        coordinator.run_final(
            [("unit", [], Path("/tmp"))], run, install, lambda _: trace.append("SDK")
        )
    assert "SDK" not in trace


def test_ordered_checks_cover_compiler_and_migrated_paths_before_installation():
    checks = coordinator.check_commands()
    labels = [label for label, _, _ in checks]
    assert labels[:2] == ["compiler freshness", "compiler tests"]
    assert labels.index("compiler tests") < labels.index("MCP pytest")
    assert labels[-1] == "whitespace"
    for _, command, cwd in checks:
        assert cwd.is_dir()
        assert "tests/unit_tests" not in command
    commands = {label: command for label, command, _ in checks}
    assert str(coordinator.COMPILER / "compile.py") in commands["compiler freshness"]
    assert commands["compiler freshness"][-2:] == ["compile", "--check"]
    assert commands["MCP pytest"][3:5] == ["-c", "pyproject.toml"]
    for category in ("unit_tests", "mock_api_tests", "real_api_tests"):
        assert str(coordinator.MCP_TESTS / category) in commands["MCP pytest"]
    for label in ("lint", "format", "types"):
        assert str(coordinator.MCP_TESTS) in commands[label]
    for label in labels:
        if label.startswith("check-"):
            assert Path(commands[label][-1]).is_file()
    assert str(coordinator.DOC_TESTS) in commands["documentation regressions"]


def test_build_and_isolated_install_precede_migrated_stdio_smoke(tmp_path, monkeypatch):
    trace = []
    monkeypatch.setattr(
        coordinator,
        "execute",
        lambda label, command, cwd, env=None: trace.append((label, command, cwd)),
    )
    installed = coordinator.update_tool(tmp_path)
    assert [label for label, _, _ in trace] == [
        "build current wheels",
        "update isolated uv tool",
        "installed stdio smoke (synthetic project A/B)",
    ]
    assert installed == tmp_path / "bin/token-io-decoupling"
    assert str(coordinator.MCP_TESTS / "support/installed_stdio_smoke.py") in trace[2][1]
    assert trace[1][2] == tmp_path


def test_missing_credentials_stop_before_checks_install_or_sdk(monkeypatch, capsys):
    monkeypatch.setenv("TOKEN_IO_CODEX_CLI_PATH", "/synthetic/codex")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(
        coordinator,
        "check_commands",
        lambda: (_ for _ in ()).throw(AssertionError("checks started without credentials")),
    )
    assert coordinator.main() == 1
    assert "required process variable missing: OPENAI_API_KEY" in capsys.readouterr().out

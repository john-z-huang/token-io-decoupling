"""通过真实 Bash 子进程验证 Hooks 安装、更新及失败边界。"""

import os
from pathlib import Path

import pytest
from mock_api_tests.test_install_codex_mcp import REPO, _calls, _run
from mock_api_tests.test_install_codex_mcp import harness as harness


@pytest.mark.parametrize("action", ["install", "update"])
def test_hooks_install_and_update_use_local_packages_and_register(harness, action):
    env = harness["env"]
    tools = harness["tools"]
    (tools / "codex").unlink()
    result = _run(harness, "--hooks", action, "--python", "3.12")
    assert result.returncode == 0, result.stderr
    calls = _calls(harness)
    source = REPO / "mcp/packages"
    expected = ["uv", "tool", "install", "--managed-python", "--python", "3.12"]
    for name in ("core", "transport", "workflow"):
        expected += ["--with", os.fspath(source / f"token_io_decoupling_{name}")]
    if action == "update":
        expected += ["--force", "--reinstall"]
    expected += [os.fspath(source / "token_io_decoupling_hooks")]
    assert calls == [expected, ["uv", "tool", "dir", "--bin"], ["hooks", "setup", "codex"]]
    assert "/hooks" in result.stdout
    assert Path(env["CONFIG_SENTINEL"]).read_text() == 'mcp_servers = "unchanged"\n'


def test_hooks_configuration_path_preserves_spaces(harness):
    destination = "/project with spaces/.codex/hooks.json"
    result = _run(harness, "--hooks", "install", "--hooks-file", destination)
    assert result.returncode == 0, result.stderr
    assert _calls(harness)[-1] == ["hooks", "setup", "codex", "--hooks-file", destination]


@pytest.mark.parametrize("action", ["install", "update"])
def test_hooks_dry_run_needs_no_tools_and_has_no_effects(harness, action):
    harness["env"]["PATH"] = "/nonexistent"
    result = _run(harness, "--hooks", action, "--dry-run")
    assert result.returncode == 0, result.stderr
    assert "token_io_decoupling_hooks" in result.stdout
    assert "token-io-decoupling-hooks setup codex" in result.stdout
    assert ("--force --reinstall" in result.stdout) == (action == "update")
    assert "token-io-decoupling skills" not in result.stdout
    assert _calls(harness) == []


@pytest.mark.parametrize(
    "arguments",
    [
        ("--hooks",),
        ("--hooks", "remove"),
        ("--hooks", "install", "--hooks", "update"),
        ("--hooks-file", "/project/hooks.json"),
        ("--hooks", "install", "--hooks-file"),
        ("--hooks", "install", "--hooks-file", "relative.json"),
        ("--hooks", "install", "--hooks-file", "/one", "--hooks-file", "/two"),
        ("--hooks", "install", "--name", "unrelated"),
    ],
)
def test_invalid_hooks_arguments_stop_without_effects(harness, arguments):
    result = _run(harness, *arguments)
    assert result.returncode == 2
    assert _calls(harness) == []


@pytest.mark.parametrize(
    ("env_key", "value", "expected_status", "expected_calls"),
    [
        ("FRESHNESS_FAIL", "37", 37, 0),
        ("INSTALL_FAIL", "17", 17, 1),
        ("MISSING_HOOKS_LAUNCHER", "1", 1, 2),
        ("SETUP_FAIL", "19", 19, 3),
    ],
)
def test_hooks_failure_preserves_status_and_stops(
    harness, env_key, value, expected_status, expected_calls
):
    harness["env"][env_key] = value
    result = _run(harness, "--hooks", "update", "--skills", "update")
    assert result.returncode == expected_status
    calls = _calls(harness)
    assert len(calls) == expected_calls
    assert all("skills" not in call for call in calls)


def test_combined_operations_register_mcp_then_hooks_before_skill(harness):
    result = _run(harness, "--mcp", "--hooks", "update", "--skills", "update")
    assert result.returncode == 0, result.stderr
    calls = _calls(harness)
    assert calls[0][:3] == ["uv", "tool", "install"]
    assert calls[1][-1].endswith("/token_io_decoupling_hooks")
    assert calls[2:] == [
        ["uv", "tool", "dir", "--bin"],
        ["setup", "setup", "codex"],
        ["hooks", "setup", "codex"],
        ["setup", "skills", "update", "--name", "token-io-decoupling-skill"],
    ]

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[6]

SCRIPT = REPO / "tid"

BASH = "/bin/bash" if Path("/bin/bash").is_file() else shutil.which("bash")

pytestmark = pytest.mark.skipif(BASH is None, reason="Bash is required to exercise the wrapper")


def _write_executable(path: Path, source: str) -> None:
    path.write_text(source, encoding="utf-8")
    path.chmod(0o755)


@pytest.fixture
def harness(tmp_path: Path) -> dict[str, Path | dict[str, str]]:
    tools = tmp_path / "fake tools"
    tools.mkdir()
    tool_bin = tmp_path / "uv tools bin"
    tool_bin.mkdir()
    log = tmp_path / "calls.jsonl"
    sentinel = tmp_path / "codex-config.toml"
    sentinel.write_text('mcp_servers = "unchanged"\n', encoding="utf-8")
    launcher = tool_bin / "token-io-decoupling"
    workflow_launcher = tool_bin / "token-io-decoupling-workflow"
    tools_launcher = tool_bin / "token-io-decoupling-tools"
    py = os.fspath(Path(sys.executable))
    launcher_source = tmp_path / "launcher.py"
    launcher_source.write_text(
        f"#!{py}\nimport json, os, sys\n"
        "with open(os.environ['CALL_LOG'],'a') as f: "
        "f.write(json.dumps(['hooks' if sys.argv[0].endswith('-hooks') else 'setup',"
        "*sys.argv[1:]])+'\\n')\n"
        "raise SystemExit(int(os.environ.get('SETUP_FAIL','0')))\n",
        encoding="utf-8",
    )
    _write_executable(
        tools / "uv",
        f"#!{py}\n"
        "import json, os, pathlib, sys\n"
        "args=sys.argv[1:]\n"
        "with open(os.environ['CALL_LOG'],'a') as f: f.write(json.dumps(['uv',*args])+'\\n')\n"
        "if args[:2] == ['tool','install']:\n"
        "  if os.environ.get('INSTALL_FAIL'): raise SystemExit(int(os.environ['INSTALL_FAIL']))\n"
        "  p=pathlib.Path(os.environ['LAUNCHER'])\n"
        "  if os.environ.get('EMPTY_BIN'): print('')\n"
        "  elif os.environ.get('MISSING_LAUNCHER'): pass\n"
        "  else:\n"
        "    p.write_bytes(pathlib.Path(os.environ['LAUNCHER_SOURCE']).read_bytes())\n"
        "    p.chmod(0o644 if os.environ.get('NONEXEC_LAUNCHER') else 0o755)\n"
        "  for key in ('WORKFLOW_LAUNCHER','TOOLS_LAUNCHER'):\n"
        "    if not os.environ.get('MISSING_'+key):\n"
        "      q=pathlib.Path(os.environ[key])\n"
        "      q.write_bytes(pathlib.Path(os.environ['LAUNCHER_SOURCE']).read_bytes())\n"
        "      q.chmod(0o755)\n"
        "  if args[-1].endswith('/token_io_decoupling_hooks'):\n"
        "    q=p.parent/'token-io-decoupling-hooks'\n"
        "    if not os.environ.get('MISSING_HOOKS_LAUNCHER'):\n"
        "      q.write_bytes(pathlib.Path(os.environ['LAUNCHER_SOURCE']).read_bytes())\n"
        "      q.chmod(0o755)\n"
        "elif args == ['tool','dir','--bin']:\n"
        "  if os.environ.get('BIN_FAIL'): raise SystemExit(int(os.environ['BIN_FAIL']))\n"
        "  print('' if os.environ.get('EMPTY_BIN') else os.environ['TOOL_BIN'])\n",
    )
    _write_executable(tools / "codex", f"#!{py}\nraise SystemExit(0)\n")
    _write_executable(
        tools / "python3",
        f"#!{py}\nimport os\nraise SystemExit(int(os.environ.get('FRESHNESS_FAIL', '0')))\n",
    )
    env = os.environ.copy()
    env.update(
        PATH=os.fspath(tools),
        CALL_LOG=os.fspath(log),
        LAUNCHER=os.fspath(launcher),
        WORKFLOW_LAUNCHER=os.fspath(workflow_launcher),
        TOOLS_LAUNCHER=os.fspath(tools_launcher),
        LAUNCHER_SOURCE=os.fspath(launcher_source),
        TOOL_BIN=os.fspath(tool_bin),
        CONFIG_SENTINEL=os.fspath(sentinel),
        SCRIPT_SOURCE=os.fspath(SCRIPT),
    )
    return {
        "cwd": tmp_path / "unrelated cwd",
        "env": env,
        "log": log,
        "sentinel": sentinel,
        "tools": tools,
    }


def _run(
    harness: dict[str, Path | dict[str, str]],
    *args: str,
    script: Path | None = None,
    via_bash: bool = False,
) -> subprocess.CompletedProcess[str]:
    cwd = harness["cwd"]
    assert isinstance(cwd, Path)
    cwd.mkdir(exist_ok=True)
    env = harness["env"]
    assert isinstance(env, dict)
    command = [os.fspath(script or SCRIPT), *args]
    if via_bash:
        command.insert(0, BASH or "bash")
    return subprocess.run(
        command,
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def _calls(harness: dict[str, Path | dict[str, str]]) -> list[list[str]]:
    log = harness["log"]
    assert isinstance(log, Path)
    return [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []


def test_installs_and_invokes_absolute_launcher_from_unrelated_cwd(harness):
    result = _run(harness, "--mcp")
    assert result.returncode == 0, result.stderr
    calls = _calls(harness)
    assert calls == [
        [
            "uv",
            "tool",
            "install",
            "--force",
            "--reinstall",
            "--managed-python",
            "--with-executables-from",
            "token-io-decoupling-workflow",
            "--with-executables-from",
            "token-io-decoupling-tools",
            "--python",
            "3.14",
            os.fspath(REPO / "mcp"),
        ],
        ["uv", "tool", "dir", "--bin"],
        ["setup", "setup", "codex"],
    ]
    assert "Reload the affected MCP servers" in result.stdout
    sentinel = harness["sentinel"]
    assert isinstance(sentinel, Path)
    assert sentinel.read_text(encoding="utf-8") == 'mcp_servers = "unchanged"\n'


def test_default_setup_registers_both_fixed_servers(harness):
    result = _run(harness, "--mcp")
    assert result.returncode == 0, result.stderr
    assert _calls(harness)[-1] == ["setup", "setup", "codex"]


def test_custom_python_and_dry_run_options(harness):
    env = harness["env"]
    assert isinstance(env, dict)
    env["PATH"] = "/nonexistent"
    result = _run(harness, "--python", "3.12", "--dry-run")
    assert result.returncode == 0
    assert "--python 3.12" in result.stdout
    assert "--force --reinstall" in result.stdout
    assert "setup codex --dry-run" in result.stdout
    assert "<uv-tool-bin>/token-io-decoupling-workflow" in result.stdout
    assert "<uv-tool-bin>/token-io-decoupling-tools" in result.stdout
    assert _calls(harness) == []


def test_dry_run_and_help_need_no_tools_or_config(harness):
    env = harness["env"]
    assert isinstance(env, dict)
    env["PATH"] = "/nonexistent"
    for args in [("--dry-run",), ("--help",)]:
        result = _run(harness, *args)
        assert result.returncode == 0
    assert _calls(harness) == []


@pytest.mark.parametrize(
    "args",
    [
        ("--profile", "worker"),
        ("--all",),
        ("--replace",),
        ("--migrate-tools",),
        ("--profile",),
        ("--profile", ""),
        ("--python",),
        ("--python", ""),
        ("--python", "--dry-run"),
        ("--python", "3.12", "--python", "3.13"),
        ("--bogus",),
    ],
)
def test_invalid_arguments_have_no_side_effects(harness, args):
    result = _run(harness, *args)
    assert result.returncode != 0
    assert _calls(harness) == []


def test_missing_prerequisites_stop_before_install(harness):
    env = harness["env"]
    assert isinstance(env, dict)
    env["PATH"] = "/nonexistent"
    result = _run(harness, "--mcp")
    assert result.returncode == 127
    assert "uv was not found" in result.stderr
    assert _calls(harness) == []


def test_missing_codex_stops_before_install(harness):
    tools = harness["tools"]
    assert isinstance(tools, Path)
    (tools / "codex").unlink()
    result = _run(harness, "--mcp")
    assert result.returncode == 127
    assert "Codex CLI was not found" in result.stderr
    assert _calls(harness) == []


@pytest.mark.parametrize(
    ("env_key", "value", "expected_status", "message"),
    [
        ("INSTALL_FAIL", "17", 17, "installation/update failed"),
        ("BIN_FAIL", "18", 18, "installation succeeded"),
        ("SETUP_FAIL", "19", 19, "tool installation succeeded, but Codex setup failed"),
    ],
)
def test_failures_stop_and_preserve_status(harness, env_key, value, expected_status, message):
    env = harness["env"]
    assert isinstance(env, dict)
    env[env_key] = value
    result = _run(harness, "--mcp")
    assert result.returncode == expected_status
    assert message in result.stderr
    calls = _calls(harness)
    if env_key == "INSTALL_FAIL":
        assert len(calls) == 1
    elif env_key == "BIN_FAIL":
        assert [call[0] for call in calls] == ["uv", "uv"]
    else:
        assert [call[0] for call in calls] == ["uv", "uv", "setup"]


@pytest.mark.parametrize(
    ("env_key", "message"),
    [
        ("EMPTY_BIN", "empty tool bin directory"),
        ("MISSING_LAUNCHER", "missing or not executable"),
        ("NONEXEC_LAUNCHER", "missing or not executable"),
        ("MISSING_WORKFLOW_LAUNCHER", "missing or not executable"),
        ("MISSING_TOOLS_LAUNCHER", "missing or not executable"),
    ],
)
def test_unusable_installed_command_stops_before_setup(harness, env_key, message):
    env = harness["env"]
    assert isinstance(env, dict)
    env[env_key] = "1"
    result = _run(harness, "--mcp")
    assert result.returncode == 1
    assert message in result.stderr
    calls = _calls(harness)
    assert [call[0] for call in calls] == ["uv", "uv"]


def test_script_finds_repo_when_repo_and_cwd_paths_contain_spaces(harness, tmp_path):
    copied_repo = tmp_path / "repository with spaces"
    (copied_repo / "mcp").mkdir(parents=True)
    script = copied_repo / "tid"
    shutil.copy2(SCRIPT, script)
    compiler_stub = copied_repo / "instruction-compiler/compile.py"
    compiler_stub.parent.mkdir()
    compiler_stub.write_text("# Source-check fixture; invoked by the fake Python tool.\n")
    result = _run(harness, "--mcp", script=script)
    assert result.returncode == 0, result.stderr
    assert _calls(harness)[0][-1] == os.fspath(copied_repo / "mcp")


def test_relative_script_invocation_with_spaces_from_unrelated_cwd(harness, tmp_path):
    copied_repo = tmp_path / "relative repository with spaces"
    (copied_repo / "mcp").mkdir(parents=True)
    script = copied_repo / "tid"
    shutil.copy2(SCRIPT, script)
    compiler_stub = copied_repo / "instruction-compiler/compile.py"
    compiler_stub.parent.mkdir()
    compiler_stub.write_text("# Source-check fixture; invoked by the fake Python tool.\n")
    caller = copied_repo / "unrelated caller"
    caller.mkdir()
    env = harness["env"]
    assert isinstance(env, dict)
    result = subprocess.run(
        [os.path.join("..", script.name), "--dry-run"],
        cwd=caller,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert os.fspath(copied_repo / "mcp").replace(" ", r"\ ") in result.stdout


@pytest.mark.parametrize("symlink_kind", ["file", "directory"])
def test_symlinked_installer_resolves_repository_with_spaces(harness, tmp_path, symlink_kind):
    link_parent = tmp_path / "installer links with spaces"
    link_parent.mkdir()
    if symlink_kind == "file":
        link = link_parent / "installer link.sh"
        link.symlink_to(os.path.relpath(SCRIPT, link_parent))
    else:
        link = link_parent / "scripts alias"
        link.symlink_to(SCRIPT.parent, target_is_directory=True)
        link = link / SCRIPT.name
    result = _run(harness, "--mcp", script=link)
    assert result.returncode == 0, result.stderr
    assert _calls(harness)[0][-1] == os.fspath(REPO / "mcp")


def test_stale_compiled_resources_stop_before_tool_install(harness):
    env = harness["env"]
    assert isinstance(env, dict)
    env["FRESHNESS_FAIL"] = "37"
    result = _run(harness, "--mcp")
    assert result.returncode == 37
    assert "freshness" in result.stderr
    assert _calls(harness) == []


@pytest.mark.parametrize("link_count", [3, 41])
def test_symlink_chain_resolves_or_stops_before_install(harness, tmp_path, link_count):
    target = SCRIPT
    for index in range(link_count):
        link = tmp_path / f"installer link {index}.sh"
        link.symlink_to(os.path.relpath(target, link.parent) if index % 2 else target)
        target = link
    # 显式使用 Bash，避免操作系统先拦截超长链接，确保覆盖脚本自身的防护。
    result = _run(harness, "--mcp", script=target, via_bash=link_count > 40)
    if link_count <= 40:
        assert result.returncode == 0, result.stderr
        assert _calls(harness)[0][-1] == os.fspath(REPO / "mcp")
    else:
        # 系统可能在 Bash 打开脚本时先拒绝过长链接链，早于脚本内的保护。
        assert result.returncode in {1, 126}
        expected_message = (
            "symlink chain exceeded"
            if result.returncode == 1
            else "Too many levels of symbolic links"
        )
        assert expected_message in result.stderr
        assert _calls(harness) == []


def test_cdpath_does_not_pollute_repository_resolution(harness, tmp_path):
    env = harness["env"]
    assert isinstance(env, dict)
    env["CDPATH"] = os.fspath(tmp_path)
    result = _run(harness, "--mcp")
    assert result.returncode == 0, result.stderr
    assert _calls(harness)[0][-1] == os.fspath(REPO / "mcp")


@pytest.mark.parametrize("action", ["install", "update"])
def test_skill_only_uses_installed_cli_without_mcp_prerequisites(harness, action):
    env = harness["env"]
    assert isinstance(env, dict)
    _write_executable(Path(env["LAUNCHER"]), Path(env["LAUNCHER_SOURCE"]).read_text())
    tools = harness["tools"]
    assert isinstance(tools, Path)
    (tools / "codex").unlink()
    (tools / "python3").unlink()
    result = _run(harness, "--skills", action, "--name", "custom-skill")
    assert result.returncode == 0, result.stderr
    assert _calls(harness) == [
        ["uv", "tool", "dir", "--bin"],
        ["setup", "skills", action, "--name", "custom-skill"],
    ]


@pytest.mark.parametrize("action", ["install", "update"])
def test_combined_mcp_and_skill_run_in_order(harness, action):
    result = _run(harness, "--mcp", "--skills", action)
    assert result.returncode == 0, result.stderr
    calls = _calls(harness)
    assert calls[0][:3] == ["uv", "tool", "install"]
    assert calls[1:] == [
        ["uv", "tool", "dir", "--bin"],
        ["setup", "setup", "codex"],
        ["setup", "skills", action, "--name", "token-io-decoupling-skill"],
    ]


@pytest.mark.parametrize(
    "args",
    [
        ("--skills",),
        ("--skills", "remove"),
        ("--skills", "install", "--skills", "update"),
        ("--name", "custom-skill"),
        ("--skills", "install", "--name"),
        ("--skills", "install", "--name", ""),
        ("--skills", "install", "--name", "one", "--name", "two"),
        ("--skills", "update", "--python", "3.14"),
    ],
)
def test_invalid_skill_arguments_have_no_side_effects(harness, args):
    result = _run(harness, *args)
    assert result.returncode == 2
    assert _calls(harness) == []


def test_skill_dry_run_does_not_require_tools_or_install_mcp(harness):
    env = harness["env"]
    assert isinstance(env, dict)
    env["PATH"] = "/nonexistent"
    result = _run(harness, "--skills", "update", "--dry-run")
    assert result.returncode == 0, result.stderr
    assert "skills update --name token-io-decoupling-skill" in result.stdout
    assert "uv tool install" not in result.stdout
    assert "setup codex" not in result.stdout
    assert _calls(harness) == []


def test_skill_only_requires_installed_management_cli(harness):
    result = _run(harness, "--skills", "install")
    assert result.returncode == 1
    assert "requires an installed management command" in result.stderr
    assert _calls(harness) == [["uv", "tool", "dir", "--bin"]]


@pytest.mark.parametrize("combined", [False, True])
def test_skill_failure_preserves_status(harness, combined):
    env = harness["env"]
    assert isinstance(env, dict)
    launcher_source = Path(env["LAUNCHER_SOURCE"])
    source = launcher_source.read_text().replace(
        "raise SystemExit(int(os.environ.get('SETUP_FAIL','0')))",
        "raise SystemExit(23 if sys.argv[1] == 'skills' else 0)",
    )
    launcher_source.write_text(source)
    _write_executable(Path(env["LAUNCHER"]), source)
    args = ["--mcp"] if combined else []
    result = _run(harness, *args, "--skills", "update")
    assert result.returncode == 23
    assert "Skill update failed (exit 23)" in result.stderr


def test_mcp_setup_failure_stops_before_skill(harness):
    env = harness["env"]
    assert isinstance(env, dict)
    env["SETUP_FAIL"] = "19"
    result = _run(harness, "--mcp", "--skills", "install")
    assert result.returncode == 19
    assert _calls(harness)[-1] == ["setup", "setup", "codex"]


def test_no_arguments_print_help_without_side_effects(harness):
    env = harness["env"]
    assert isinstance(env, dict)
    env["PATH"] = "/nonexistent"
    result = _run(harness)
    assert result.returncode == 0, result.stderr
    assert "用法：./tid [选项]" in result.stdout
    assert "--mcp" in result.stdout
    assert "--skills" in result.stdout
    assert result.stderr == ""
    assert _calls(harness) == []
    sentinel = harness["sentinel"]
    assert isinstance(sentinel, Path)
    assert sentinel.read_text(encoding="utf-8") == 'mcp_servers = "unchanged"\n'

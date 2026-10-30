"""Run all ordinary checks, update an isolated uv tool, then inspect via a fresh Codex."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from codex_sdk import _FINAL_INSPECTION, fixed_codex_session

WORKSPACE = Path(__file__).resolve().parents[2]
REPOSITORY = WORKSPACE.parent


def check_commands():
    python = sys.executable
    commands = [
        (
            "MCP pytest",
            [
                python,
                "-m",
                "pytest",
                "-q",
                "tests/unit_tests",
                "tests/mock_api_tests",
                "tests/real_api_tests",
            ],
            WORKSPACE,
        ),
        ("lint", ["uv", "run", "--no-sync", "ruff", "check"], WORKSPACE),
        ("format", ["uv", "run", "--no-sync", "ruff", "format", "--check"], WORKSPACE),
        ("types", ["uv", "run", "--no-sync", "ty", "check"], WORKSPACE),
        (
            "documentation regressions",
            [python, "-m", "unittest", "discover", "-s", "tests"],
            REPOSITORY,
        ),
    ]
    for script in (
        "check-multilingual-docs.py",
        "check-doc-layer-links.py",
        "check-layer-01-sections.py",
        "check-layer-02-04-provider-neutrality.py",
        "check-layer-04-workflow-maps.py",
    ):
        commands.append((script, [python, str(REPOSITORY / "scripts" / script)], REPOSITORY))
    commands.append(("whitespace", ["git", "diff", "--check"], REPOSITORY))
    return commands


def execute(label, command, cwd, env=None):
    result = subprocess.run(command, cwd=cwd, env=env, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(f"{label} failed; final SDK phase was not accepted")
    print(f"PASS: {label}", flush=True)


def update_tool(directory):
    artifacts = directory / "artifacts"
    execute(
        "build current wheels",
        [
            "uv",
            "build",
            "--all-packages",
            "--wheel",
            "--no-build-isolation",
            "--python",
            sys.executable,
            "--out-dir",
            str(artifacts),
        ],
        WORKSPACE,
    )
    env = {
        **os.environ,
        "UV_TOOL_DIR": str(directory / "tools"),
        "UV_TOOL_BIN_DIR": str(directory / "bin"),
    }
    wheel = artifacts / "token_io_decoupling-0.1.0-py3-none-any.whl"
    execute(
        "update isolated uv tool",
        [
            "uv",
            "tool",
            "install",
            "--force",
            "--reinstall",
            "--offline",
            "--python",
            sys.executable,
            "--find-links",
            str(artifacts),
            str(wheel),
        ],
        directory,
        env,
    )
    return directory / "bin/token-io-decoupling"


def run_final(checks, runner, installer, inspector):
    # No skip-checks path: an exception prevents installation and SDK launch.
    for label, command, cwd in checks:
        runner(label, command, cwd)
    installed = installer()
    return inspector(installed)


def main():
    executable = os.environ.get("TOKEN_IO_CODEX_CLI_PATH") or shutil.which("codex")
    if not executable:
        print("FAIL: installed Codex CLI unavailable")
        return 1
    for name in ("OPENAI_API_KEY", "OPENAI_BASE_URL"):
        if not os.environ.get(name, "").strip():
            print(f"FAIL: required process variable missing: {name}")
            return 1
    try:
        with tempfile.TemporaryDirectory(prefix="token-io-final-tool-") as temporary:

            def inspect(installed):
                command = [str(installed), "start-mcp-server", "--profile", "workflow"]
                with fixed_codex_session(
                    Path(executable).resolve(), command, phase=_FINAL_INSPECTION
                ) as session:
                    return session.check_mcp()

            report = run_final(
                check_commands(), execute, lambda: update_tool(Path(temporary)), inspect
            )
            print(json.dumps(report))
        return 0
    except Exception as error:
        # Only our bounded errors may be reported; never expose SDK config/stderr.
        from codex_sdk import CodexTestError

        if isinstance(error, CodexTestError) or type(error) is RuntimeError:
            print(f"FAIL: {error}")
        else:
            print(f"FAIL: final inspection prerequisite ({type(error).__name__})")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

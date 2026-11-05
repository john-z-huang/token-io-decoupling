"""Opt-in real installer/configuration smoke, using temporary stores and no model turns."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import tomlkit
from mcp import Client, StdioServerParameters
from mcp.types import TextContent

REPOSITORY = Path(__file__).resolve().parents[3]


def fixtures(root: Path) -> tuple[Path, Path]:
    project = root / "target project"
    data = project / ".serena"
    memories = data / "memories"
    (memories / "notes").mkdir(parents=True)
    home = root / "serena home"
    (home / "memories/global").mkdir(parents=True)
    (home / "serena_config.yml").write_text(
        json.dumps(
            {
                "project_serena_folder_location": "$projectDir/.serena",
                "ignored_memory_patterns": ["global_hidden/.*"],
                "read_only_memory_patterns": ["readonly/.*"],
            }
        ),
        encoding="utf-8",
    )
    (data / "project.yml").write_text(
        json.dumps(
            {
                "project_name": "installer-smoke",
                "languages": ["python"],
                "ignored_memory_patterns": ["old_project_hidden/.*"],
                "activation_command": "this command must never execute",
            }
        ),
        encoding="utf-8",
    )
    (data / "project.local.yml").write_text(
        json.dumps({"ignored_memory_patterns": ["local_hidden/.*"]}),
        encoding="utf-8",
    )
    (memories / "notes/install.md").write_text("before\n安装配置成功\n", encoding="utf-8")
    for topic in ("global_hidden", "local_hidden", "old_project_hidden", "readonly"):
        folder = memories / topic
        folder.mkdir()
        (folder / "record.md").write_text("policy fixture\n", encoding="utf-8")
    return project, home


def snapshot(root: Path) -> dict[str, tuple[int, bytes | None]]:
    return {
        str(path.relative_to(root)): (
            path.stat().st_mode,
            path.read_bytes() if path.is_file() else None,
        )
        for path in root.rglob("*")
    }


def check_backend(serena_python: Path) -> None:
    from token_io_decoupling.serena_memory_runtime import IsolatedSerenaMemoryService

    with tempfile.TemporaryDirectory(prefix="serena-backend-smoke-") as temporary:
        root = Path(temporary).resolve()
        project, home = fixtures(root)
        before = snapshot(root)
        previous_home = os.environ.get("SERENA_HOME")
        os.environ["SERENA_HOME"] = str(home)
        try:
            reader = IsolatedSerenaMemoryService(project, serena_python)
            capability = reader.capability()
            assert capability["status"] == "configured", capability.get("reason_code")
            result = reader.tail_read("mem:notes/install", 1)
            assert result["status"] == "available", result.get("reason_code")
            assert result["content"] == "安装配置成功\n" and result["total_lines"] == 2
            assert reader.write_check("notes/install", "安装配置成功\n", 1)["success"] is True
            assert reader.write_check("notes/install", "missing", 1)["success"] is False
            assert reader.tail_read("global_hidden/record", 1)["status"] == "unavailable"
            assert reader.tail_read("local_hidden/record", 1)["status"] == "unavailable"
            assert reader.tail_read("old_project_hidden/record", 1)["status"] == "available"
            assert reader.tail_read("readonly/record", 1)["status"] == "available"
        finally:
            if previous_home is None:
                os.environ.pop("SERENA_HOME", None)
            else:
                os.environ["SERENA_HOME"] = previous_home
        assert snapshot(root) == before, "read backend changed temporary configuration or data"


def _execute(command: list[str], cwd: Path, environment: dict[str, str]) -> str:
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=environment,
        capture_output=True,
        text=True,
        timeout=180,
    )
    if completed.returncode:
        diagnostic = completed.stderr
        stage = "command"
        if "uv tool installation/update failed" in diagnostic:
            stage = "source_tool_install"
        elif "Serena Memory preflight failed" in diagnostic:
            stage = "serena_preflight"
        elif "Codex setup failed" in diagnostic:
            stage = "codex_setup"
        elif "was not found on PATH" in diagnostic:
            stage = "prerequisite"
        normalized = diagnostic.lower().replace("_", "-")
        print(
            "FAIL: installer smoke subprocess "
            + json.dumps(
                {
                    "stage": stage,
                    "exit_code": completed.returncode,
                    "dependency_resolution": "no solution found" in normalized,
                    "workspace_dependency": "token-io-decoupling-core" in normalized,
                    "build_failure": "failed to build" in normalized,
                    "preflight_reason": next(
                        iter(
                            re.findall(
                                r"Serena Memory preflight failed \(([a-z0-9_]{1,96})\)", diagnostic
                            )
                        ),
                        None,
                    ),
                }
            ),
            flush=True,
        )
        raise RuntimeError(
            "Serena installer/configuration smoke failed; captured output suppressed"
        )
    return completed.stdout


def verify_installation(directory: Path, serena_python: Path) -> None:
    """Run only after ordinary checks and the coordinator's current-wheel installation."""
    # macOS tempfile may use /var; the backend requires canonical, non-symlink roots.
    directory = directory.resolve(strict=True)
    if not serena_python.is_absolute() or not serena_python.is_file():
        raise RuntimeError("explicit existing Serena Python is required for installer smoke")
    codex = shutil.which("codex")
    if codex is None:
        raise RuntimeError("installed Codex CLI is required for installer smoke")
    root = directory / "serena-installer"
    root.mkdir()
    project, home = fixtures(root)
    data_before = snapshot(project)
    home_before = snapshot(home)
    codex_home = root / "codex configuration"
    codex_home.mkdir()
    (codex_home / "config.toml").write_text("# isolated installer test\n", encoding="utf-8")
    # Expose the existing isolated Serena env to this temporary uv tool root, without modifying it.
    (directory / "tools/serena-agent").symlink_to(
        serena_python.parent.parent, target_is_directory=True
    )
    environment = {
        **os.environ,
        "UV_TOOL_DIR": str(directory / "tools"),
        "UV_TOOL_BIN_DIR": str(directory / "bin"),
        "UV_OFFLINE": "1",
        "CODEX_HOME": str(codex_home),
        "SERENA_HOME": str(home),
    }
    installer = REPOSITORY / "scripts/install-codex-mcp.sh"
    _execute(
        ["/bin/bash", str(installer), "--serena-project-root", str(project)], root, environment
    )
    print("PASS: documented installer ran with isolated Codex/uv directories", flush=True)
    document = tomlkit.parse((codex_home / "config.toml").read_text(encoding="utf-8"))
    servers = document["mcp_servers"]
    workflow = servers["token-io-decoupling-workflow"]
    arguments = list(workflow["args"])
    assert arguments[:3] == ["start-mcp-server", "--profile", "workflow"]
    assert arguments[3:5] == ["--serena-project-root", str(project.resolve())]
    assert arguments[5] == "--serena-python"
    assert Path(arguments[6]).name == "python" and Path(arguments[6]).parent.name == "bin"
    assert "SERENA_HOME" in workflow["env_vars"]
    for name in (
        "token-io-decoupling-root-agent-tools",
        "token-io-decoupling-worker-agent-tools",
        "token-io-decoupling-share-tools",
    ):
        assert "--serena-project-root" not in servers[name]["args"]
        assert "SERENA_HOME" not in servers[name]["env_vars"]

    print("PASS: workflow project/interpreter and forwarding persisted", flush=True)

    async def call_tools() -> None:
        parameters = StdioServerParameters(
            command=str(workflow["command"]),
            args=arguments,
            cwd=str(root),
            env={"SERENA_HOME": str(home)},
        )
        async with Client(parameters, mode="auto") as client:

            async def value(name: str, payload: dict[str, Any]) -> dict[str, Any]:
                response = await client.call_tool(name, payload)
                assert not response.is_error and isinstance(response.content[0], TextContent)
                return json.loads(response.content[0].text)

            capability = await value("workflow_capabilities", {})
            assert capability["serena_memory_reads"] == "configured"
            result = await value(
                "serena_memory_tail_read",
                {"memory_path": "notes/install", "tail_lines": 1},
            )
            assert result["content"] == "安装配置成功\n"
            checked = await value(
                "serena_memory_write_check",
                {
                    "memory_path": "notes/install",
                    "changed_content": "安装配置成功\n",
                    "tail_lines": 1,
                },
            )
            assert checked["success"] is True

    asyncio.run(call_tools())
    print("PASS: installed configured tail read and write check", flush=True)
    config_before = (codex_home / "config.toml").read_bytes()
    _execute(
        [
            str(directory / "bin/token-io-decoupling"),
            "setup",
            "codex",
            "--serena-project-root",
            str(project),
        ],
        root,
        environment,
    )
    assert (codex_home / "config.toml").read_bytes() == config_before
    assert snapshot(project) == data_before and snapshot(home) == home_before
    print("PASS: real documented installer, uv Serena discovery, persisted binding and tool calls")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--serena-python", type=Path, required=True)
    arguments = parser.parse_args()
    check_backend(arguments.serena_python)
    print("PASS: real isolated uv Serena backend; temporary configuration unchanged")

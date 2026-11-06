"""Smoke-test the two installed MCP executables through real stdio subprocesses."""

from __future__ import annotations

import argparse
import asyncio
import os
import subprocess
import tempfile
from pathlib import Path

from installed_stdio_checks.delegation import check_delegation_denials
from installed_stdio_checks.protocol import SERVER_NAMES, check_discovery, check_memory_scope
from installed_stdio_checks.workflow import (
    check_capabilities,
    check_context_denial,
    check_rule_instructions,
)
from mcp import Client, StdioServerParameters


def _prepare_project(cwd: Path, repo_root: Path, memory_content: str | None) -> None:
    """只在仓库外准备隔离项目；Memory 初值用于检查服务启动目录隔离。"""
    if cwd.is_relative_to(repo_root):
        raise AssertionError("stdio subprocess working directory must be outside the checkout")
    if memory_content is not None:
        memory_file = cwd / ".serena" / "memories" / "notes.md"
        memory_file.parent.mkdir(parents=True)
        memory_file.write_text(memory_content, encoding="utf-8")


async def _exercise(
    cli_path: Path,
    server_kind: str,
    repo_root: Path,
    memory_content: str | None = None,
) -> None:
    """在仓库外临时项目启动实际安装服务，按职责验证协议且禁止意外写入工作目录。"""
    if not cli_path.is_absolute():
        raise AssertionError("installed CLI path must be absolute")
    cli_path = cli_path.resolve(strict=True)
    if cli_path.is_relative_to(repo_root):
        raise AssertionError("installed CLI must be an absolute path outside the checkout")
    with tempfile.TemporaryDirectory(prefix="token-io-installed-stdio-") as temporary:
        cwd = Path(temporary).resolve()
        _prepare_project(cwd, repo_root, memory_content)
        parameters = StdioServerParameters(
            command=str(cli_path),
            args=[],
            cwd=str(cwd),
            env={
                "PATH": "" if memory_content is not None else os.defpath,
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONPATH": "",
            },
        )
        async with Client(parameters, mode="auto") as client:
            await check_discovery(client, server_kind)
            if server_kind == "tools" and memory_content is not None:
                await check_memory_scope(client, memory_content)
            if server_kind == "workflow":
                await check_capabilities(client)
                await check_context_denial(client)
                await check_delegation_denials(client)
                await check_rule_instructions(client)
            expected_entries = {".serena"} if memory_content is not None else set()
            if {entry.name for entry in cwd.iterdir()} != expected_entries:
                raise AssertionError(
                    "public stdio calls wrote into their temporary working directory"
                )


def _exercise_codex_dry_run(cli_path: Path, repo_root: Path) -> None:
    """隔离 CODEX_HOME 与 PATH 检查安装干跑，只输出配置方案且不改用户配置。"""
    if cli_path.name != "token-io-decoupling" or not cli_path.is_file():
        raise AssertionError(f"installed unified executable is missing or mislabeled: {cli_path}")
    if os.name != "nt" and not os.access(cli_path, os.X_OK):
        raise AssertionError("installed executable is not executable")
    with tempfile.TemporaryDirectory(prefix="token-io-codex-dry-run-") as temporary:
        temporary_path = Path(temporary).resolve()
        if temporary_path.is_relative_to(repo_root):
            raise AssertionError("setup dry-run working directory must be outside the checkout")
        empty_path = temporary_path / "empty-path"
        empty_path.mkdir()
        result = subprocess.run(
            [str(cli_path), "setup", "codex", "--dry-run"],
            cwd=temporary_path,
            env={
                "CODEX_HOME": str(temporary_path),
                "PATH": str(empty_path),
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONPATH": "",
            },
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
        if result.returncode != 0:
            raise AssertionError(
                f"installed setup dry-run failed ({result.returncode}): {result.stderr.strip()}"
            )
        lines = result.stdout.splitlines()
        if (temporary_path / "config.toml").exists():
            raise AssertionError("setup dry-run wrote a Codex configuration")
        for name in SERVER_NAMES.values():
            command = cli_path.with_name(name).resolve(strict=True)
            if f"Would configure {name}: {command} (args=[])" not in lines:
                raise AssertionError(f"setup dry-run omitted the installed {name} command")
        if (
            "OPENAI_TIMEOUT_MAX_RETRIES" not in result.stdout
            or "工具发现不产生权限" not in result.stdout
        ):
            raise AssertionError("setup dry-run omitted environment forwarding or install limits")


def main() -> None:
    """分别用项目 A/B 检查两服务，再执行统一安装入口干跑，覆盖项目隔离和安装声明。"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--cli", required=True, type=Path)
    args = parser.parse_args()
    repo_root = Path(__file__).resolve().parents[6]
    cli_path = args.cli.resolve(strict=True)
    for content in ("synthetic project A\n", "synthetic project B\n"):
        workflow = cli_path.with_name(SERVER_NAMES["workflow"])
        asyncio.run(_exercise(workflow, "workflow", repo_root, content))
        tools = cli_path.with_name(SERVER_NAMES["tools"])
        asyncio.run(_exercise(tools, "tools", repo_root, content))
    _exercise_codex_dry_run(cli_path, repo_root)
    print("installed workflow and tools discovery: ok")


if __name__ == "__main__":
    main()

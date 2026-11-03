from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from mcp import Client, StdioServerParameters
from mcp.types import TextContent

from token_io_decoupling_dev.server import (
    SERVER_DESCRIPTION,
    SERVER_INSTRUCTIONS,
    SERVER_NAME,
    TOOL_DESCRIPTION,
    create_server,
    dev_capabilities,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PROJECT_ROOT / "src"


def _result_payload(result: Any) -> dict[str, Any]:
    structured = getattr(result, "structured_content", None)
    if structured is not None:
        return structured
    for item in result.content:
        if isinstance(item, TextContent):
            return json.loads(item.text)
    raise AssertionError("tool result contained neither structured content nor JSON text")


def test_capability_inventory_is_stable_truthful_and_fresh() -> None:
    first = dev_capabilities()
    first["unavailable"].clear()

    second = dev_capabilities()
    assert second["status"] == "skeleton"
    assert [item["id"] for item in second["implemented"]] == ["dev_capabilities"]
    assert {item["id"] for item in second["unavailable"]} == {
        "rule_compiler",
        "project_compliance_checks",
        "output_materialization",
    }
    assert all(item["status"] == "unavailable" for item in second["unavailable"])
    assert second["side_effects"] == {
        "network": False,
        "openai_api": False,
        "filesystem_read": False,
        "filesystem_write": False,
        "git_or_github": False,
        "memory_read_or_write": False,
    }


def test_in_process_server_exposes_only_no_argument_capability_tool() -> None:
    async def inspect_server() -> None:
        async with Client(create_server(), mode="auto") as client:
            assert client.server_info is not None
            assert client.server_info.name == SERVER_NAME
            assert client.server_info.version == "0.1.0"
            assert client.server_info.description == SERVER_DESCRIPTION
            assert client.instructions == SERVER_INSTRUCTIONS

            listed = await client.list_tools()
            assert [tool.name for tool in listed.tools] == ["dev_capabilities"]
            tool = listed.tools[0]
            assert tool.description == TOOL_DESCRIPTION
            assert tool.annotations is not None
            assert tool.annotations.read_only_hint is True
            assert tool.annotations.destructive_hint is False
            assert tool.annotations.idempotent_hint is True
            assert tool.annotations.open_world_hint is False
            assert tool.input_schema["properties"] == {}
            assert tool.input_schema.get("required", []) == []

            result = await client.call_tool("dev_capabilities", {})
            assert not result.is_error
            assert _result_payload(result) == dev_capabilities()

    asyncio.run(inspect_server())


def test_negotiated_stdio_startup_and_call_without_project_side_effects(tmp_path: Path) -> None:
    async def inspect_stdio() -> None:
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "token_io_decoupling_dev", "--stdio"],
            env={
                **os.environ,
                "PYTHONPATH": str(SOURCE_ROOT),
                "PYTHONDONTWRITEBYTECODE": "1",
                "HOME": str(tmp_path / "home"),
            },
            cwd=str(tmp_path),
        )
        async with Client(params, mode="auto") as client:
            assert client.server_info is not None
            assert client.server_info.name == SERVER_NAME
            assert client.instructions == SERVER_INSTRUCTIONS
            listed = await client.list_tools()
            assert [tool.name for tool in listed.tools] == ["dev_capabilities"]
            tool = listed.tools[0]
            assert tool.annotations is not None
            assert tool.annotations.read_only_hint is True
            assert tool.annotations.destructive_hint is False
            assert tool.annotations.idempotent_hint is True
            assert tool.annotations.open_world_hint is False
            result = await client.call_tool("dev_capabilities", {})
            assert not result.is_error
            assert _result_payload(result)["status"] == "skeleton"

    asyncio.run(inspect_stdio())
    assert list(tmp_path.iterdir()) == []


def test_cli_help_version_and_default_stdio_contract() -> None:
    env = {
        **os.environ,
        "PYTHONPATH": str(SOURCE_ROOT),
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    help_result = subprocess.run(
        [sys.executable, "-m", "token_io_decoupling_dev", "--help"],
        cwd=PROJECT_ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert help_result.returncode == 0
    assert "--stdio" in help_result.stdout
    assert "read-only capability discovery" in help_result.stdout

    version_result = subprocess.run(
        [sys.executable, "-m", "token_io_decoupling_dev", "--version"],
        cwd=PROJECT_ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert version_result.returncode == 0
    assert version_result.stdout.strip() == "0.1.0"


def test_runtime_dependency_boundary_is_standalone() -> None:
    import tomllib

    project = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text())
    dependencies = project["project"]["dependencies"]
    assert dependencies == ["mcp>=2.3,<3"]
    assert project["project"]["name"] == "token-io-decoupling-dev"
    assert project["project"]["scripts"]["token-io-decoupling-dev"] == (
        "token_io_decoupling_dev.cli:main"
    )


def test_source_imports_do_not_depend_on_product_runtime() -> None:
    import ast

    forbidden = {
        "token_io_decoupling",
        "token_io_decoupling_core",
        "token_io_decoupling_state",
        "token_io_decoupling_workflow",
        "token_io_decoupling_root",
        "token_io_decoupling_worker",
    }
    for source in (PROJECT_ROOT / "src").rglob("*.py"):
        tree = ast.parse(source.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                roots = {alias.name.split(".", 1)[0] for alias in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                roots = {node.module.split(".", 1)[0]}
            else:
                continue
            assert roots.isdisjoint(forbidden), f"product runtime import in {source}: {roots}"

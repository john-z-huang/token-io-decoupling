"""Smoke-test an installed wheel through an isolated real stdio subprocess."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import tempfile
from pathlib import Path

from mcp import Client, StdioServerParameters

EXPECTED_TOOLS = {
    "workflow_capabilities",
    "rules_get_context",
    "database_schema_status",
}


def _text(result: object) -> str:
    content = getattr(result, "content", None)
    if not content:
        raise AssertionError("stdio call returned no content")
    return "\n".join(getattr(item, "text", "") for item in content)


async def _exercise(cli_path: Path, repo_root: Path) -> None:
    if not cli_path.is_absolute():
        raise AssertionError("installed CLI path must be absolute")
    cli_path = cli_path.resolve(strict=True)
    if cli_path.is_relative_to(repo_root):
        raise AssertionError("installed CLI must be an absolute path outside the checkout")

    with tempfile.TemporaryDirectory(prefix="token-io-installed-stdio-") as temporary:
        cwd = Path(temporary).resolve()
        if cwd.is_relative_to(repo_root):
            raise AssertionError("stdio subprocess working directory must be outside the checkout")
        parameters = StdioServerParameters(
            command=str(cli_path),
            cwd=str(cwd),
            env={
                "PATH": os.defpath,
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONPATH": "",
            },
        )
        async with Client(parameters, mode="auto") as client:
            if client.protocol_version != "2026-07-28":
                raise AssertionError(
                    f"unexpected negotiated MCP protocol: {client.protocol_version}"
                )
            tools = await client.list_tools()
            names = {tool.name for tool in tools.tools}
            if names != EXPECTED_TOOLS:
                raise AssertionError(f"unbound installed CLI exposed unexpected tools: {names}")

            capabilities = await client.call_tool("workflow_capabilities", {})
            capability_data = json.loads(_text(capabilities))
            if capabilities.is_error or capability_data.get("mode_fallback") != "Native":
                raise AssertionError("installed unbound CLI did not report Native fallback")

            english = await client.call_tool(
                "rules_get_context",
                {"payload": {"node_id": "contract", "language": "en"}},
            )
            if english.is_error or "Before Mode and Session pass" not in _text(english):
                raise AssertionError("installed wheel did not return the English Contract rule")
            chinese = await client.call_tool(
                "rules_get_context",
                {"payload": {"node_id": "contract", "language": "zh_cn"}},
            )
            if chinese.is_error or "Mode 和 Session 通过前" not in _text(chinese):
                raise AssertionError("installed wheel did not return the Chinese Contract rule")
            status = await client.call_tool("database_schema_status", {})
            status_text = _text(status)
            if status.is_error or '"available": false' not in status_text:
                raise AssertionError("unbound schema status was not unavailable")
            if "no state path was inspected" not in status_text:
                raise AssertionError("unbound schema status inspected a state path")
            if list(cwd.iterdir()):
                raise AssertionError(
                    "public stdio calls wrote into their temporary working directory"
                )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cli", required=True, type=Path)
    args = parser.parse_args()
    repo_root = Path(__file__).resolve().parents[2]
    asyncio.run(_exercise(args.cli, repo_root))
    print("installed wheel stdio discovery: ok")


if __name__ == "__main__":
    main()

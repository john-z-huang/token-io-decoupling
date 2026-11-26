"""Inspect the sole installed tools executable over stdio without API calls."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import tempfile
from pathlib import Path

from mcp import Client, StdioServerParameters
from token_io_decoupling_core.server_tools import TOOLS_SERVER_TOOLS


async def _exercise(cli_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[3]
    if not cli_path.is_absolute():
        raise AssertionError("installed CLI path must be absolute")
    cli_path = cli_path.resolve(strict=True)
    assert not cli_path.is_relative_to(repo_root)
    with tempfile.TemporaryDirectory(prefix="token-io-installed-stdio-") as temporary:
        cwd = Path(temporary)
        memory = cwd / ".serena/memories/notes.md"
        memory.parent.mkdir(parents=True)
        memory.write_text("synthetic local memory\n", encoding="utf-8")
        parameters = StdioServerParameters(
            command=str(cli_path), args=[], cwd=str(cwd),
            env={"PATH": os.defpath, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": ""},
        )
        async with Client(parameters, mode="auto") as client:
            assert client.server_info is not None
            assert client.server_info.name == "token-io-decoupling-tools"
            assert client.server_info.description and client.instructions
            tools = (await client.list_tools()).tools
            names = {tool.name for tool in tools}
            assert names == set(TOOLS_SERVER_TOOLS)
            assert len(names) == 34
            assert all(tool.description for tool in tools)
            assert not any(name.startswith(("workflow_", "task_plan_")) for name in names)
            result = await client.call_tool(
                "serena_memory_tail_read", {"memory_path": "notes", "tail_lines": 1}
            )
            assert not result.is_error
            data = json.loads(result.content[0].text)
            assert data["content"] == "synthetic local memory\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cli", type=Path, required=True)
    args = parser.parse_args()
    asyncio.run(_exercise(args.cli))


if __name__ == "__main__":
    main()

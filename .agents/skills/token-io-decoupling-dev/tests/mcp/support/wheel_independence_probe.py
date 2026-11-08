"""隔离 wheel 环境中的依赖缺失断言与真实 stdio 场景。"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import sys
from pathlib import Path

from mcp import Client, StdioServerParameters


def check_available_distributions(service: str) -> None:
    sibling = "workflow" if service == "tools" else "tools"
    assert importlib.util.find_spec("token_io_decoupling_" + sibling) is None
    assert importlib.util.find_spec("token_io_decoupling") is None
    if service == "tools":
        assert importlib.util.find_spec("token_io_decoupling_core.rules") is None
    else:
        assert importlib.util.find_spec("dev_workflow_standards_tools") is None


async def run(service: str) -> None:
    executable = Path(sys.executable).with_name("token-io-decoupling-" + service)
    async with Client(StdioServerParameters(command=str(executable), args=[])) as client:
        tools = (await client.list_tools()).tools
        assert len(tools) == (41 if service == "tools" else 11)
        if service == "tools":
            result = await client.call_tool(
                "serena_memory_tail_read", {"memory_path": "notes", "tail_lines": 1}
            )
            assert not result.is_error
            assert json.loads(result.content[0].text)["content"] == "wheel-only Memory\n"
        else:
            result = await client.call_tool(
                "rules_get_context", {"payload": {"node_id": "contract", "context_version": 2}}
            )
            assert not result.is_error
            assert json.loads(result.content[0].text)["complete"]


if __name__ == "__main__":
    service = sys.argv[1]
    check_available_distributions(service)
    asyncio.run(run(service))

"""独立进程内的服务导入守卫和真实 MCP 场景断言。"""

from __future__ import annotations

import asyncio
import importlib.abc
import json
import sys
from pathlib import Path

from mcp import Client


class DenySibling(importlib.abc.MetaPathFinder):
    def __init__(self, service):
        self.sibling = "workflow" if service == "tools" else "tools"

    def find_spec(self, fullname, path=None, target=None):
        if fullname == "dev_workflow_standards_tools.server":
            raise AssertionError("runtime imported an upstream server composition root")
        if fullname == "token_io_decoupling" or fullname.startswith("token_io_decoupling."):
            raise AssertionError("runtime imported the admin distribution")
        if fullname == "token_io_decoupling_" + self.sibling or fullname.startswith(
            "token_io_decoupling_" + self.sibling + "."
        ):
            raise AssertionError("runtime imported its sibling distribution")


def _unconfigured_plan_payload(project_root: Path):
    return {
        "payload": {
            "request": {
                "project_root": str(project_root),
                "plan_id": "standalone",
                "expected_revision": None,
                "request_id": "create-1",
                "records": [
                    {
                        "record_id": "goal",
                        "kind": "goal",
                        "text": "Independent plan",
                        "sources": ["test"],
                    }
                ],
            }
        }
    }


async def check_tools(client, listed):
    assert len(listed) == 41
    result = await client.call_tool(
        "serena_memory_write_check",
        {"memory_path": "notes", "changed_content": "independent Memory", "tail_lines": 1},
    )
    assert not result.is_error
    assert json.loads(result.content[0].text)["success"]
    unavailable = await client.call_tool("task_plan_update", _unconfigured_plan_payload(Path.cwd()))
    assert not unavailable.is_error
    assert json.loads(unavailable.content[0].text)["status"] == "unavailable"
    result = await client.call_tool(
        "serena_memory_tail_read", {"memory_path": "notes", "tail_lines": 1}
    )
    assert json.loads(result.content[0].text)["content"] == "independent Memory\n"
    check_tools_metadata(listed)


def check_tools_metadata(listed):
    for tool in listed:
        for token in (
            "rules_get_context",
            "workflow_capabilities",
            "SM01",
            "MM01",
            "generate_skill_content first",
        ):
            assert token not in tool.description
    from token_io_decoupling_tools.tool_metadata import SERVER_INSTRUCTIONS

    assert "先调用" not in SERVER_INSTRUCTIONS
    assert "选择与顺序" not in SERVER_INSTRUCTIONS


async def check_workflow(client, listed):
    assert len(listed) == 11
    assert all(not tool.name.startswith(("task_plan_", "serena_memory_")) for tool in listed)
    result = await client.call_tool(
        "rules_get_context", {"payload": {"node_id": "contract", "context_version": 2}}
    )
    assert not result.is_error
    assert json.loads(result.content[0].text)["complete"]
    caps = await client.call_tool("workflow_capabilities", {})
    data = json.loads(caps.content[0].text)
    assert "task_plan_tools" not in data
    assert "serena_memory_binding" not in data


async def run(service: str) -> None:
    if service == "tools":
        from token_io_decoupling_tools.server import create_tools_server as create
    else:
        from token_io_decoupling_workflow.server import create_workflow_server as create
    async with Client(create()) as client:
        listed = (await client.list_tools()).tools
        if service == "tools":
            await check_tools(client, listed)
        else:
            await check_workflow(client, listed)


def main(service: str) -> None:
    # 必须在导入运行时组合根之前安装守卫，验证缺少兄弟分发包时仍可独立服务。
    sys.meta_path.insert(0, DenySibling(service))
    asyncio.run(run(service))


if __name__ == "__main__":
    main(sys.argv[1])

"""Exercise real MCP calls while forbidden sibling imports fail immediately."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.parametrize("service", ["tools", "workflow"])
def test_services_never_import_the_sibling_or_admin(service: str, tmp_path: Path) -> None:
    memory = tmp_path / ".serena/memories"
    memory.mkdir(parents=True)
    (memory / "notes.md").write_text("independent Memory\n", encoding="utf-8")
    code = r"""
import asyncio
import importlib.abc
import json
import sys
from mcp import Client

service = sys.argv[1]
sibling = "workflow" if service == "tools" else "tools"


class DenySibling(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "dev_workflow_standards_tools.server":
            raise AssertionError("runtime imported an upstream server composition root")
        if fullname == "token_io_decoupling" or fullname.startswith(
            "token_io_decoupling."
        ):
            raise AssertionError("runtime imported the admin distribution")
        if fullname == "token_io_decoupling_" + sibling or fullname.startswith(
            "token_io_decoupling_" + sibling + "."
        ):
            raise AssertionError("runtime imported its sibling distribution")


sys.meta_path.insert(0, DenySibling())
if service == "tools":
    from token_io_decoupling_tools.server import create_tools_server as create
else:
    from token_io_decoupling_workflow.server import create_workflow_server as create


async def run():
    async with Client(create()) as client:
        listed = (await client.list_tools()).tools
        if service == "tools":
            assert len(listed) == 41
            # The first operation is a direct Memory query, with no diagnostic or route call.
            result = await client.call_tool(
                "serena_memory_write_check",
                {
                    "memory_path": "notes",
                    "changed_content": "independent Memory",
                    "tail_lines": 1,
                },
            )
            assert not result.is_error
            assert json.loads(result.content[0].text)["success"]
            unavailable = await client.call_tool(
                "task_plan_update",
                {
                    "payload": {
                        "request": {
                            "project_root": str(__import__("pathlib").Path.cwd()),
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
                },
            )
            assert not unavailable.is_error
            assert json.loads(unavailable.content[0].text)["status"] == "unavailable"
            result = await client.call_tool(
                "serena_memory_tail_read", {"memory_path": "notes", "tail_lines": 1}
            )
            assert (
                json.loads(result.content[0].text)["content"] == "independent Memory\n"
            )
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
        else:
            assert len(listed) == 11
            assert all(
                not tool.name.startswith(("task_plan_", "serena_memory_"))
                for tool in listed
            )
            result = await client.call_tool(
                "rules_get_context",
                {"payload": {"node_id": "contract", "context_version": 2}},
            )
            assert not result.is_error
            assert json.loads(result.content[0].text)["complete"]
            caps = await client.call_tool("workflow_capabilities", {})
            data = json.loads(caps.content[0].text)
            assert "task_plan_tools" not in data
            assert "serena_memory_binding" not in data


asyncio.run(run())
"""
    env = {
        key: value
        for key, value in os.environ.items()
        if key
        not in {
            "OPENAI_API_KEY",
            "OPENAI_BASE_URL",
            "PYTHONPATH",
        }
    }
    completed = subprocess.run(
        [sys.executable, "-c", code, service],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        timeout=30,
    )
    assert completed.returncode == 0, completed.stderr

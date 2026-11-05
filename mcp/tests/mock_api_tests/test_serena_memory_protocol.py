from __future__ import annotations

import asyncio
import json
from typing import Any

from mcp import Client
from mcp.shared.exceptions import MCPError
from mcp.types import TextContent
from token_io_decoupling_workflow.serena_memory import SerenaMemoryReadService

from token_io_decoupling.server import create_workflow_server


def receipt(result: Any) -> dict[str, Any]:
    assert not result.is_error
    assert isinstance(result.content[0], TextContent)
    return json.loads(result.content[0].text)


class Reader(SerenaMemoryReadService):
    def __init__(self) -> None:
        super().__init__()
        self.calls: list[tuple[object, ...]] = []

    def capability(self) -> dict[str, Any]:
        return {"status": "configured", "reason_code": "protocol_fixture"}

    def tail_read(self, memory_path: str, tail_lines: int) -> dict[str, Any]:
        self.calls.append(("tail", memory_path, tail_lines))
        return {"status": "available", "content": "新增记录\n", "total_lines": 9}

    def write_check(
        self, memory_path: str, changed_content: str, tail_lines: int
    ) -> dict[str, Any]:
        self.calls.append(("check", memory_path, changed_content, tail_lines))
        return {"status": "available", "success": True, "reason": "content_found_in_tail"}


def test_flat_wire_contract_and_configured_dispatch() -> None:
    async def run() -> None:
        reader = Reader()
        async with Client(create_workflow_server(serena_memory_service=reader)) as client:
            tools = {tool.name: tool for tool in (await client.list_tools()).tools}
            for name, fields in (
                ("serena_memory_tail_read", {"memory_path", "tail_lines"}),
                ("serena_memory_write_check", {"memory_path", "changed_content", "tail_lines"}),
            ):
                tool = tools[name]
                schema = tool.model_dump(by_alias=True)["inputSchema"]
                assert set(schema["properties"]) == set(schema["required"]) == fields
                assert tool.annotations is not None and tool.annotations.read_only_hint
                assert tool.description is not None and "payload envelope" in tool.description
            caps = receipt(await client.call_tool("workflow_capabilities", {}))
            assert caps["serena_memory_reads"] == "configured"
            tail = receipt(
                await client.call_tool(
                    "serena_memory_tail_read", {"memory_path": "mem:plans/test", "tail_lines": 2}
                )
            )
            assert tail["content"] == "新增记录\n"
            checked = receipt(
                await client.call_tool(
                    "serena_memory_write_check",
                    {
                        "memory_path": "mem:plans/test",
                        "changed_content": "新增记录",
                        "tail_lines": 2,
                    },
                )
            )
            assert checked["success"] is True
            assert reader.calls == [
                ("tail", "mem:plans/test", 2),
                ("check", "mem:plans/test", "新增记录", 2),
            ]

    asyncio.run(run())


def test_unconfigured_tools_are_discoverable_but_unavailable() -> None:
    async def run() -> None:
        async with Client(create_workflow_server()) as client:
            caps = receipt(await client.call_tool("workflow_capabilities", {}))
            assert caps["serena_memory_reads"] == "unavailable"
            for name, args in (
                ("serena_memory_tail_read", {"memory_path": "mem:notes", "tail_lines": 1}),
                (
                    "serena_memory_write_check",
                    {"memory_path": "mem:notes", "changed_content": "new", "tail_lines": 1},
                ),
            ):
                assert receipt(await client.call_tool(name, args))["status"] == "unavailable"

    asyncio.run(run())


def test_wire_validation_rejects_invalid_windows_and_empty_expected_text() -> None:
    async def run() -> None:
        reader = Reader()
        async with Client(create_workflow_server(serena_memory_service=reader)) as client:
            invalid_calls = [
                ("serena_memory_tail_read", {"memory_path": "notes", "tail_lines": value})
                for value in (-1, True, "2", 10001)
            ]
            invalid_calls.append(
                (
                    "serena_memory_write_check",
                    {"memory_path": "notes", "changed_content": "", "tail_lines": 1},
                )
            )
            for name, arguments in invalid_calls:
                try:
                    response = await client.call_tool(name, arguments)
                except MCPError:
                    pass
                else:
                    assert response.is_error
            assert not reader.calls

    asyncio.run(run())

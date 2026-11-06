"""验证安装后协议发现与当前项目 Memory，保留真实客户端结果断言。"""

from __future__ import annotations

import json

from mcp import Client

from token_io_decoupling_core.server_tools import TOOLS_SERVER_TOOLS, WORKFLOW_TOOLS

EXPECTED_TOOLS = {"workflow": WORKFLOW_TOOLS, "tools": TOOLS_SERVER_TOOLS}
SERVER_NAMES = {"workflow": "token-io-decoupling-workflow", "tools": "token-io-decoupling-tools"}


def result_text(result: object) -> str:
    """仅拼接协议中的文本内容，供随后 JSON 检查使用。"""
    content = getattr(result, "content", None)
    if not content:
        raise AssertionError("stdio call returned no content")
    return "\n".join(getattr(item, "text", "") for item in content)


async def check_discovery(client: Client, server_kind: str) -> None:
    """核对实际协商的服务身份、工具清单与输入schema，防止启动了错误或过期可执行文件。"""
    if client.protocol_version != "2026-07-28":
        raise AssertionError(f"unexpected negotiated MCP protocol: {client.protocol_version}")
    if (
        client.server_info is None
        or not client.server_info.description
        or not client.instructions
        or client.server_info.name != SERVER_NAMES[server_kind]
    ):
        raise AssertionError(f"installed {server_kind} server omitted discovery metadata")
    tools = await client.list_tools()
    if server_kind == "tools" and "workflow_capabilities" in client.instructions:
        raise AssertionError("standalone tools inherited workflow entry instructions")
    names = {tool.name for tool in tools.tools}
    if names != EXPECTED_TOOLS[server_kind]:
        raise AssertionError(f"unbound {server_kind} server exposed unexpected tools: {names}")
    if any(not tool.description for tool in tools.tools):
        raise AssertionError(f"installed {server_kind} server has an undescribed tool")


async def check_memory_scope(client: Client, memory_content: str) -> None:
    """在两个独立临时项目读取各自 Memory，证明安装服务按启动项目隔离而不借用旧状态。"""
    tail = await client.call_tool(
        "serena_memory_tail_read", {"memory_path": "notes", "tail_lines": 1}
    )
    tail_data = json.loads(result_text(tail))
    if tail.is_error or tail_data.get("content") != memory_content:
        raise AssertionError("installed local Memory tail did not match this project")
    check = await client.call_tool(
        "serena_memory_write_check",
        {
            "memory_path": "mem:notes.md",
            "changed_content": memory_content.strip(),
            "tail_lines": 1,
        },
    )
    check_data = json.loads(result_text(check))
    if check.is_error or check_data.get("success") is not True:
        raise AssertionError("installed local Memory check did not match this project")

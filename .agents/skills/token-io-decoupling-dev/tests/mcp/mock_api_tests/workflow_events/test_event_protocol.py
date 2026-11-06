"""通过 MCP 线协议验证静态事件与可选建议的独立调用。"""

from __future__ import annotations

import asyncio
import json

import pytest
from mcp import Client
from mcp.types import CallToolResult, TextContent
from support.event_cases import EVENT_REQUIREMENTS, FakeClient, request_data, response

from token_io_decoupling_workflow.decisions import DecisionsRuntimeConfig
from token_io_decoupling_workflow.server import create_workflow_server


def _wire_text(result: CallToolResult) -> str:
    """先确认成功且为 TextContent，再解析 JSON，非文本内容不能静默当成正常回复。"""
    assert not result.is_error
    content = result.content[0]
    assert isinstance(content, TextContent)
    return content.text


def test_events_are_directly_callable_without_prior_capabilities_or_lookup(monkeypatch):
    """六事件都能直接调用，不依赖先查能力或按阶段读取规则。"""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)

    async def run():
        """逐事件检查真实线协议输出，确认完整指令与结构判断相互独立。"""
        async with Client(create_workflow_server()) as client:
            inventory = {tool.name for tool in (await client.list_tools()).tools}
            assert len(inventory) == 11
            assert "workflow_check_event" in inventory
            assert "decide_decoupling_workflow" not in inventory
            for event in EVENT_REQUIREMENTS:
                wire = await client.call_tool(
                    "workflow_check_event",
                    {
                        "payload": {
                            "request": request_data(
                                event, mode="single-agent", include_workflow=True
                            )
                        }
                    },
                )
                output = json.loads(_wire_text(wire))
                assert output["event"] == event
                assert output["status"] == "checked"
                assert output["instructions"]["complete"] is True
                assert output["instructions"]["workflow"]["mode"] == "single-agent"
                assert output["structural_check"]["status"] == "ready_for_agent_review"
                assert output["advice"]["status"] == "not_requested"
                assert output["authority"] == "advisory_only"

    asyncio.run(run())


@pytest.mark.parametrize("event", ["completion_requested", "session_resumed"])
def test_wire_missing_evidence_stays_unresolved_and_does_not_recover_prior_state(event):
    """先前成功请求不能替后续缺证据请求恢复服务端状态。"""

    async def run():
        """在同一会话连续调用，直接验证后一次响应仍报告自己的事实和证据缺口。"""
        async with Client(create_workflow_server()) as client:
            await client.call_tool("workflow_check_event", {"payload": {"request": request_data()}})
            wire = await client.call_tool(
                "workflow_check_event", {"payload": {"request": {"event": event}}}
            )
            output = json.loads(_wire_text(wire))
            assert output["structural_check"]["status"] == "incomplete_for_agent_review"
            assert output["structural_check"]["missing_facts"] == EVENT_REQUIREMENTS[event][0]
            assert output["structural_check"]["missing_evidence"] == EVENT_REQUIREMENTS[event][1]
            assert output["advice"]["suggested_outcome"] is None

    asyncio.run(run())


def test_host_enabled_event_advice_still_requires_per_call_outbound_permission(monkeypatch):
    """即使启动配置启用建议，当前请求没有外发许可也不能调用模型。"""
    monkeypatch.setenv("OPENAI_API_KEY", "mock-protocol-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://protocol.example.invalid/v1")
    fake = FakeClient(response("wait"))

    async def run():
        """先拒绝再放行同一假客户端，确认只允许的一次请求产生建议。"""
        server = create_workflow_server(
            event_advice_config=DecisionsRuntimeConfig(enabled=True, outbound_data_permitted=True),
            decisions_client_factory=lambda _key, _url: fake,
        )
        async with Client(server) as client:
            denied = await client.call_tool(
                "workflow_check_event",
                {
                    "payload": {
                        "request": request_data(semantic_input={"outbound_data_permitted": False})
                    }
                },
            )
            assert (
                json.loads(_wire_text(denied))["advice"]["reason"] == "outbound_data_not_permitted"
            )
            assert fake.calls == []
            allowed = await client.call_tool(
                "workflow_check_event",
                {
                    "payload": {
                        "request": request_data(semantic_input={"outbound_data_permitted": True})
                    }
                },
            )
            output = json.loads(_wire_text(allowed))
            assert output["advice"]["status"] == "available"
            assert output["advice"]["suggested_outcome"] == "wait"
            assert output["advice"]["authority"] == "advisory_only"
        assert len(fake.calls) == 1
        assert fake.closed

    asyncio.run(run())

from __future__ import annotations

import asyncio
import json
from dataclasses import replace
from pathlib import Path

import pytest
from mcp import Client
from mcp.server import MCPServer
from token_io_decoupling_core.binding import DenyingBindingProvider
from token_io_decoupling_tools.serena_memory import SerenaMemoryReadService
from token_io_decoupling_transport.registration import ToolDefinition, ToolRegistrar

from token_io_decoupling.server import create_tools_server


def registrar(*names: str) -> ToolRegistrar:
    provider = DenyingBindingProvider()
    return ToolRegistrar(
        MCPServer("test"),
        provider=provider,
        state_provider=provider,
        allowed_tools=frozenset(names),
        require_codex_context=False,
        bound_role_for=lambda _: None,
    )


def definition() -> ToolDefinition:
    def callback(value: str = "default") -> dict:
        return {"value": value}

    return ToolDefinition(
        "check_api_input", callback, "test", parameter_descriptions={"value": "v"}
    )


def test_full_wire_contract_matches_pre_refactor_snapshot() -> None:
    baseline = json.loads(
        Path(__file__).with_name("fixtures").joinpath("tool_contract_before.json").read_text()
    )

    async def run() -> None:
        async with Client(create_tools_server()) as client:
            actual = {
                tool.name: tool.model_dump(mode="json", by_alias=True)
                for tool in (await client.list_tools()).tools
            }
        assert len(actual) == 34
        assert actual == baseline

    asyncio.run(run())


def test_duplicate_unknown_and_manifest_drift_fail_closed() -> None:
    tool = definition()
    registry = registrar(tool.name)
    for definitions in ((tool, tool), (), (replace(tool, name="unknown"),)):
        with pytest.raises(ValueError):
            registry.validate_definitions(definitions)
        assert not registry.server._tool_manager.list_tools()
    with pytest.raises(ValueError):
        registrar("unknown")
    with pytest.raises(ValueError):
        registry.register(replace(tool, name="rules_get_context"))
    registry.register(tool)
    with pytest.raises(ValueError):
        registry.register(tool)
    assert len(registry.server._tool_manager.list_tools()) == 1


def test_parameter_description_mismatch_is_rejected_before_registration() -> None:
    registry = registrar("check_api_input")
    for descriptions in ({}, {"wrong": "wrong"}, {"value": "v", "extra": "extra"}):
        with pytest.raises(ValueError, match="parameter descriptions"):
            registry.validate_definitions(
                (replace(definition(), parameter_descriptions=descriptions),)
            )
    assert not registry.server._tool_manager.list_tools()


def test_flat_callback_exceptions_are_not_payload_redacted() -> None:
    def callback() -> dict:
        raise ValueError("original service failure")

    registry = registrar("check_api_input")
    registry.register(ToolDefinition("check_api_input", callback, "test"))
    tool = registry.server._tool_manager.list_tools()[0]
    with pytest.raises(ValueError, match="original service failure"):
        tool.fn()


def test_server_validation_errors_hide_rejected_arguments() -> None:
    async def run() -> None:
        async with Client(create_tools_server()) as client:
            result = await client.call_tool(
                "serena_memory_tail_read",
                {"memory_path": "test", "tail_lines": "synthetic-sensitive-value"},
            )
        assert result.is_error
        assert result.content[0].text == (
            "Invalid tool arguments; review the published input schema."
        )

    asyncio.run(run())


def test_server_memory_configuration_is_isolated() -> None:
    class Reader(SerenaMemoryReadService):
        def __init__(self, label: str) -> None:
            super().__init__()
            self.label = label
            self.calls = 0

        def tail_read(self, memory_path: str, tail_lines: int) -> dict:
            self.calls += 1
            return {"label": self.label}

    first, second = Reader("first"), Reader("second")
    servers = [create_tools_server(serena_memory_service=reader) for reader in (first, second)]

    async def run() -> None:
        async def call(server: MCPServer) -> str:
            async with Client(server) as client:
                result = await client.call_tool(
                    "serena_memory_tail_read", {"memory_path": "test", "tail_lines": 1}
                )
                assert not result.is_error
                return json.loads(result.content[0].text)["label"]

        assert await asyncio.gather(*(call(server) for server in servers)) == ["first", "second"]

    asyncio.run(run())
    assert first.calls == second.calls == 1


def test_upstream_ai_wrapper_remains_monkeypatchable(monkeypatch) -> None:
    from dev_workflow_standards_tools.services import api_input_review

    seen = []

    def check(request):
        seen.append(request)
        return {"status": "mocked"}

    monkeypatch.setattr(api_input_review, "check_api_input", check)

    async def run() -> None:
        async with Client(create_tools_server()) as client:
            result = await client.call_tool(
                "check_api_input", {"request": {"purpose": "test", "content": "test"}}
            )
            assert not result.is_error
            assert json.loads(result.content[0].text) == {"status": "mocked"}

    asyncio.run(run())
    assert len(seen) == 1

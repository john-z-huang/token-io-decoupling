"""Contract and architecture regressions for the shared registration template."""

from __future__ import annotations

import ast
import asyncio
import hashlib
import json
from pathlib import Path
from typing import Annotated, Any

import pytest
from mcp import Client
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import BaseModel, Field

from token_io_decoupling_core.binding import DenyingBindingProvider
from token_io_decoupling_tools.server import create_tools_server
from token_io_decoupling_transport.identity import bound_role
from token_io_decoupling_transport.server import SafeMCPServer
from token_io_decoupling_transport.tool import ToolDefinition, ToolRegistrar
from token_io_decoupling_workflow.server import create_workflow_server


def _registrar(server: MCPServer[Any], names: set[str]) -> ToolRegistrar:
    provider = DenyingBindingProvider()
    return ToolRegistrar(
        server,
        provider=provider,
        state_provider=provider,
        allowed_tools=frozenset(names),
        require_codex_context=False,
        bound_role_for=bound_role,
        description_for=lambda name: f"Independent operation {name}.",
    )


@pytest.mark.parametrize("service", ["tools", "workflow"])
def test_complete_public_contract_matches_before_refactor(service: str) -> None:
    fixture = json.loads(
        (Path(__file__).parent / "fixtures/tool_registration_contracts.json").read_text()
    )

    async def run() -> None:
        create = create_tools_server if service == "tools" else create_workflow_server
        async with Client(create()) as client:
            tools = (await client.list_tools()).tools
        actual = {
            tool.name: hashlib.sha256(
                json.dumps(
                    tool.model_dump(mode="json", by_alias=True),
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=False,
                ).encode()
            ).hexdigest()
            for tool in tools
        }
        # The fixture predates the implementation; it covers schemas and all metadata.
        assert actual == fixture["contracts"][service]

    asyncio.run(run())


def test_sdk_registration_has_one_entrypoint_in_tool_py() -> None:
    root = Path(__file__).resolve().parents[6] / "mcp"
    registrations = []
    paths = [*(root / "src").rglob("*.py"), *root.glob("packages/*/src/**/*.py")]
    for path in paths:
        for node in ast.walk(ast.parse(path.read_text())):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in {"tool", "add_tool"}
            ):
                registrations.append(path.relative_to(root).as_posix())
    assert registrations == [
        "packages/token_io_decoupling_transport/src/token_io_decoupling_transport/tool.py"
    ]


@pytest.mark.parametrize("names", [[], ["operation", "operation"], ["other"]])
def test_invalid_inventory_is_rejected_before_registering(names: list[str]) -> None:
    server = MCPServer("invalid-inventory")
    registrar = _registrar(server, {"operation"})
    definitions = tuple(ToolDefinition(name, lambda: {}) for name in names)

    with pytest.raises(ValueError, match="manifest"):
        registrar.register_all(definitions)
    assert not server._tool_manager.list_tools()


class _Payload(BaseModel):
    value: Annotated[int, Field(strict=True)]


def test_native_payload_and_no_arg_callbacks_share_registration_and_keep_contracts() -> None:
    calls = []

    def native(value: Annotated[int, Field(strict=True)], label: str = "default") -> dict[str, Any]:
        calls.append((value, label))
        return {"value": value, "label": label}

    server = SafeMCPServer("template-contract")
    _registrar(server, {"native", "payload", "no_args"}).register_all(
        (
            ToolDefinition(
                name="native",
                callback=native,
                structured_output=None,
                parameter_descriptions={"value": "An integer.", "label": "A label."},
            ),
            ToolDefinition(
                name="payload",
                callback=lambda payload, internal="hidden": {"value": payload.value},
                payload_type=_Payload,
            ),
            ToolDefinition(name="no_args", callback=lambda: {"ok": True}, bounded_errors=True),
        )
    )

    async def run() -> None:
        async with Client(server) as client:
            tools = {tool.name: tool for tool in (await client.list_tools()).tools}
            assert tools["native"].output_schema is not None
            assert tools["payload"].output_schema is None
            assert set(tools["payload"].input_schema["properties"]) == {"payload"}
            assert not tools["no_args"].input_schema["properties"]
            native_result = await client.call_tool("native", {"value": 7})
            assert native_result.structured_content == {"value": 7, "label": "default"}
            result = await client.call_tool("payload", {"payload": {"value": 9}})
            assert json.loads(result.content[0].text) == {"value": 9}
            assert json.loads((await client.call_tool("no_args")).content[0].text) == {"ok": True}
        for name, arguments, message in (
            ("native", {"value": "sensitive-input"}, "Invalid tool arguments"),
            ("payload", {"payload": {"value": "sensitive-input"}}, "typed operation contract"),
        ):
            with pytest.raises(ToolError, match=message) as rejected:
                await server.call_tool(name, arguments)
            assert "sensitive-input" not in str(rejected.value)

    asyncio.run(run())
    assert calls == [(7, "default")]

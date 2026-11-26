"""Official MCP v2 stdio transport for the bounded Token I/O API."""

from __future__ import annotations

from importlib import resources
from pathlib import Path
from typing import Any, cast

from mcp.server import MCPServer
from mcp.server.mcpserver import Context
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import CallToolResult, InputRequiredResult
from pydantic import ValidationError
from token_io_decoupling_core.binding import BindingError, BindingProvider, DenyingBindingProvider
from token_io_decoupling_core.codex_context import CodexCallerBoundProvider
from token_io_decoupling_core.rules import RuleLoader
from token_io_decoupling_core.server_tools import (
    TOOLS_SERVER_NAME,
    TOOLS_SERVER_TOOLS,
)
from token_io_decoupling_tools.compliance_preflight import CompliancePreflightService
from token_io_decoupling_tools.output_materialization import (
    OutputMaterializationService,
    OutputMaterializerConfig,
)
from token_io_decoupling_tools.serena_memory import SerenaMemoryReadService
from token_io_decoupling_transport.identity import (
    bound_role as _bound_role,
)
from token_io_decoupling_transport.registration import ToolRegistrar
from token_io_decoupling_transport.tool_metadata import (
    tools_server_description,
    tools_server_instructions,
)

from token_io_decoupling.tool_registry import register_tools


class _ToolsServer(MCPServer[Any]):
    """屏蔽 SDK 校验错误中的原始参数值。"""

    async def call_tool(
        self, name: str, arguments: dict[str, Any], context: Context | None = None
    ) -> CallToolResult | InputRequiredResult:
        try:
            return await super().call_tool(name, arguments, context)
        except ToolError as error:
            if isinstance(error.__cause__, ValidationError):
                raise ToolError(
                    "Invalid tool arguments; review the published input schema."
                ) from None
            raise


def create_tools_server(
    binding_provider: BindingProvider | None = None,
    *,
    require_bound: bool = False,
    require_codex_context: bool = False,
    serena_memory_service: SerenaMemoryReadService | None = None,
    compliance_service: CompliancePreflightService | None = None,
    output_materializer_config: OutputMaterializerConfig | None = None,
) -> MCPServer[Any]:
    local = binding_provider is None
    provider = binding_provider or DenyingBindingProvider()
    registry_resource = resources.files("token_io_decoupling_core").joinpath(
        "_resources", "registry.json"
    )
    rules = (
        RuleLoader()
        if registry_resource.is_file()
        else RuleLoader(repository_root=Path(__file__).resolve().parents[3])
    )
    if serena_memory_service is not None and not isinstance(
        serena_memory_service, SerenaMemoryReadService
    ):
        raise TypeError("serena_memory_service must be a SerenaMemoryReadService")
    if compliance_service is not None and not isinstance(
        compliance_service, CompliancePreflightService
    ):
        raise TypeError("compliance_service must be a CompliancePreflightService")
    bound_role = _bound_role(provider) if binding_provider is not None else None
    if require_bound and bound_role is None:
        raise BindingError("authenticated host channel did not provide a usable bound identity")
    embedded = bound_role is not None
    if require_codex_context and not embedded and not local:
        raise BindingError("Codex caller matching requires a usable bound identity")

    server = _ToolsServer(
        name=TOOLS_SERVER_NAME,
        version="0.1.0",
        description=tools_server_description(),
        instructions=tools_server_instructions(),
    )

    state_provider = CodexCallerBoundProvider(provider) if require_codex_context else provider
    output_materializer = (
        OutputMaterializationService(
            authorization_provider=output_materializer_config.authorization_provider,
            compliance_service=compliance_service,
            config=output_materializer_config,
        )
        if (output_materializer_config is not None and compliance_service is not None)
        else None
    )
    registrar = ToolRegistrar(
        server,
        provider=provider,
        state_provider=state_provider,
        allowed_tools=TOOLS_SERVER_TOOLS,
        require_codex_context=require_codex_context,
        bound_role_for=_bound_role,
    )
    register_tools(
        registrar,
        serena_memory_service=serena_memory_service,
        compliance_service=compliance_service,
        rules=rules,
        provider=provider,
        output_materializer=output_materializer,
    )
    discovered = [tool.name for tool in server._tool_manager.list_tools()]
    actual = set(discovered)
    if len(discovered) != len(actual) or actual != TOOLS_SERVER_TOOLS:
        raise ValueError(
            "MCP server inventory differs from its fixed manifest "
            f"(missing={sorted(TOOLS_SERVER_TOOLS - actual)!r}, "
            f"unexpected={sorted(actual - TOOLS_SERVER_TOOLS)!r})"
        )
    cast(Any, server)._output_materializer = output_materializer
    return server

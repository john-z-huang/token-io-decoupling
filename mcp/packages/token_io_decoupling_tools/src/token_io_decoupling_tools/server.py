"""Standalone tools composition root; no workflow imports or rule resources."""

from typing import Any, cast

from mcp.server import MCPServer

from token_io_decoupling_core.binding import BindingError, BindingProvider, DenyingBindingProvider
from token_io_decoupling_core.codex_context import CodexCallerBoundProvider
from token_io_decoupling_core.server_tools import TOOLS_SERVER_NAME, TOOLS_SERVER_TOOLS
from token_io_decoupling_tools.compliance.service import CompliancePreflightService
from token_io_decoupling_tools.materialization.models import OutputMaterializerConfig
from token_io_decoupling_tools.materialization.service import OutputMaterializationService
from token_io_decoupling_tools.registration.local import register_tools
from token_io_decoupling_tools.serena_memory import SerenaMemoryReadService
from token_io_decoupling_tools.task_plans.service import TaskPlanService
from token_io_decoupling_tools.tool_metadata import (
    SERVER_DESCRIPTION,
    SERVER_INSTRUCTIONS,
    tool_description,
)
from token_io_decoupling_transport.identity import bound_role
from token_io_decoupling_transport.server import SafeMCPServer
from token_io_decoupling_transport.tool import ToolRegistrar


def create_tools_server(
    binding_provider: BindingProvider | None = None,
    *,
    require_bound: bool = False,
    require_codex_context: bool = False,
    task_plan_service: TaskPlanService | None = None,
    serena_memory_service: SerenaMemoryReadService | None = None,
    compliance_service: CompliancePreflightService | None = None,
    output_materializer_config: OutputMaterializerConfig | None = None,
) -> MCPServer[Any]:
    provider = binding_provider or DenyingBindingProvider()
    role = bound_role(provider) if binding_provider is not None else None
    if require_bound and role is None:
        raise BindingError("trusted provider did not supply a usable bound identity")
    if require_codex_context and binding_provider is not None and role is None:
        raise BindingError("Codex caller matching requires a usable bound identity")
    for service, expected in (
        (task_plan_service, TaskPlanService),
        (serena_memory_service, SerenaMemoryReadService),
        (compliance_service, CompliancePreflightService),
    ):
        if service is not None and not isinstance(service, expected):
            raise TypeError("configured service has the wrong type")
    server = SafeMCPServer(
        name=TOOLS_SERVER_NAME,
        version="0.1.0",
        description=SERVER_DESCRIPTION,
        instructions=SERVER_INSTRUCTIONS,
    )
    registrar = ToolRegistrar(
        server,
        provider=provider,
        state_provider=CodexCallerBoundProvider(provider) if require_codex_context else provider,
        allowed_tools=TOOLS_SERVER_TOOLS,
        require_codex_context=require_codex_context,
        bound_role_for=bound_role,
        description_for=tool_description,
    )
    materializer = (
        OutputMaterializationService(
            authorization_provider=output_materializer_config.authorization_provider,
            compliance_service=compliance_service,
            config=output_materializer_config,
        )
        if output_materializer_config is not None and compliance_service is not None
        else None
    )
    details = (
        materializer.capability()
        if materializer is not None
        else {
            "status": "unavailable",
            "reason_code": "output_materializer_or_preflight_not_configured"
            if output_materializer_config is not None
            else "output_materializer_not_configured",
        }
    )
    register_tools(
        registrar,
        provider=provider,
        task_plan_service=task_plan_service or TaskPlanService(),
        serena_memory_service=serena_memory_service or SerenaMemoryReadService(),
        compliance_service=compliance_service,
        output_materializer=materializer,
        output_materialization_details=details,
    )
    discovered = server._tool_manager.list_tools()
    names = [tool.name for tool in discovered]
    if len(names) != len(set(names)) or set(names) != TOOLS_SERVER_TOOLS:
        raise ValueError("standalone tool inventory differs from its manifest")
    cast(Any, server)._output_materializer = materializer
    return server

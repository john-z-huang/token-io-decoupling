"""Official MCP v2 stdio transport for the bounded Token I/O API."""

from __future__ import annotations

from collections.abc import Callable
from importlib import resources
from pathlib import Path
from typing import Any, cast

from mcp.server import MCPServer
from token_io_decoupling_core.binding import BindingError, BindingProvider
from token_io_decoupling_core.codex_context import CodexCallerBoundProvider
from token_io_decoupling_core.rules import RuleLoader
from token_io_decoupling_core.server_tools import (
    TOOLS_SERVER_NAME,
    TOOLS_SERVER_TOOLS,
    WORKFLOW_SERVER_NAME,
    WORKFLOW_TOOLS,
)
from token_io_decoupling_root.tools import register_root_tools
from token_io_decoupling_shared.tools import register_shared_tools
from token_io_decoupling_state.local_context import LocalSessionContext
from token_io_decoupling_state.service import StateService
from token_io_decoupling_state.state.common import DEFAULT_STATE_ROOT
from token_io_decoupling_transport.identity import (
    binding_details as _binding_details,
)
from token_io_decoupling_transport.identity import (
    binding_diagnostic as _binding_diagnostic,
)
from token_io_decoupling_transport.identity import (
    bound_role as _bound_role,
)
from token_io_decoupling_transport.identity import (
    schema_status as _schema_status,
)
from token_io_decoupling_transport.registration import ToolRegistrar
from token_io_decoupling_transport.tool_metadata import (
    tools_server_description,
    tools_server_instructions,
    workflow_server_description,
    workflow_server_instructions,
)
from token_io_decoupling_worker.tools import register_worker_tools
from token_io_decoupling_workflow.compliance_preflight import CompliancePreflightService
from token_io_decoupling_workflow.decisions import DecisionsAdvisor, DecisionsRuntimeConfig
from token_io_decoupling_workflow.output_materialization import (
    OutputMaterializationService,
    OutputMaterializerConfig,
)
from token_io_decoupling_workflow.serena_memory import SerenaMemoryReadService
from token_io_decoupling_workflow.task_plan_core import TaskPlanService
from token_io_decoupling_workflow.tools import register_workflow_tools


def _build_server(
    *,
    name: str,
    allowed_tools: frozenset[str],
    with_development_tools: bool,
    binding_provider: BindingProvider | None = None,
    require_bound: bool = False,
    require_codex_context: bool = False,
    state_root: Path | str | None = None,
    decisions_config: DecisionsRuntimeConfig | None = None,
    decisions_client_factory: Callable[[str, str], object] | None = None,
    task_plan_service: TaskPlanService | None = None,
    serena_memory_service: SerenaMemoryReadService | None = None,
    compliance_service: CompliancePreflightService | None = None,
    output_materializer_config: OutputMaterializerConfig | None = None,
) -> MCPServer[Any]:
    local = binding_provider is None
    provider = binding_provider or LocalSessionContext(
        Path.cwd(), Path(state_root) if state_root else DEFAULT_STATE_ROOT
    )
    registry_resource = resources.files("token_io_decoupling_core").joinpath(
        "_resources", "registry.json"
    )
    rules = (
        RuleLoader()
        if registry_resource.is_file()
        else RuleLoader(repository_root=Path(__file__).resolve().parents[3])
    )
    if task_plan_service is not None and not isinstance(task_plan_service, TaskPlanService):
        raise TypeError("task_plan_service must be a TaskPlanService")
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

    server_type = MCPServer
    development = None
    description = workflow_server_description()
    instructions = workflow_server_instructions()
    if with_development_tools:
        # The pinned upstream revision owns validation-error redaction and tool registrations.
        from dev_workflow_standards_tools import server as development

        server_type = development._SafeMCPServer
        description = tools_server_description() + " " + development.SERVER_DESCRIPTION
        instructions = tools_server_instructions() + " " + development.SERVER_INSTRUCTIONS
    server = server_type(
        name=name,
        version="0.1.0",
        description=description,
        instructions=instructions,
    )

    state_provider = (
        CodexCallerBoundProvider(provider) if require_codex_context and not local else provider
    )
    require_codex_context = require_codex_context or local
    service = StateService(
        binding_provider=state_provider, state_root=state_root, rule_loader=rules
    )
    config = decisions_config or DecisionsRuntimeConfig()
    advisor = DecisionsAdvisor(service, rules, config, client_factory=decisions_client_factory)
    task_plans = task_plan_service if task_plan_service is not None else TaskPlanService()
    output_materializer = (
        OutputMaterializationService(
            state_service=service,
            compliance_service=compliance_service,
            config=output_materializer_config,
        )
        if (
            with_development_tools
            and output_materializer_config is not None
            and compliance_service is not None
        )
        else None
    )
    output_materialization_details = (
        output_materializer.capability()
        if output_materializer is not None
        else {
            "status": "unavailable",
            "reason_code": (
                "output_materializer_or_preflight_not_configured"
                if output_materializer_config is not None and compliance_service is None
                else "output_materializer_not_configured"
            ),
        }
    )
    registrar = ToolRegistrar(
        server,
        provider=provider,
        state_provider=state_provider,
        allowed_tools=allowed_tools,
        require_codex_context=require_codex_context,
        bound_role_for=_bound_role,
    )
    register_workflow_tools(
        registrar,
        service=service,
        task_plan_service=task_plans,
        serena_memory_service=serena_memory_service,
        compliance_service=compliance_service,
        rules=rules,
        advisor=advisor,
        decisions_config=decisions_config,
        provider=provider,
        embedded=embedded,
        require_codex_context=require_codex_context,
        binding_details=_binding_details,
        output_materialization_details=output_materialization_details,
    )
    register_shared_tools(
        registrar,
        service=service,
        provider=provider,
        schema_status=_schema_status,
        binding_diagnostic=_binding_diagnostic,
        bound_role_for=_bound_role,
    )
    if development is not None:
        register_root_tools(registrar, service)
        register_worker_tools(registrar, service, output_materializer)
        for register in (
            development.register_git_tools,
            development.register_repository_tools,
            development.register_github_tools,
            development.register_codex_session_fact_tools,
            development.register_ai_workflow_tools,
        ):
            register(server)
    discovered = [tool.name for tool in server._tool_manager.list_tools()]
    actual = set(discovered)
    if len(discovered) != len(actual) or actual != allowed_tools:
        raise ValueError(
            "MCP server inventory differs from its fixed manifest "
            f"(missing={sorted(allowed_tools - actual)!r}, "
            f"unexpected={sorted(actual - allowed_tools)!r})"
        )
    cast(Any, server)._output_materializer = output_materializer
    return server


def create_workflow_server(
    binding_provider: BindingProvider | None = None,
    *,
    require_bound: bool = False,
    require_codex_context: bool = False,
    state_root: Path | str | None = None,
    decisions_config: DecisionsRuntimeConfig | None = None,
    decisions_client_factory: Callable[[str, str], object] | None = None,
    task_plan_service: TaskPlanService | None = None,
    serena_memory_service: SerenaMemoryReadService | None = None,
    compliance_service: CompliancePreflightService | None = None,
) -> MCPServer[Any]:
    """Create the fixed local workflow stdio server."""
    return _build_server(
        name=WORKFLOW_SERVER_NAME,
        allowed_tools=WORKFLOW_TOOLS,
        with_development_tools=False,
        binding_provider=binding_provider,
        require_bound=require_bound,
        require_codex_context=require_codex_context,
        state_root=state_root,
        decisions_config=decisions_config,
        decisions_client_factory=decisions_client_factory,
        task_plan_service=task_plan_service,
        serena_memory_service=serena_memory_service,
        compliance_service=compliance_service,
    )


def create_tools_server(
    binding_provider: BindingProvider | None = None,
    *,
    require_bound: bool = False,
    require_codex_context: bool = False,
    state_root: Path | str | None = None,
    compliance_service: CompliancePreflightService | None = None,
    output_materializer_config: OutputMaterializerConfig | None = None,
) -> MCPServer[Any]:
    """Create the fixed local aggregate tools stdio server."""
    return _build_server(
        name=TOOLS_SERVER_NAME,
        allowed_tools=TOOLS_SERVER_TOOLS,
        with_development_tools=True,
        binding_provider=binding_provider,
        require_bound=require_bound,
        require_codex_context=require_codex_context,
        state_root=state_root,
        compliance_service=compliance_service,
        output_materializer_config=output_materializer_config,
    )

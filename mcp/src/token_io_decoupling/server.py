"""Official MCP v2 stdio transport for the bounded Token I/O API."""

from __future__ import annotations

from collections.abc import Callable
from importlib import resources
from pathlib import Path
from typing import Any, cast

from mcp.server import MCPServer
from token_io_decoupling_core.binding import BindingError, BindingProvider, DenyingBindingProvider
from token_io_decoupling_core.codex_context import CodexCallerBoundProvider
from token_io_decoupling_core.profiles import PROFILE_ROLES as PROFILE_ROLES
from token_io_decoupling_core.profiles import PROFILE_TOOLS as PROFILE_TOOLS
from token_io_decoupling_core.rules import RuleLoader
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
from token_io_decoupling_transport.tool_metadata import server_description, server_instructions
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


def create_server(
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
    output_materializer_config: OutputMaterializerConfig | None = None,
    profile: str | None = None,
    server_name: str | None = None,
) -> MCPServer[Any]:
    """Create named local stdio profiles, or an explicit embedding/test context."""
    local = binding_provider is None and profile is not None
    provider = binding_provider or (
        LocalSessionContext(Path.cwd(), Path(state_root) if state_root else DEFAULT_STATE_ROOT)
        if local
        else DenyingBindingProvider()
    )
    registry_resource = resources.files("token_io_decoupling_core").joinpath(
        "_resources", "registry.json"
    )
    rules = (
        RuleLoader()
        if registry_resource.is_file()
        else RuleLoader(repository_root=Path(__file__).resolve().parents[3])
    )
    if profile is not None and profile not in PROFILE_TOOLS:
        raise ValueError(f"unknown server profile: {profile}")
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
    server = MCPServer(
        name=server_name or "token-io-decoupling",
        version="0.1.0",
        description=server_description(profile, bound_role),
        instructions=server_instructions(profile, bound_role),
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
    worker_materialization_enabled = profile == "worker" or (
        profile is None and bound_role == "worker"
    )
    output_materializer = (
        OutputMaterializationService(
            state_service=service,
            compliance_service=compliance_service,
            config=output_materializer_config,
        )
        if (
            worker_materialization_enabled
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
        profile=profile,
        bound_role=bound_role,
        embedded=embedded,
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
        profile=profile,
        schema_status=_schema_status,
        binding_diagnostic=_binding_diagnostic,
        bound_role_for=_bound_role,
    )
    if not embedded and profile is None:
        return server
    register_root_tools(registrar, service)
    register_worker_tools(registrar, service, output_materializer)
    cast(Any, server)._output_materializer = output_materializer
    return server

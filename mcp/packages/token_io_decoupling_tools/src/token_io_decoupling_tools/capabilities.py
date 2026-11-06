"""Optional, service-local dependency diagnostics without workflow state."""

from typing import Any

from token_io_decoupling_core.binding import BindingProvider
from token_io_decoupling_core.server_tools import TOOLS_SERVER_TOOLS
from token_io_decoupling_tools.compliance_preflight import CompliancePreflightService
from token_io_decoupling_tools.serena_memory import SerenaMemoryReadService
from token_io_decoupling_tools.task_plan_core import TaskPlanService
from token_io_decoupling_transport.identity import binding_details


def capability_report(
    provider: BindingProvider,
    *,
    task_plan_service: TaskPlanService,
    serena_memory_service: SerenaMemoryReadService,
    compliance_service: CompliancePreflightService | None,
    output_materialization: dict[str, str],
) -> dict[str, Any]:
    plans = task_plan_service.capability()
    memory = serena_memory_service.capability()
    compliance = (
        compliance_service.capability()
        if compliance_service is not None
        else {
            "status": "unavailable",
            "reason_code": "compliance_backend_not_configured",
            "policy_scopes": [],
        }
    )
    return {
        "subsystem": "token-io-tools",
        "agent_runtime": "codex_cli",
        "supported_transports": ["stdio"],
        "tool_count": len(TOOLS_SERVER_TOOLS),
        "workflow_required": False,
        "task_plan_tools": plans["status"],
        "serena_memory_reads": memory["status"],
        "serena_memory_binding": memory,
        "decoupling_compliance": compliance["status"],
        "compliance_policy_scopes": compliance.get("policy_scopes", []),
        "output_materialization": output_materialization["status"],
        "binding": binding_details(provider),
        "capability_details": {
            "schema_version": 3,
            "configuration": {
                "task_plan_tools": plans,
                "serena_memory_reads": memory,
                "decoupling_compliance": compliance,
                "output_materialization": output_materialization,
            },
        },
    }

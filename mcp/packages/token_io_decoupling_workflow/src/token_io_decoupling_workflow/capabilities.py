"""Workflow-local diagnostics; never import or probe tools services."""

from collections.abc import Callable
from typing import Any

from token_io_decoupling_core.binding import BindingProvider
from token_io_decoupling_core.server_tools import WORKFLOW_TOOLS


def capability_report(
    provider: BindingProvider,
    *,
    embedded: bool,
    require_codex_context: bool,
    api_decisions_enabled: bool,
    diagnose_binding: Callable[[BindingProvider], dict[str, str]],
) -> dict[str, Any]:
    binding = diagnose_binding(provider)
    detail = {
        "status": "available",
        "reason_code": "fixed_codex_cli",
        "message": "Local Codex CLI rule navigation and supplied-fact structural checks.",
        "source": "static_support.agent_runtime",
        "next_step": "Use complete returned instructions when choosing this workflow.",
    }
    return {
        "subsystem": "token-io-mcp",
        "agent_runtime": "codex_cli",
        "supported_transports": ["stdio"],
        "tool_count": len(WORKFLOW_TOOLS),
        "trusted_binding": ("available" if binding["status"] == "available" else "unavailable")
        if embedded
        else "unverified",
        "binding_transport": "embedded_provider" if embedded else "unavailable",
        "caller_match": "required" if require_codex_context else "disabled",
        "api_decisions": "enabled" if api_decisions_enabled else "disabled",
        "workflow_routing": "available_per_invocation",
        "child_effort_decisions": "available_per_invocation",
        "delegation_decisions": "available_per_invocation",
        "decision_context_generation": "available_per_invocation",
        "instruction_delivery": {
            "schema_version": 2,
            "format": "compiled_json",
            "source_fallback": False,
            "resource_status": "checked_per_instruction_call",
            "start": {
                "tool": "rules_get_context",
                "payload": {"node_id": "contract", "context_version": 2},
            },
            "interpretation": "Compiled instructions are not authority or completion evidence.",
        },
        "protocol_target": "2026-07-28",
        "capability_details": {
            "schema_version": 3,
            "support": {
                "agent_runtime": detail,
                "identity_bound_operations": {
                    **detail,
                    "status": "unavailable",
                    "reason_code": "workflow_has_no_identity_bound_operations",
                    "message": "This server exposes only stateless workflow operations.",
                    "next_step": "Use each independent operation's current authorization contract.",
                },
            },
            "configuration": {
                "public_interfaces": {
                    **detail,
                    "status": "unverified",
                    "reason_code": "tool_dependencies_not_probed",
                    "message": "Structural checks do not authenticate facts or authorize effects.",
                    "next_step": "Check each operation's inputs and optional API configuration.",
                },
                "caller_match": {
                    **detail,
                    "status": "required" if require_codex_context else "disabled",
                    "reason_code": "configured_required"
                    if require_codex_context
                    else "configured_disabled",
                },
                "api_decisions": {
                    **detail,
                    "status": "enabled" if api_decisions_enabled else "disabled",
                    "reason_code": "configured_enabled"
                    if api_decisions_enabled
                    else "configured_disabled",
                    "message": "Optional API advice is separate; no API readiness probe.",
                },
            },
            "runtime": {
                "binding": binding,
                "binding_transport": {
                    **detail,
                    "status": "unverified" if embedded else "unavailable",
                    "reason_code": "transport_not_reported"
                    if embedded
                    else "provider_not_configured",
                },
                "server_mode": {
                    **detail,
                    "status": "embedded" if embedded else "public_only",
                    "reason_code": "startup_binding_verified"
                    if embedded
                    else "startup_binding_unverified",
                    "message": "No caller identity or workflow state store is established here."
                    if not embedded
                    else "Injected scope is not independent host authentication.",
                },
            },
        },
    }

"""Public capability reports: static support, configuration, and current binding evidence."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from token_io_decoupling_core.binding import BindingProvider, DenyingBindingProvider
from token_io_decoupling_core.host_binding import HostChannelBindingProvider

from token_io_decoupling_workflow.task_plan_core import TaskPlanService


def _detail(status: str, code: str, message: str, source: str, next_step: str) -> dict[str, str]:
    return {
        "status": status,
        "reason_code": code,
        "message": message,
        "source": source,
        "next_step": next_step,
    }


def capability_report(
    provider: BindingProvider,
    *,
    embedded: bool,
    require_codex_context: bool,
    api_decisions_enabled: bool,
    diagnose_binding: Callable[[BindingProvider], dict[str, str]],
    task_plan_service: TaskPlanService | None = None,
) -> dict[str, Any]:
    """Read binding evidence once without mutating state, inspecting paths, or calling an API."""
    binding = diagnose_binding(provider)
    adapters = {
        name: {"identity_attestation": "unavailable", "guard_binding": "unavailable"}
        for name in ("Codex Desktop", "ChatGPT Desktop")
    }
    adapter_details = {
        name: {
            capability: _detail(
                status,
                "adapter_not_implemented",
                "This built-in Desktop capability is not implemented; no provider was probed here.",
                "static_support.built_in_desktop_adapters",
                "Use Native or supply a trusted host provider; see runtime.binding.",
            )
            for capability, status in capabilities.items()
        }
        for name, capabilities in adapters.items()
    }
    caller_match = "required" if require_codex_context else "disabled"
    api_decisions = "enabled" if api_decisions_enabled else "disabled"
    task_plan_details = (
        task_plan_service.capability()
        if task_plan_service is not None
        else {
            "status": "unavailable",
            "reason_code": "task_plan_backend_not_configured",
            "project_root": None,
            "namespace": None,
        }
    )
    # Never serialize provider attributes: even transport labels can contain secrets or raise.
    transport = (
        "authenticated_inherited_unix_socket"
        if isinstance(provider, HostChannelBindingProvider)
        else "embedded_provider"
    )
    if type(provider) is DenyingBindingProvider:
        transport_detail = _detail(
            "unavailable",
            "provider_not_configured",
            "No host binding transport is configured.",
            "server.default_provider",
            "Use Native or configure a trusted host integration.",
        )
    elif isinstance(provider, HostChannelBindingProvider):
        transport_detail = _detail(
            "available",
            "known_transport",
            "The provider uses an authenticated inherited Unix socket.",
            "provider_type",
            "Check runtime.binding for current validation; transport type is not authority.",
        )
    else:
        transport_detail = _detail(
            "unverified",
            "transport_not_reported",
            "A custom provider's transport has not been independently classified.",
            "provider_type",
            "Consult the trusted host integration; do not infer transport from a label.",
        )
    return {
        "subsystem": "token-io-mcp",
        "supported_transports": ["stdio"],
        "host_adapters": adapters,
        "enhanced_binding": (
            "unverified"
            if not embedded
            else "available"
            if binding["status"] == "available"
            else "unavailable"
        ),
        "binding_transport": transport if embedded else "unavailable",
        "caller_match": caller_match,
        "mode_fallback": "Native",
        "api_decisions": api_decisions,
        "child_effort_decisions": "available_per_invocation",
        "delegation_decisions": "available_per_invocation",
        "decision_context_generation": "available_per_invocation",
        "task_plan_tools": task_plan_details.get("status", "unavailable"),
        "protocol_target": "2026-07-28",
        "capability_details": {
            "schema_version": 1,
            "support": {"host_adapters": adapter_details},
            "configuration": {
                "task_plan_tools": _detail(
                    task_plan_details.get("status", "unavailable"),
                    task_plan_details.get("reason_code", "task_plan_backend_unavailable"),
                    "Plan tools use only an explicitly injected Serena "
                    "MemoryManager-backed service; no path or config is "
                    "probed here.",
                    "server.task_plan_service",
                    "Use an explicitly configured trusted task-plan "
                    "factory or keep plan tools unavailable.",
                ),
                "caller_match": _detail(
                    caller_match,
                    "configured_required" if require_codex_context else "configured_disabled",
                    "Caller matching is configured at server startup; disabled is not an error.",
                    "server.require_codex_context",
                    "Check caller metadata per protected request; this call does not verify it.",
                ),
                "api_decisions": _detail(
                    api_decisions,
                    "configured_enabled" if api_decisions_enabled else "configured_disabled",
                    "Persisted API advice is configured separately from per-invocation tools.",
                    "server.decisions_config.enabled",
                    "No API probe; per-call tools require permission and configuration.",
                ),
            },
            "runtime": {
                "binding": binding,
                "binding_transport": transport_detail,
                "server_mode": _detail(
                    "embedded" if embedded else "public_only",
                    "startup_binding_accepted" if embedded else "startup_binding_unverified",
                    "Startup fixes registration scope; current diagnostics never expand it.",
                    "server.create_server",
                    "Protected calls still check identity, caller context, and required guards.",
                ),
            },
        },
    }

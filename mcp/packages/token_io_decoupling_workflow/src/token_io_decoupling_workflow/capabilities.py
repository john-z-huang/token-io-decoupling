"""Public capability reports: static support, configuration, and current binding evidence."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from token_io_decoupling_core.binding import BindingProvider, DenyingBindingProvider
from token_io_decoupling_core.host_binding import HostChannelBindingProvider


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
) -> dict[str, Any]:
    """Read binding evidence once without mutating state, inspecting paths, or calling an API."""
    binding = diagnose_binding(provider)
    caller_match = "required" if require_codex_context else "disabled"
    api_decisions = "enabled" if api_decisions_enabled else "disabled"
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
        "agent_runtime": "codex_cli",
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
        "protocol_target": "2026-07-28",
        "capability_details": {
            "schema_version": 2,
            "support": {
                "agent_runtime": _detail(
                    "available",
                    "fixed_codex_cli",
                    "This MCP server targets Codex CLI, including its app-server use from Desktop "
                    "and local Work.",
                    "static_support.agent_runtime",
                    "Use Codex CLI; verify host identity, caller context, and guards separately.",
                )
            },
            "configuration": {
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

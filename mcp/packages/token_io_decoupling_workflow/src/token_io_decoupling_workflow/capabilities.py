"""Public capability reports: static support, configuration, and current binding evidence."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from token_io_decoupling_core.binding import BindingProvider, DenyingBindingProvider
from token_io_decoupling_state.local_context import LocalSessionContext

from token_io_decoupling_workflow.compliance_preflight import CompliancePreflightService
from token_io_decoupling_workflow.serena_memory import SerenaMemoryReadService
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
    compliance_service: CompliancePreflightService | None = None,
    output_materialization: dict[str, str] | None = None,
    serena_memory_service: SerenaMemoryReadService | None = None,
) -> dict[str, Any]:
    """Read binding evidence and task-plan diagnostics without state mutation or API calls.

    An absent task-plan service causes no Git or Memory-path probe. A configured global plan
    service may perform a bounded local Git identity check and verify its already-bound Serena
    root; it never creates or initializes Memory paths here.
    """
    binding = diagnose_binding(provider)
    memory_read_details = (serena_memory_service or SerenaMemoryReadService()).capability()
    caller_match = "required" if require_codex_context else "disabled"
    api_decisions = "enabled" if api_decisions_enabled else "disabled"
    task_plan_details = (
        task_plan_service.capability()
        if task_plan_service is not None
        else {
            "status": "unavailable",
            "reason_code": "task_plan_backend_not_configured",
            "project_root": None,
            "storage_scope": None,
            "repository_id": None,
            "namespace": None,
            "archive_namespace": None,
        }
    )
    compliance_details = (
        compliance_service.capability()
        if compliance_service is not None
        else {
            "status": "unavailable",
            "reason_code": "compliance_backend_not_configured",
            "policy_scopes": [],
        }
    )
    output_details = output_materialization or {
        "status": "unavailable",
        "reason_code": "output_materializer_not_configured",
    }
    # Never serialize provider attributes: even transport labels can contain secrets or raise.
    local = isinstance(provider, LocalSessionContext)
    transport = "stdio" if local else "embedded_provider"
    transport_detail = _detail(
        "available" if local else "unverified",
        "local_stdio" if local else "transport_not_reported",
        "Local Codex stdio uses application request scoping, not privileged host authentication."
        if local
        else "Injected context is not independently authenticated by this diagnostic.",
        "server.local_stdio" if local else "provider_type",
        "Supply Codex request metadata for state calls; configuration and authorization "
        "remain separate."
        if local
        else "Check the configured context; a transport label is not authority.",
    )
    if type(provider) is DenyingBindingProvider:
        transport_detail = _detail(
            "unavailable",
            "provider_not_configured",
            "No local request context is configured.",
            "server.default_provider",
            "Start the workflow or tools executable from the intended project root.",
        )
    return {
        "subsystem": "token-io-mcp",
        "supported_transports": ["stdio"],
        "agent_runtime": "codex_cli",
        "enhanced_binding": (
            "not_applicable"
            if local
            else "unverified"
            if not embedded
            else "available"
            if binding["status"] == "available"
            else "unavailable"
        ),
        "binding_transport": transport if local or embedded else "unavailable",
        "caller_match": caller_match,
        "mode_fallback": "Native",
        "api_decisions": api_decisions,
        "workflow_routing": "available_per_invocation",
        "child_effort_decisions": "available_per_invocation",
        "delegation_decisions": "available_per_invocation",
        "decision_context_generation": "available_per_invocation",
        "task_plan_tools": task_plan_details.get("status", "unavailable"),
        "serena_memory_reads": memory_read_details.get("status", "unavailable"),
        "serena_memory_binding": memory_read_details,
        "decoupling_compliance": compliance_details.get("status", "unavailable"),
        "compliance_policy_scopes": compliance_details.get("policy_scopes", []),
        "output_materialization": output_details.get("status", "unavailable"),
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
                ),
                "local_stdio": _detail(
                    "available",
                    "local_stdio_request_scoping",
                    "The workflow and aggregate tools executables use local Codex stdio without a "
                    "privileged host, "
                    "inherited host descriptor or external identity provider. Metadata and "
                    "recorded allocations scope state; they do not authenticate other "
                    "same-user processes.",
                    "static_support.local_stdio",
                    "Start Codex from the intended project root. State calls require "
                    "threadId/sessionId request metadata and operation-specific authorization.",
                ),
            },
            "configuration": {
                "public_interfaces": _detail(
                    "unverified",
                    "tool_dependencies_not_probed",
                    "Public means no Enhanced binding requirement, not configured or authorized. "
                    "Capability/rule/schema diagnostics, local Memory reads, Native task plans, "
                    "candidate compliance, workflow routing and stateless selection/context "
                    "tools are public. Schema diagnostics do not inspect unbound state paths. "
                    "Workflow/Control evaluation and Root/Worker/state operations require local "
                    "request scope, recorded roles, permissions and current operation checks.",
                    "workflow.public_tool_contracts",
                    "Check each tool: Memory requires existing startup-project files; plans "
                    "require an injected backend; compliance requires an operator-configured "
                    "reader/root/policy. API-backed selection/context and automatic routing "
                    "require nonblank OPENAI_API_KEY and OPENAI_BASE_URL and per-call outbound "
                    "authorization; explicit-stage routing is local. Materialization additionally "
                    "requires a registered Worker, configured service and independent "
                    "operator grant. "
                    "No API or execution-readiness probe was made.",
                ),
                "serena_memory_reads": _detail(
                    str(memory_read_details.get("status", "unavailable")),
                    str(memory_read_details.get("reason_code", "serena_memory_unavailable")),
                    "Read-only tail and literal write-check tools read files only under "
                    "<workflow server startup cwd>/.serena/memories. They use Python standard "
                    "library file operations and do not require Serena-Agent or another local "
                    "program. Missing directories/files are unavailable; no model/API request.",
                    "server.serena_memory_service",
                    "Start the workflow server with the intended project as its runtime working "
                    "directory. It captures that cwd at startup and reads only "
                    "its .serena/memories "
                    "directory; tool arguments do not select project paths. Inspect the "
                    "returned binding and limits before reading.",
                ),
                "task_plan_tools": _detail(
                    task_plan_details.get("status", "unavailable"),
                    task_plan_details.get("reason_code", "task_plan_backend_unavailable"),
                    "Plan tools use only an explicitly injected Serena "
                    "MemoryManager-backed service. Without a configured service, "
                    "no Git or Memory path is probed. A configured global store "
                    "revalidates its local Git identity and existing global root "
                    "without creating paths.",
                    "server.task_plan_service",
                    "Use an explicitly configured trusted task-plan "
                    "factory or keep plan tools unavailable.",
                ),
                "decoupling_compliance": _detail(
                    compliance_details.get("status", "unavailable"),
                    compliance_details.get("reason_code", "compliance_backend_unavailable"),
                    "Compliance preflight is read-only and uses only an explicitly injected "
                    "operator-configured root and policy-scope allowlist. Without a configured "
                    "reader, it does not probe paths and reports disk evidence as unknown.",
                    "server.compliance_service",
                    "Configure a trusted compliance factory at startup; inspect unknown checks. "
                    "This tool does not run candidate or target-repository scripts.",
                ),
                "output_materialization": _detail(
                    output_details.get("status", "unavailable"),
                    output_details.get("reason_code", "output_materializer_not_configured"),
                    "Worker output materialization requires an explicit trusted factory, the same "
                    "pinned read-only preflight root, and a fresh operator grant per action. "
                    "A Native coding-task role or an Agent Session's Primary Output label is not "
                    "a verified MCP Worker binding. Capability reporting does not probe paths "
                    "or assert current Worker authority.",
                    "server.output_materializer_config",
                    "Use the Worker-only tool only for a confirmed Primary Output assignment "
                    "with code_configuration or skill_instructions output and a matching "
                    "operator grant, pinned roots, and fresh passing preflight; inspect any "
                    "unavailable result.",
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
                "workflow_routing": _detail(
                    "available",
                    "stateless_local_or_decisions_advice",
                    "Explicit stages use local rule context; auto stage selection may use one "
                    "bounded Decisions choice. The tool never verifies readiness or grants "
                    "authority.",
                    "workflow.decide_decoupling_workflow",
                    "Inspect the returned route, module, facts, and rule hashes; follow the "
                    "current route owners and capability gates.",
                ),
            },
            "runtime": {
                "binding": binding,
                "binding_transport": transport_detail,
                "server_mode": _detail(
                    "local_stdio" if local else "embedded" if embedded else "public_only",
                    "local_request_scoping"
                    if local
                    else "startup_binding_accepted"
                    if embedded
                    else "startup_binding_unverified",
                    "The fixed workflow and tools executables select their own inventories; "
                    "each state call resolves its current local scope.",
                    "server.create_workflow_server/create_tools_server",
                    "Use the current request role, path scope and explicit operation "
                    "authorization.",
                ),
            },
        },
    }

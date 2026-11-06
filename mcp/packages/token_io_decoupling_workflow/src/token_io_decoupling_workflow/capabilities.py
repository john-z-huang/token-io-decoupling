"""Workflow-local diagnostics; never import or probe tools services."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from token_io_decoupling_core.binding import BindingProvider
from token_io_decoupling_core.server_tools import WORKFLOW_TOOLS


@dataclass(frozen=True)
class AdviceAvailability:
    """仅报告两种建议入口的启动开关，不代表凭据或调用就绪。"""

    checkpoint: bool
    event: bool


def _enabled_status(enabled: bool) -> str:
    """摘要和明细共用同一公开状态词，避免配置诊断表达漂移。"""
    return "enabled" if enabled else "disabled"


def capability_report(
    provider: BindingProvider,
    *,
    embedded: bool,
    require_codex_context: bool,
    advice: AdviceAvailability,
    diagnose_binding: Callable[[BindingProvider], dict[str, str]],
) -> dict[str, Any]:
    """汇总静态支持与启动配置，不探测 tools 后端、模型就绪状态或任务完成情况。"""
    binding = diagnose_binding(provider)
    detail = {
        "status": "available",
        "reason_code": "fixed_codex_cli",
        "message": "为本地 Codex CLI 提供规则查询及调用方事实的结构检查。",
        "source": "static_support.agent_runtime",
        "next_step": "采用本 workflow 时，完整读取并使用返回的指令。",
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
        "api_decisions": _enabled_status(advice.checkpoint),
        "event_checks": "available_per_invocation",
        "event_advice": _enabled_status(advice.event),
        "workflow_state_store": "not_provided",
        "child_effort_decisions": "available_per_invocation",
        "delegation_decisions": "available_per_invocation",
        "decision_context_generation": "available_per_invocation",
        "instruction_delivery": {
            "schema_version": 3,
            "format": "compiled_json",
            "source_fallback": False,
            "resource_status": "checked_per_instruction_call",
            "start": {
                "tool": "workflow_check_event",
                "payload": {"request": {"event": "task_received"}},
            },
            "interpretation": "编译指令不构成授权或完成证据。",
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
                    "message": "本服务仅提供无状态 workflow 操作。",
                    "next_step": "独立操作须遵循其当前授权契约。",
                },
            },
            "configuration": {
                "public_interfaces": {
                    **detail,
                    "status": "unverified",
                    "reason_code": "tool_dependencies_not_probed",
                    "message": "结构检查不认证事实，也不授权副作用。",
                    "next_step": "核对当次操作的输入及可选 API 配置。",
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
                    "status": _enabled_status(advice.checkpoint),
                    "reason_code": "configured_enabled"
                    if advice.checkpoint
                    else "configured_disabled",
                    "message": "可选 API 建议独立提供；此诊断不探测 API 就绪状态。",
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
                    "message": "此处不建立调用方身份或 workflow 状态存储。"
                    if not embedded
                    else "Injected scope is not independent host authentication.",
                },
            },
        },
    }

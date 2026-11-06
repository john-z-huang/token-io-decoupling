"""将受支持的 Codex 原生事件适配为无状态文档检查。"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field, JsonValue, StrictBool, StrictInt, model_validator

from token_io_decoupling_core.models import Language, StrictModel
from token_io_decoupling_workflow.events.contracts import (
    DEFAULT_EVENT_TEXT_BUDGET,
    MAX_CONTEXT_TEXT_BUDGET,
    MIN_CONTEXT_TEXT_BUDGET,
    EventId,
    WorkflowMode,
)
from token_io_decoupling_workflow.events.models import (
    EventCheckRequest,
    EventCheckResult,
    EventEvidenceReference,
    EventFact,
    EventSemanticInput,
    canonical_event_json,
)

NATIVE_EVENT_MAP: dict[str, EventId] = {
    "UserPromptSubmit": "task_received",
    "PreToolUse": "boundary_requested",
    "PostToolUse": "action_observed",
    "SubagentStop": "progress_reported",
    "Stop": "completion_requested",
    "SessionStart": "session_resumed",
}
MAX_HOOK_OUTPUT_BYTES = 128 * 1024


class NativeHookOptions(StrictModel):
    """当次适配配置；不接受凭据、端点、持久状态或伪造的执行预算。"""

    mode: WorkflowMode | None = None
    language: Language = "zh_cn"
    max_chars: Annotated[
        StrictInt, Field(ge=MIN_CONTEXT_TEXT_BUDGET, le=MAX_CONTEXT_TEXT_BUDGET)
    ] = DEFAULT_EVENT_TEXT_BUDGET
    semantic: StrictBool = False
    outbound_data_permitted: StrictBool = False
    block_once: StrictBool = False

    @model_validator(mode="after")
    def explicit_outbound_permission(self) -> NativeHookOptions:
        """语义请求与一次纠正都须显式选择，不能由默认配置隐式外发。"""
        if self.semantic and not self.outbound_data_permitted:
            raise ValueError("--semantic requires --outbound-data-permitted")
        if self.block_once and not (self.semantic and self.outbound_data_permitted):
            raise ValueError("--block-once requires --semantic and --outbound-data-permitted")
        return self


def _native_event(payload: dict[str, JsonValue]) -> str:
    """只接受已映射的原生事件名，未知时点不能套用其他事件的输出协议。"""
    name = payload.get("hook_event_name")
    if not isinstance(name, str) or name not in NATIVE_EVENT_MAP:
        raise ValueError("unsupported native hook event")
    return name


def _native_metadata(payload: dict[str, JsonValue]) -> dict[str, JsonValue]:
    """仅保留白名单中的简单观察值，不把权限模式或会话标识认证为授权。"""
    return {
        key: payload[key]
        for key in (
            "session_id",
            "turn_id",
            "source",
            "permission_mode",
            "model",
            "agent_id",
            "agent_type",
            "stop_hook_active",
            "tool_name",
        )
        if key in payload and isinstance(payload[key], (str, bool))
    }


def _tool_observations(
    payload: dict[str, JsonValue], native_event: str
) -> tuple[dict[str, JsonValue], list[str]]:
    """区分拟议工具动作与实际返回，只为原生输入已提供的结果标记引用。"""
    action: JsonValue = {
        "tool_name": payload.get("tool_name"),
        "tool_input": payload.get("tool_input"),
    }
    if native_event == "PreToolUse":
        # permission_mode 只是观察值，不能伪装成授权范围证据。
        return {"proposed_action": action, "session_context": _native_metadata(payload)}, []
    values: dict[str, JsonValue] = {"action": action, "result": payload.get("tool_response")}
    evidence = ["operation_result"] if "tool_response" in payload else []
    return values, evidence


def _native_observations(
    payload: dict[str, JsonValue], native_event: str
) -> tuple[dict[str, JsonValue], list[str]]:
    """按事件提取可直接观察的事实；会话开始不从 ID 重建任务历史。"""
    if native_event == "UserPromptSubmit":
        return {"task": payload.get("prompt"), "session_context": _native_metadata(payload)}, [
            "request_source"
        ]
    if native_event in {"PreToolUse", "PostToolUse"}:
        return _tool_observations(payload, native_event)
    if native_event == "Stop":
        return {"results": payload.get("last_assistant_message")}, []
    if native_event == "SubagentStop":
        evidence = ["progress_signal"] if "last_assistant_message" in payload else []
        return {"progress": payload.get("last_assistant_message")}, evidence
    # 原生 SessionStart 不包含任务历史，不能从 Session ID 重建已通过记录。
    return {}, ["context_source"]


def _observed_facts(values: dict[str, JsonValue], reference: str) -> dict[str, EventFact]:
    """保留非空观察及其原生来源，不补造输入未提供的任务事实。"""
    facts: dict[str, EventFact] = {}
    for name, value in values.items():
        if value is None or value == "" or value == {}:
            continue
        text = value if isinstance(value, str) else canonical_event_json(value)
        if text.strip():
            facts[name] = EventFact(value=text, source=reference)
    return facts


def normalize_native_event(
    payload: dict[str, JsonValue], options: NativeHookOptions | None = None
) -> EventCheckRequest:
    """仅映射可直接观察的字段；不读取 transcript、任意文件或历史。"""
    options = options if options is not None else NativeHookOptions()
    native_event = _native_event(payload)
    values, evidence = _native_observations(payload, native_event)
    reference = f"native:{native_event}"
    return EventCheckRequest(
        event=NATIVE_EVENT_MAP[native_event],
        mode=options.mode,
        language=options.language,
        context_summary=canonical_event_json(_native_metadata(payload)),
        facts=_observed_facts(values, reference),
        evidence_refs=[EventEvidenceReference(kind=kind, reference=reference) for kind in evidence],
        max_chars=options.max_chars,
        semantic_input=(
            EventSemanticInput(outbound_data_permitted=options.outbound_data_permitted)
            if options.semantic
            else None
        ),
    )


def _notice(result: EventCheckResult) -> str:
    """报告当次状态和结构缺口，同时说明结果不授权、不验收也不提供模型理由。"""
    missing = result.structural_check.missing_facts + result.structural_check.missing_evidence
    return (
        f"workflow {result.event}: {result.status}; "
        f"structure={result.structural_check.status}; advice={result.advice.status}; "
        f"outcome={result.advice.suggested_outcome or 'none'}; "
        f"missing={','.join(missing) or 'none'}. "
        "此结果不授予权限或完成验收。Agent 自行保存并复核上下文。"
        "可用模型选项不包含针对本例的语义理由。"
    )


def _feedback(result: EventCheckResult) -> str:
    """组合结构诊断与同源文档反馈；完整性不足时不拼接可执行的半份正文。"""
    parts = [_notice(result)]
    if result.advice.feedback is not None:
        parts.append("文档中的结果反馈（不是模型推理）：" + result.advice.feedback)
    if result.instructions is not None and result.instructions.complete:
        parts.append(result.instructions.event.text)
        if result.instructions.workflow is not None:
            parts.append(result.instructions.workflow.text)
    else:
        parts.append("必需的完整指令不可用；请指出依赖该指令的缺口。")
    return "\n\n".join(parts)


def _should_block_once(
    payload: dict[str, JsonValue], result: EventCheckResult, options: NativeHookOptions
) -> bool:
    """仅为显式启用、完整已检查且宿主未续跑的补证或修订建议请求一次纠正。"""
    return (
        options.block_once
        and options.semantic
        and options.outbound_data_permitted
        and payload.get("stop_hook_active") is False
        and result.status == "checked"
        and result.instructions is not None
        and result.instructions.complete
        and result.advice.status == "available"
        and result.advice.suggested_outcome in {"needs_evidence", "amend"}
    )


def native_hook_response(
    payload: dict[str, JsonValue],
    result: EventCheckResult,
    options: NativeHookOptions | None = None,
) -> dict[str, JsonValue]:
    """遵循实际原生输出 schema；默认 Stop 提示不声称已回灌模型。"""
    options = options if options is not None else NativeHookOptions()
    native_event = _native_event(payload)
    if result.event != NATIVE_EVENT_MAP[native_event]:
        raise ValueError("native and logical event mismatch")
    if native_event in {"Stop", "SubagentStop"}:
        if _should_block_once(payload, result, options):
            return {"decision": "block", "reason": _feedback(result)}
        return {
            "systemMessage": (
                _notice(result) + " 本响应未向模型注入 Hook 契约。"
                "依赖完成或进展结论前，主动调用 workflow_check_event。"
            )
        }
    return {
        "hookSpecificOutput": {
            "hookEventName": native_event,
            "additionalContext": _feedback(result),
        }
    }

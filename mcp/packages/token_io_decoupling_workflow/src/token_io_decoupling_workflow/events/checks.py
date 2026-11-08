"""将单次事实与同批次文档分层检查，不推进工作流。"""

from __future__ import annotations

import hashlib
from typing import Literal

from token_io_decoupling_workflow.compiled_rules.contracts import RuleLoadError
from token_io_decoupling_workflow.compiled_rules.loader import RuleLoader
from token_io_decoupling_workflow.events.advice import EventAdvisor
from token_io_decoupling_workflow.events.contracts import CompiledEvent, EventInstructions
from token_io_decoupling_workflow.events.models import (
    EventAdvice,
    EventCheckRequest,
    EventCheckResult,
    EventStructuralCheck,
    canonical_event_json,
)


def load_event_instructions(rules: RuleLoader, request: EventCheckRequest) -> EventInstructions:
    """原子交付完整事件及可选流程；预算不足时两者都不交付部分正文。"""
    event = rules.load_event(request.event, language=request.language, mode=request.mode)
    workflow = None
    if request.include_workflow:
        assert request.mode is not None
        workflow = rules.load_workflow(request.mode, language=request.language)
        if workflow.build_id != event.build_id:
            raise RuleLoadError("mixed compiled instruction builds")
    required_chars = len(event.text) + (len(workflow.text) if workflow else 0)
    complete = required_chars <= request.max_chars
    if not complete:
        event = event.model_copy(update={"text": ""})
        if workflow is not None:
            workflow = workflow.model_copy(update={"text": ""})
    return EventInstructions(
        build_id=event.build_id,
        complete=complete,
        status="complete" if complete else "incomplete_budget",
        text_budget=request.max_chars,
        required_text_characters=required_chars,
        text_characters=required_chars if complete else 0,
        event=event,
        workflow=workflow,
    )


def structural_event_check(
    request: EventCheckRequest, event: CompiledEvent
) -> EventStructuralCheck:
    """检查声明形状，不把引用、unknown 或不适用解释视为真实性证明。"""
    unresolved: dict[str, str] = {
        name: request.facts[name].status
        for name in event.required_facts
        if name in request.facts and request.facts[name].status != "provided"
    }
    missing_facts = [
        name for name in event.required_facts if name not in request.facts or name in unresolved
    ]
    supplied_evidence = {item.kind for item in request.evidence_refs}
    missing_evidence = [name for name in event.required_evidence if name not in supplied_evidence]
    incomplete = bool(missing_facts or missing_evidence)
    return EventStructuralCheck(
        status="incomplete_for_agent_review" if incomplete else "ready_for_agent_review",
        reason="requirements_missing" if incomplete else "requirements_structurally_present",
        missing_facts=missing_facts,
        missing_evidence=missing_evidence,
        unresolved_fact_statuses=unresolved,
    )


def _initial_result(request: EventCheckRequest) -> EventCheckResult:
    """为本次规范输入生成指纹，结构和建议均从尚未评估的状态开始。"""
    return EventCheckResult(
        event=request.event,
        mode=request.mode,
        language=request.language,
        status="checked",
        reason="event_checked",
        input_hash=hashlib.sha256(
            canonical_event_json(request.model_dump(mode="json")).encode("utf-8")
        ).hexdigest(),
        instructions=None,
        structural_check=EventStructuralCheck(status="not_evaluated", reason="not_evaluated"),
        advice=EventAdvice(status="not_requested", reason="not_requested"),
    )


def _reject_context(
    result: EventCheckResult,
    status: Literal["instructions_incomplete", "rules_unavailable", "stale"],
    reason: str,
    semantic_requested: bool,
) -> EventCheckResult:
    """指令缺失、不完整或陈旧时停止后续评估，避免沿用先前的可用结论。"""
    result.status = status
    result.reason = reason
    result.structural_check = EventStructuralCheck(status="not_evaluated", reason=reason)
    if status == "stale":
        result.advice = EventAdvice(status="stale", reason="stale_context")
    elif semantic_requested:
        result.advice = EventAdvice(status="unavailable", reason=reason)
    return result


def expected_context_matches(request: EventCheckRequest, instructions: EventInstructions) -> bool:
    """调用方可钉住当前文档，但该指纹不是执行游标。"""
    return (
        request.expected_build_id is None or request.expected_build_id == instructions.build_id
    ) and (
        request.expected_rule_hash is None
        or request.expected_rule_hash == instructions.event.rule_hash
    )


class WorkflowEventChecker:
    """按规则完整性、输入结构、可选建议的顺序处理一个独立请求。"""

    def __init__(self, rules: RuleLoader, advisor: EventAdvisor) -> None:
        """注入静态规则与可选建议服务，不初始化运行历史或持久化后端。"""
        self._rules = rules
        self._advisor = advisor

    def check(self, request: EventCheckRequest) -> EventCheckResult:
        """不读取历史、保存状态、授权动作或替 Agent 宣告完成。"""
        result = _initial_result(request)
        semantic_requested = request.semantic_input is not None
        try:
            result.instructions = load_event_instructions(self._rules, request)
        except (RuleLoadError, OSError, ValueError):
            return _reject_context(
                result, "rules_unavailable", "rule_context_unavailable", semantic_requested
            )
        if not expected_context_matches(request, result.instructions):
            return _reject_context(result, "stale", "stale_instruction_context", semantic_requested)
        if not result.instructions.complete:
            return _reject_context(
                result, "instructions_incomplete", "instruction_budget_exceeded", semantic_requested
            )
        result.structural_check = structural_event_check(request, result.instructions.event)
        result.advice = self._advisor.advise(
            request, result.instructions, result.structural_check, result.input_hash
        )
        return result

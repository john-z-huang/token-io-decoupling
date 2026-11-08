"""准备 Decisions 问题、验证选项并构造安全回退结果。"""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from openai.types.decision_create_params import QuestionQuestionParamChoice

from token_io_decoupling_core.models import RuleContext
from token_io_decoupling_core.workflow_contracts.vocabulary import CheckpointNode
from token_io_decoupling_workflow.api_recovery import (
    ProviderFailure,
    RecoveryGuidance,
    recovery_for_provider_failure,
)
from token_io_decoupling_workflow.decision_prompts import DecisionPrompt

from .models import (
    DECISIONS_MODEL,
    DecisionAdvice,
    DecisionAdvisoryInput,
    _CheckpointSource,
    _PreparedAdvice,
)


def _decision_question(prepared: _PreparedAdvice) -> QuestionQuestionParamChoice:
    """只提供当前已审阅分支及其解释，不让调用方扩展模型可选政策。"""
    return {
        "type": "choice",
        "name": prepared.prompt.question_name,
        "instructions": prepared.prompt.instructions(),
        "choices": [
            {"value": choice, "description": prepared.prompt.branch_descriptions[choice]}
            for choice in prepared.rules.legal_branches
        ],
    }


def _checkpoint_response(response: object, prepared: _PreparedAdvice) -> DecisionAdvice:
    """解析合法选项并检查返回模型；失败保留 fallback，不伪造缺失用量。"""
    answer = validated_choice(
        response, prepared.prompt.question_name, set(prepared.rules.legal_branches)
    )
    if answer is None:
        return _fallback(
            "refusal"
            if is_refusal(response, prepared.prompt.question_name)
            else "invalid_response",
            prepared.node_id,
            prepared.basis_hash,
            prepared.rules,
        )
    response_model = getattr(response, "model", None)
    if response_model is not None and response_model != DECISIONS_MODEL:
        return _fallback("invalid_response", prepared.node_id, prepared.basis_hash, prepared.rules)
    total_tokens = getattr(getattr(response, "usage", None), "total_tokens", None)
    if type(total_tokens) is not int or total_tokens < 0:
        total_tokens = None
    return DecisionAdvice(
        status="available",
        reason="advice_available",
        node_id=prepared.node_id,
        suggested_choice=answer,
        input_hash=prepared.basis_hash,
        rule_hash=prepared.rules.context_hash,
        model=DECISIONS_MODEL,
        total_tokens=total_tokens,
    )


def _basis_hash(
    advisory_input: DecisionAdvisoryInput,
    source: _CheckpointSource,
    rule_hash: str,
) -> str:
    """把语义输入、当前事实、来源指纹与规则绑定，防止跨来源复用建议。"""
    basis = {
        "input": advisory_input.model_dump(mode="json"),
        "current_facts": source.current_facts,
        "checkpoint_source_input_hash": source.checkpoint_source_input_hash,
        "language": source.language,
        "rule_hash": rule_hash,
    }
    encoded = json.dumps(basis, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _request_input(
    advisory_input: DecisionAdvisoryInput,
    rules: RuleContext,
    prompt: DecisionPrompt,
    source: _CheckpointSource,
) -> str:
    """区分调用方事实与批准政策，将完整节点正文送入同一次有界请求。"""
    facts = advisory_input.model_dump(mode="json", exclude={"node_id"})
    payload = {
        "node_id": advisory_input.node_id.value,
        "facts": facts,
        "caller_supplied_current_facts": source.current_facts,
        "checkpoint_source_input_hash": source.checkpoint_source_input_hash,
        "language": source.language,
        "rule_facts": rules.required_facts,
        "rule_evidence": rules.required_evidence,
        "allowed_choices": rules.legal_branches,
        "decision_context": {
            "objective": prompt.objective,
            "field_meanings": dict(prompt.field_meanings),
            "evaluation_mode": rules.evaluation_mode,
            "failure_action": rules.failure_action,
            "rule_hash": rules.context_hash,
        },
        "owner_section": {
            "source": rules.owner_path,
            "heading": rules.owner_section,
            "text": rules.owner_text,
        },
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def validated_choice(response: object, expected_name: str, allowed: set[str]) -> str | None:
    """读取唯一且匹配问题名的合法选项，不证明响应整体完成或事实成立。"""
    answers = getattr(response, "answers", None)
    if not isinstance(answers, (list, tuple)) or len(answers) != 1:
        return None
    answer = answers[0]
    if getattr(answer, "type", None) != "choice" or getattr(answer, "name", None) != expected_name:
        return None
    choice = getattr(answer, "choice", None)
    return choice if isinstance(choice, str) and choice in allowed else None


def is_refusal(response: object, expected_name: str) -> bool:
    """仅识别当前单问题的显式拒绝，调用方仍需独立校验整体响应。"""
    answers = getattr(response, "answers", None)
    return (
        isinstance(answers, (list, tuple))
        and len(answers) == 1
        and getattr(answers[0], "type", None) == "refusal"
        and getattr(answers[0], "name", None) == expected_name
    )


def _fallback(
    reason: Literal[
        "missing_credentials",
        "provider_error",
        "timeout",
        "refusal",
        "invalid_response",
        "rule_context_too_large",
        "rule_context_unavailable",
        "stale_context",
    ],
    node_id: CheckpointNode,
    input_hash: str,
    rules: RuleContext,
    *,
    failure: ProviderFailure | None = None,
) -> DecisionAdvice:
    """保留供应商分类后的恢复提示；建议本身不触发重试或效果。"""
    failure_class = failure.failure_class if failure is not None else None
    recovery = (
        recovery_for_provider_failure(failure)
        if failure is not None
        else RecoveryGuidance(
            retry_eligible=False,
            action="continue_without_advice_or_review",
        )
    )
    return DecisionAdvice(
        status="fallback" if reason != "stale_context" else "stale",
        reason=reason,
        node_id=node_id,
        input_hash=input_hash,
        rule_hash=rules.context_hash,
        failure_class=failure_class,
        recovery=recovery,
        http_status=failure.http_status if failure is not None else None,
        provider_error_code=failure.provider_error_code if failure is not None else None,
    )

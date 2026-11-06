"""Bounded, non-authoritative Decisions API advice for selected Coding checkpoints."""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Callable
from contextlib import closing
from dataclasses import dataclass
from typing import Annotated, Literal, Protocol, TypeAlias, runtime_checkable

from openai.types.decision_create_params import QuestionQuestionParamChoice
from pydantic import ConfigDict, Field, StrictBool, StrictStr, model_validator

from token_io_decoupling_core.models import RuleContext, StrictModel
from token_io_decoupling_core.workflow_models import CheckpointNode, EpochDimension
from token_io_decoupling_workflow.api_recovery import (
    FailureClass,
    ProviderErrorCode,
    ProviderFailure,
    RecoveryGuidance,
    classify_provider_failure,
    recovery_for_provider_failure,
)
from token_io_decoupling_workflow.decision_prompts import DecisionPrompt, reviewed_prompt
from token_io_decoupling_workflow.rules import RuleLoader, RuleLoadError

DECISIONS_MODEL = "gpt-6-luna"
DECISIONS_TIMEOUT_SECONDS = 20.0
MAX_REQUEST_CHARS = 8_000
SUPPORTED_ADVISORY_NODES = frozenset(
    {
        CheckpointNode.TASK_INTENT,
        CheckpointNode.OUTPUT_CLASS,
        CheckpointNode.CONTRACT_CHANGE,
        CheckpointNode.VERIFICATION_IMPACT,
        CheckpointNode.CONTROL,
    }
)

ShortText = Annotated[StrictStr, Field(min_length=1, max_length=400)]
DeliverableList = Annotated[list[ShortText], Field(max_length=5)]


class AdvisoryInputBase(StrictModel):
    """调用方提供的当次语义事实；其文字不具有政策或授权效力。"""

    model_config = ConfigDict(extra="forbid", strict=True)


class TaskIntentInput(AdvisoryInputBase):
    """用于判断 Coding 范围的任务目标与交付物事实。"""

    node_id: Literal[CheckpointNode.TASK_INTENT]
    requested_outcome: ShortText
    deliverables: DeliverableList = Field(default_factory=list)
    task_signal: Literal["coding", "not_coding", "mixed", "unclear"]


class OutputClassInput(AdvisoryInputBase):
    """用于判断交付类别的输出事实；边界标签不授权委派。"""

    node_id: Literal[CheckpointNode.OUTPUT_CLASS]
    requested_output: ShortText
    deliverables: DeliverableList = Field(default_factory=list)
    delegation_boundary: Literal["root_only", "worker_eligible", "mixed", "unclear"]


class ContractChangeInput(AdvisoryInputBase):
    """当前变化与用户方向的事实，不直接确立 Contract 已经修订。"""

    node_id: Literal[CheckpointNode.CONTRACT_CHANGE]
    change_summary: ShortText
    objective_or_scope_changed: StrictBool
    new_user_direction_present: StrictBool


class VerificationImpactInput(AdvisoryInputBase):
    """用于推导受影响验证维度的变化与覆盖事实。"""

    node_id: Literal[CheckpointNode.VERIFICATION_IMPACT]
    change_summary: ShortText
    changed_dimensions: Annotated[list[EpochDimension], Field(max_length=3)]
    affected_coverage: Annotated[list[EpochDimension], Field(max_length=3)]

    @model_validator(mode="after")
    def affected_coverage_is_bounded_by_change(self) -> VerificationImpactInput:
        """禁止将受影响覆盖声明到未报告变化的维度之外。"""
        if not set(self.affected_coverage) <= set(self.changed_dimensions):
            raise ValueError("affected coverage must be included in changed dimensions")
        return self


class ControlInput(AdvisoryInputBase):
    """当前实质边界的进展与证据状态，不是自动阶段推进命令。"""

    node_id: Literal[CheckpointNode.CONTROL]
    progress_signal: Literal["continue", "amend", "stop", "evidence-on-demand"]
    slice_outcome: Literal["ready", "incomplete", "blocked", "returned"]
    evidence_request_status: Literal["not_requested", "pending", "returned"]
    boundary_summary: ShortText


DecisionAdvisoryInput: TypeAlias = Annotated[
    TaskIntentInput
    | OutputClassInput
    | ContractChangeInput
    | VerificationImpactInput
    | ControlInput,
    Field(discriminator="node_id"),
]


class DecisionsRuntimeConfig(StrictModel):
    """独立建议通道的启动设置；启用时必须明确承担数据外发许可。"""

    enabled: StrictBool = False
    outbound_data_permitted: StrictBool = False

    @model_validator(mode="after")
    def enabled_requires_explicit_outbound_permission(self) -> DecisionsRuntimeConfig:
        """阻止仅启用建议开关却没有明确外发许可的配置。"""
        if self.enabled and not self.outbound_data_permitted:
            raise ValueError("Decisions requires explicit outbound data permission")
        return self


class DecisionAdvice(StrictModel):
    """当前检查点的非权威建议；只有新鲜 available 结果可交给 Agent 复核。"""

    status: Literal["available", "fallback", "stale"]
    reason: Literal[
        "disabled",
        "advice_available",
        "rule_context_unavailable",
        "missing_credentials",
        "provider_error",
        "timeout",
        "refusal",
        "invalid_response",
        "rule_context_too_large",
        "stale_context",
    ]
    failure_class: FailureClass | None = None
    recovery: RecoveryGuidance | None = Field(
        default=None,
        description=("建议调用失败后的恢复提示；不得为了获取建议而重交包围它的状态修改。"),
    )
    http_status: Annotated[int, Field(ge=100, le=599)] | None = None
    provider_error_code: ProviderErrorCode | None = None
    node_id: CheckpointNode
    suggested_choice: str | None = None
    input_hash: str | None = None
    rule_hash: str | None = None
    model: Literal["gpt-6-luna"] | None = None
    total_tokens: int | None = None


ClientFactory = Callable[[str, str], object]


@dataclass(frozen=True)
class _CheckpointSource:
    """当次检查点来源，用同一组事实生成请求并核对返回后的新鲜度。"""

    current_facts: dict[str, str]
    checkpoint_source_input_hash: str
    language: Literal["zh_cn"]


@dataclass(frozen=True)
class _PreparedAdvice:
    """已匹配当前规则和问题的单次建议请求，不保存到服务状态。"""

    node_id: CheckpointNode
    rules: RuleContext
    prompt: DecisionPrompt
    request_input: str
    basis_hash: str


@runtime_checkable
class _ClosableClient(Protocol):
    """SDK 释放边界；无法确认关闭能力的客户端不进入请求。"""

    def close(self) -> None:
        """释放本次客户端；关闭异常交给调用边界分类。"""
        ...


@runtime_checkable
class _DecisionsResource(Protocol):
    """仅声明本功能需要的单次 Decisions 请求能力。"""

    def create(
        self, *, model: str, input: str, questions: list[QuestionQuestionParamChoice]
    ) -> object:
        """提交固定形状请求，返回值仍需独立校验。"""
        ...


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


class DecisionsAdvisor:
    """提供检查点的单次建议；规则和结构检查不依赖网络建议成功。"""

    def __init__(
        self,
        rule_loader: RuleLoader,
        config: DecisionsRuntimeConfig,
        *,
        client_factory: ClientFactory | None = None,
    ) -> None:
        self._rule_loader = rule_loader
        self._config = config
        self._client_factory = client_factory

    def advise(
        self,
        advisory_input: DecisionAdvisoryInput,
        *,
        current_facts: dict[str, str],
        checkpoint_source_input_hash: str,
        language: Literal["zh_cn"] = "zh_cn",
        expected_rule_hash: str,
    ) -> DecisionAdvice:
        """保留现有调用接口；外部请求或释放故障均返回安全 fallback。"""
        if not self._config.enabled:
            return DecisionAdvice(
                status="fallback", reason="disabled", node_id=advisory_input.node_id
            )
        source = _CheckpointSource(current_facts, checkpoint_source_input_hash, language)
        prepared = self._prepare(advisory_input, source, expected_rule_hash)
        if isinstance(prepared, DecisionAdvice):
            return prepared
        api_key, base_url = os.environ.get("OPENAI_API_KEY"), os.environ.get("OPENAI_BASE_URL")
        if not api_key or not api_key.strip() or not base_url or not base_url.strip():
            return _fallback(
                "missing_credentials", prepared.node_id, prepared.basis_hash, prepared.rules
            )
        try:
            response = self._request_decision(api_key, base_url, prepared)
        except Exception as exc:
            # SDK 请求与释放是外部边界；失败不采纳选项且不泄露供应商原始消息。
            failure = classify_provider_failure(exc)
            return _fallback(
                failure.reason,
                prepared.node_id,
                prepared.basis_hash,
                prepared.rules,
                failure=failure,
            )
        return self._finish(response, advisory_input, source, prepared)

    def _prepare(
        self,
        advisory_input: DecisionAdvisoryInput,
        source: _CheckpointSource,
        expected_rule_hash: str,
    ) -> _PreparedAdvice | DecisionAdvice:
        """在外发前绑定当前规则、已审阅问题与来源指纹，缺失或超限时直接返回。"""
        node_id = advisory_input.node_id
        if node_id not in SUPPORTED_ADVISORY_NODES:
            return DecisionAdvice(status="fallback", reason="invalid_response", node_id=node_id)
        try:
            rules = self._rule_loader.load_context(node_id.value, language=source.language)
        except (RuleLoadError, OSError, ValueError):
            return DecisionAdvice(
                status="fallback", reason="rule_context_unavailable", node_id=node_id
            )
        if rules.context_hash != expected_rule_hash:
            return DecisionAdvice(status="stale", reason="stale_context", node_id=node_id)
        prompt = reviewed_prompt(node_id, list(rules.legal_branches))
        if not rules.legal_branches or prompt is None:
            return DecisionAdvice(status="fallback", reason="invalid_response", node_id=node_id)
        request_input = _request_input(advisory_input, rules, prompt, source)
        if len(request_input) > MAX_REQUEST_CHARS:
            return _fallback("rule_context_too_large", node_id, "", rules)
        return _PreparedAdvice(
            node_id,
            rules,
            prompt,
            request_input,
            _basis_hash(advisory_input, source, rules.context_hash),
        )

    def _request_decision(self, api_key: str, base_url: str, prepared: _PreparedAdvice) -> object:
        """返回响应前释放客户端；请求或关闭异常都交给上层阻止采纳。"""
        client = self._make_client(api_key, base_url)
        if not isinstance(client, _ClosableClient):
            raise TypeError("checkpoint advice client must support close")
        with closing(client):
            resource = getattr(client, "decisions", None)
            if not isinstance(resource, _DecisionsResource):
                raise TypeError("checkpoint advice client must support decisions.create")
            return resource.create(
                model=DECISIONS_MODEL,
                input=prepared.request_input,
                questions=[_decision_question(prepared)],
            )

    def _finish(
        self,
        response: object,
        advisory_input: DecisionAdvisoryInput,
        source: _CheckpointSource,
        prepared: _PreparedAdvice,
    ) -> DecisionAdvice:
        """仅在响应可用且规则仍新鲜时保留选项，变化时移除选择并返回 stale。"""
        advice = _checkpoint_response(response, prepared)
        if advice.status != "available":
            return advice
        if not self._rules_unchanged(advisory_input, source, prepared):
            return DecisionAdvice(
                status="stale",
                reason="stale_context",
                node_id=prepared.node_id,
                input_hash=prepared.basis_hash,
                rule_hash=prepared.rules.context_hash,
            )
        return advice

    def _rules_unchanged(
        self,
        advisory_input: DecisionAdvisoryInput,
        source: _CheckpointSource,
        prepared: _PreparedAdvice,
    ) -> bool:
        """请求后重读同一规则并重算事实依据；读回失败也不能继续采纳建议。"""
        try:
            current = self._rule_loader.load_context(
                prepared.node_id.value, language=source.language
            )
        except (RuleLoadError, OSError, ValueError):
            return False
        return (
            current.context_hash == prepared.rules.context_hash
            and _basis_hash(advisory_input, source, current.context_hash) == prepared.basis_hash
        )

    def _make_client(self, api_key: str, base_url: str) -> object:
        if self._client_factory is not None:
            return self._client_factory(api_key, base_url)
        from .openai_client import make_openai_client

        return make_openai_client(api_key, base_url, timeout=DECISIONS_TIMEOUT_SECONDS)


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

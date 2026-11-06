"""Stateless, bounded Responses API generation of decision context."""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Callable
from typing import Annotated, Any, Literal, cast

from pydantic import Field, StrictBool, StrictStr, field_validator

from token_io_decoupling_core.models import StrictModel
from token_io_decoupling_transport.payloads import payload_model
from token_io_decoupling_workflow.api_recovery import (
    RecoveryGuidance,
    classify_provider_failure,
    recovery_for_provider_failure,
    recovery_for_reason,
)
from token_io_decoupling_workflow.rules import RuleLoader, RuleLoadError

GENERATION_MODEL = "gpt-6-luna"
GENERATION_TIMEOUT_SECONDS = 20.0

DecisionOutputKind = Literal["decision_question", "decision_context"]
BoundedContent = Annotated[StrictStr, Field(min_length=1, max_length=60_000)]
BoundedGoal = Annotated[StrictStr, Field(min_length=1, max_length=1200)]
ShortText = Annotated[StrictStr, Field(min_length=1, max_length=240)]


class DecisionContextInput(StrictModel):
    """调用方整理的来源材料及一个具体输出目标。"""

    raw_content: BoundedContent = Field(
        description=("调用方整理并标注来源的原始材料，最多 60000 字符；工具不读取文件或仓库。")
    )
    decision_goal: BoundedGoal = Field(
        description=("下游判断的具体目标及所需描述，最多 1200 字符。")
    )
    output_kind: DecisionOutputKind = Field(
        description=("返回一个 decision_question，或一段客观的 decision_context。")
    )
    outbound_data_permitted: StrictBool = Field(
        description=("明确断言允许本次数据外发；该字段不证明实际授权。")
    )

    @field_validator("raw_content", "decision_goal")
    @classmethod
    def text_is_not_blank(cls, value: str) -> str:
        """来源材料与判断目标都必须有实际内容，不能只满足长度类型。"""
        if not value.strip():
            raise ValueError("text fields must not be blank")
        return value


DecisionContextPayload = payload_model(
    "DecisionContextPayload", request=(DecisionContextInput, ...)
)


class DecisionContextStructuredOutput(StrictModel):
    """Responses API 返回的严格结构，后续仍须检查输出类别。"""

    description: Annotated[StrictStr, Field(min_length=1, max_length=6000)] | None
    missing_information: Annotated[list[ShortText], Field(max_length=8)]


class DecisionContextResult(StrictModel):
    """一份已校验的描述或明确缺口；生成成功仍须调用方审阅忠实性。"""

    status: Literal["available", "blocked"]
    reason: Literal[
        "description_generated",
        "policy_unavailable",
        "stale_policy",
        "outbound_data_not_permitted",
        "missing_credentials",
        "provider_error",
        "timeout",
        "refusal",
        "incomplete",
        "invalid_response",
        "insufficient_evidence",
    ]
    description: StrictStr | None = None
    missing_information: list[ShortText] = Field(default_factory=list, max_length=8)
    input_hash: Annotated[StrictStr, Field(pattern=r"^[a-f0-9]{64}$")]
    output_kind: DecisionOutputKind
    model: Literal["gpt-6-luna"] | None = None
    source_policy_hash: Annotated[StrictStr, Field(pattern=r"^[a-f0-9]{64}$")] | None = None
    recovery: RecoveryGuidance | None = Field(
        default=None, description="供调用方参考的恢复提示；null 表示没有重试提示。"
    )
    total_tokens: int | None = None


ClientFactory = Callable[[str, str], object]


class DecisionContextGenerator:
    """只生成一个有界问题或背景段落，不读取仓库状态或触发下游操作。"""

    def __init__(self, *, rules: RuleLoader, client_factory: ClientFactory | None = None) -> None:
        self._rules = rules
        self._client_factory = client_factory

    def generate(self, payload: DecisionContextInput) -> DecisionContextResult:
        """核对政策与外发许可后请求一次描述，并将陈旧或无效结果安全阻止。"""
        input_hash = _input_hash(payload)
        if not payload.outbound_data_permitted:
            return _blocked("outbound_data_not_permitted", input_hash, payload.output_kind)

        try:
            policy = self._rules.load_delegation_policy("decision-context-generation")
            policy_text, source_policy_hash = policy.text, policy.content_sha256
        except (RuleLoadError, OSError, ValueError):
            return _blocked("policy_unavailable", input_hash, payload.output_kind)

        def blocked(
            reason: Literal[
                "policy_unavailable",
                "stale_policy",
                "outbound_data_not_permitted",
                "missing_credentials",
                "provider_error",
                "timeout",
                "refusal",
                "incomplete",
                "invalid_response",
                "insufficient_evidence",
            ],
            *,
            missing_information: list[ShortText] | None = None,
            recovery: RecoveryGuidance | None = None,
        ) -> DecisionContextResult:
            return _blocked(
                reason,
                input_hash,
                payload.output_kind,
                missing_information=missing_information,
                source_policy_hash=source_policy_hash,
                recovery=recovery,
            )

        api_key = os.environ.get("OPENAI_API_KEY")
        base_url = os.environ.get("OPENAI_BASE_URL")
        if not api_key or not api_key.strip() or not base_url or not base_url.strip():
            return blocked("missing_credentials")

        request = _request_input(payload)
        client: object | None = None
        try:
            client = self._make_client(api_key, base_url)
            response = cast(Any, client).responses.parse(
                model=GENERATION_MODEL,
                input=request,
                instructions=policy_text,
                text_format=DecisionContextStructuredOutput,
                store=False,
                reasoning={"effort": "medium"},
                max_output_tokens=4096,
                truncation="disabled",
                tools=[],
            )
        except Exception as exc:
            failure = classify_provider_failure(exc)
            return blocked(_failure_reason(exc), recovery=recovery_for_provider_failure(failure))
        finally:
            close = getattr(client, "close", None)
            if callable(close):
                try:
                    close()
                except Exception:
                    pass

        if getattr(response, "status", None) != "completed":
            return blocked("incomplete")
        if (
            getattr(response, "error", None) is not None
            or getattr(response, "incomplete_details", None) is not None
        ):
            return blocked("invalid_response")
        if getattr(response, "model", None) != GENERATION_MODEL:
            return blocked("invalid_response")
        if _is_refusal(response):
            return blocked("refusal")

        parsed = getattr(response, "output_parsed", None)
        if type(parsed) is not DecisionContextStructuredOutput:
            return blocked("invalid_response")
        description = parsed.description
        missing = parsed.missing_information
        if any(not item.strip() for item in missing):
            return blocked("invalid_response")
        if description is None:
            if not missing:
                return blocked("invalid_response")
            return blocked(
                "insufficient_evidence",
                missing_information=missing,
            )
        if not description.strip() or missing:
            return blocked("invalid_response")
        output_limit = 1200 if payload.output_kind == "decision_question" else 6000
        if len(description) > output_limit:
            return blocked("invalid_response")

        try:
            current_policy_hash = self._rules.load_delegation_policy(
                "decision-context-generation"
            ).content_sha256
        except (RuleLoadError, OSError, ValueError):
            return blocked("stale_policy")
        if current_policy_hash != source_policy_hash:
            return blocked("stale_policy")

        usage = getattr(response, "usage", None)
        total_tokens = getattr(usage, "total_tokens", None)
        if type(total_tokens) is not int or total_tokens < 0:
            total_tokens = None
        return DecisionContextResult(
            status="available",
            reason="description_generated",
            description=description,
            input_hash=input_hash,
            output_kind=payload.output_kind,
            model=GENERATION_MODEL,
            source_policy_hash=source_policy_hash,
            total_tokens=total_tokens,
        )

    def _make_client(self, api_key: str, base_url: str) -> object:
        if self._client_factory is not None:
            return self._client_factory(api_key, base_url)
        from .openai_client import make_openai_client

        return make_openai_client(api_key, base_url, timeout=GENERATION_TIMEOUT_SECONDS)


def _request_input(payload: DecisionContextInput) -> str:
    request = payload.model_dump(mode="json", exclude={"outbound_data_permitted"})
    return json.dumps(
        {"request": request},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _input_hash(payload: DecisionContextInput) -> str:
    content = payload.model_dump(mode="json", exclude={"outbound_data_permitted"})
    return hashlib.sha256(
        json.dumps(content, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()


def _is_refusal(response: object) -> bool:
    output = getattr(response, "output", None)
    if not isinstance(output, list):
        return False
    for item in output:
        content_items = getattr(item, "content", None)
        if not isinstance(content_items, list):
            continue
        for content in content_items:
            if getattr(content, "type", None) == "refusal" or getattr(content, "refusal", None):
                return True
    return False


def _failure_reason(exc: Exception) -> Literal["provider_error", "timeout", "invalid_response"]:
    name = type(exc).__name__.lower()
    if "timeout" in name:
        return "timeout"
    if "validation" in name or "parsing" in name or "parse" in name:
        return "invalid_response"
    return "provider_error"


def _blocked(
    reason: Literal[
        "policy_unavailable",
        "stale_policy",
        "outbound_data_not_permitted",
        "missing_credentials",
        "provider_error",
        "timeout",
        "refusal",
        "incomplete",
        "invalid_response",
        "insufficient_evidence",
    ],
    input_hash: str,
    output_kind: DecisionOutputKind,
    *,
    missing_information: list[ShortText] | None = None,
    source_policy_hash: str | None = None,
    recovery: RecoveryGuidance | None = None,
) -> DecisionContextResult:
    return DecisionContextResult(
        status="blocked",
        reason=reason,
        input_hash=input_hash,
        output_kind=output_kind,
        missing_information=missing_information or [],
        source_policy_hash=source_policy_hash,
        recovery=recovery or recovery_for_reason(reason),
    )

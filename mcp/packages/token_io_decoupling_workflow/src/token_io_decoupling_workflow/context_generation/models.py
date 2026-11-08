"""描述生成的受限输入、严格输出和稳定阻止原因。"""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated, Literal

from pydantic import Field, StrictBool, StrictStr, field_validator

from token_io_decoupling_core.models import StrictModel
from token_io_decoupling_transport.payloads import payload_model
from token_io_decoupling_workflow.api_recovery import (
    RecoveryGuidance,
    recovery_for_reason,
)

GENERATION_MODEL = "gpt-6-luna"


GENERATION_TIMEOUT_SECONDS = 20.0


DecisionOutputKind = Literal["decision_question", "decision_context"]


BoundedContent = Annotated[StrictStr, Field(min_length=1, max_length=60_000)]


BoundedGoal = Annotated[StrictStr, Field(min_length=1, max_length=1200)]


ShortText = Annotated[StrictStr, Field(min_length=1, max_length=240)]


_BlockedReason = Literal[
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
    reason: Literal["description_generated", _BlockedReason]
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


_RequestFailureReason = Literal[
    "missing_credentials", "provider_error", "timeout", "invalid_response"
]


_ResponseFailureReason = Literal[
    "incomplete", "invalid_response", "refusal", "insufficient_evidence"
]


def _blocked(
    reason: _BlockedReason,
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

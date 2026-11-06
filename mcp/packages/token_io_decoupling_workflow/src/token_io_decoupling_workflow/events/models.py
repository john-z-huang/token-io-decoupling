"""单次 Hook 检查的数据契约；不承载跨调用运行状态。"""

from __future__ import annotations

import json
from typing import Annotated, Literal

from pydantic import Field, StrictBool, StrictInt, StrictStr, model_validator

from token_io_decoupling_core.models import Language, Sha256, StrictModel
from token_io_decoupling_workflow.api_recovery import (
    FailureClass,
    ProviderErrorCode,
    RecoveryGuidance,
)
from token_io_decoupling_workflow.events.contracts import (
    DEFAULT_EVENT_TEXT_BUDGET,
    MAX_CONTEXT_TEXT_BUDGET,
    MIN_CONTEXT_TEXT_BUDGET,
    EventId,
    EventInstructions,
    EventOutcome,
    WorkflowMode,
)

MAX_EVENT_REQUEST_BYTES = 32 * 1024
FactName = Annotated[StrictStr, Field(pattern=r"^[a-z][a-z0-9_]{0,79}$")]
FactText = Annotated[StrictStr, Field(min_length=1, max_length=16_000)]
ReferenceText = Annotated[StrictStr, Field(min_length=1, max_length=512)]


def canonical_event_json(value: object) -> str:
    """生成有序 JSON；拒绝 JSON 标准外的 NaN 和无穷大。"""
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    )


class EventFact(StrictModel):
    """调用方声明的事实状态、内容与来源；unknown 和不适用仍需 Agent 复核。"""

    status: Literal["provided", "unknown", "not_applicable"] = "provided"
    value: FactText | None = None
    source: ReferenceText | None = None

    @model_validator(mode="after")
    def value_matches_status(self) -> EventFact:
        """已提供事实和不适用判断必须有非空依据，未知状态不能伪装充分信息。"""
        if self.status in {"provided", "not_applicable"} and (
            self.value is None or not self.value.strip()
        ):
            raise ValueError("provided facts and not_applicable explanations need a value")
        if self.value is not None and not self.value.strip():
            raise ValueError("fact value must not be blank")
        if self.source is not None and not self.source.strip():
            raise ValueError("fact source must not be blank")
        return self


class EventEvidenceReference(StrictModel):
    """只提供有界证据定位，服务不读取引用或认证其真实性。"""

    kind: FactName
    reference: ReferenceText

    @model_validator(mode="after")
    def reference_is_not_blank(self) -> EventEvidenceReference:
        """拒绝空白定位，保证缺口报告仍可人工追溯。"""
        if not self.reference.strip():
            raise ValueError("evidence reference must not be blank")
        return self


class EventSemanticInput(StrictModel):
    """当次可选语义建议的外发声明与关注点，不允许覆盖文档政策。"""

    outbound_data_permitted: StrictBool = False
    focus: Annotated[StrictStr, Field(min_length=1, max_length=1_000)] | None = None

    @model_validator(mode="after")
    def focus_is_not_blank(self) -> EventSemanticInput:
        """提供关注点时必须有实际内容，避免无意义数据进入请求。"""
        if self.focus is not None and not self.focus.strip():
            raise ValueError("semantic focus must not be blank")
        return self


class EventCheckRequest(StrictModel):
    """一个独立逻辑事件及当前事实；不接受阶段控制或跨调用状态。"""

    event: EventId
    mode: WorkflowMode | None = None
    language: Language = "zh_cn"
    include_workflow: StrictBool = False
    context_summary: Annotated[StrictStr, Field(max_length=8_000)] = ""
    facts: Annotated[dict[FactName, EventFact], Field(max_length=64)] = Field(default_factory=dict)
    evidence_refs: Annotated[list[EventEvidenceReference], Field(max_length=64)] = Field(
        default_factory=list
    )
    expected_build_id: Sha256 | None = None
    expected_rule_hash: Sha256 | None = None
    max_chars: Annotated[
        StrictInt, Field(ge=MIN_CONTEXT_TEXT_BUDGET, le=MAX_CONTEXT_TEXT_BUDGET)
    ] = DEFAULT_EVENT_TEXT_BUDGET
    semantic_input: EventSemanticInput | None = None

    @model_validator(mode="after")
    def request_is_bounded(self) -> EventCheckRequest:
        """校验模式依赖与完整请求字节上限，不截断调用方事实。"""
        if self.include_workflow and self.mode is None:
            raise ValueError("include_workflow requires an explicit mode")
        encoded = canonical_event_json(self.model_dump(mode="json")).encode("utf-8")
        if len(encoded) > MAX_EVENT_REQUEST_BYTES:
            raise ValueError("event_check_request_exceeds_32_kib")
        return self


class EventCheckPayload(StrictModel):
    """MCP 请求信封；完整信封也须通过独立字节预算。"""

    request: EventCheckRequest

    @model_validator(mode="after")
    def payload_is_bounded(self) -> EventCheckPayload:
        """按实际规范 JSON 字节检查完整请求，防止仅限制内层内容。"""
        if len(canonical_event_json(self.model_dump(mode="json")).encode("utf-8")) > (
            MAX_EVENT_REQUEST_BYTES
        ):
            raise ValueError("event_check_payload_exceeds_32_kib")
        return self


class EventStructuralCheck(StrictModel):
    """事实与证据声明的结构缺口；ready 不表示真实、获准或验收成功。"""

    status: Literal["not_evaluated", "incomplete_for_agent_review", "ready_for_agent_review"]
    authority: Literal["structural_check_only"] = "structural_check_only"
    reason: str
    missing_facts: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    unresolved_fact_statuses: dict[str, str] = Field(default_factory=dict)


class EventAdvice(StrictModel):
    """选择与同源规范反馈；不将文档说明冒充模型针对本例的理由。"""

    status: Literal["not_requested", "unavailable", "available", "stale"]
    authority: Literal["advisory_only"] = "advisory_only"
    reason: str
    suggested_outcome: EventOutcome | None = None
    feedback: str | None = None
    feedback_source: Literal["approved_event_instructions"] | None = None
    semantic_reason_provided: Literal[False] = False
    input_hash: Sha256 | None = None
    rule_hash: Sha256 | None = None
    model: Literal["gpt-6-luna"] | None = None
    total_tokens: Annotated[StrictInt, Field(ge=0)] | None = None
    failure_class: FailureClass | None = None
    http_status: StrictInt | None = None
    provider_error_code: ProviderErrorCode | None = None
    recovery: RecoveryGuidance | None = None


class EventCheckResult(StrictModel):
    """分别报告指令、结构与建议；结果不推进状态或自动执行动作。"""

    schema_version: Literal[1] = 1
    event: EventId
    mode: WorkflowMode | None = None
    language: Language
    status: Literal["checked", "instructions_incomplete", "rules_unavailable", "stale"]
    reason: str
    authority: Literal["advisory_only"] = "advisory_only"
    input_hash: Sha256
    instructions: EventInstructions | None
    structural_check: EventStructuralCheck
    advice: EventAdvice
    limitations: list[str] = Field(
        default_factory=lambda: [
            "caller supplied facts and references are not authenticated",
            "structure and advice do not authorize effects or establish acceptance",
            "the Agent retains context; this operation stores no workflow state",
            "no stage progression or cross-call budget is enforced",
        ]
    )

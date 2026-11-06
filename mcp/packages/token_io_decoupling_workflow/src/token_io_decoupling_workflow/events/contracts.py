"""编译后的事件文档与完整性交付契约，不承载执行状态。"""

from __future__ import annotations

import re
from typing import Annotated, Literal, TypeAlias, get_args

from pydantic import Field, StrictInt, StrictStr, field_validator, model_validator

from token_io_decoupling_core.models import Language, Sha256, StrictModel

MIN_CONTEXT_TEXT_BUDGET = 256
MAX_CONTEXT_TEXT_BUDGET = 60_000
DEFAULT_EVENT_TEXT_BUDGET = 24_000
EventId: TypeAlias = Literal[
    "task_received",
    "boundary_requested",
    "action_observed",
    "progress_reported",
    "completion_requested",
    "session_resumed",
]
WorkflowMode: TypeAlias = Literal["single-agent", "multi-agent"]
EventOutcome: TypeAlias = Literal[
    "continue", "needs_evidence", "amend", "wait", "stop", "not_applicable"
]
EVENT_IDS = frozenset(get_args(EventId))
WORKFLOW_MODES = frozenset(get_args(WorkflowMode))
EVENT_OUTCOMES = frozenset(get_args(EventOutcome))
NonemptyText = Annotated[StrictStr, Field(min_length=1)]
DocumentText = Annotated[StrictStr, Field(max_length=MAX_CONTEXT_TEXT_BUDGET)]


class CompiledDocument(StrictModel):
    """仅表示已校验资源的文档内容；空 text 仅用于不完整交付。"""

    schema_version: Literal[1]
    build_id: Sha256
    language: Language
    text: DocumentText
    content_sha256: Sha256
    instruction_ids: Annotated[list[NonemptyText], Field(min_length=1)]

    @field_validator("schema_version", mode="before")
    @classmethod
    def strict_schema_version(cls, value: object) -> object:
        """拒绝布尔值等隐式整数，避免错误版本被接受。"""
        if type(value) is not int or value != 1:
            raise ValueError("compiled event schema_version must be 1")
        return value

    @field_validator("instruction_ids")
    @classmethod
    def unique_instruction_ids(cls, value: list[str]) -> list[str]:
        """保持完整交付单元的身份唯一，避免重复政策被误计。"""
        if len(value) != len(set(value)):
            raise ValueError("compiled instruction identities must be unique")
        return value


class CompiledEvent(CompiledDocument):
    """结构元数据来自作者文档，不在运行时重建判断政策。"""

    event_id: EventId
    rule_hash: Sha256
    modes: Annotated[list[WorkflowMode], Field(min_length=1)]
    required_facts: Annotated[list[NonemptyText], Field(min_length=1)]
    required_evidence: Annotated[list[NonemptyText], Field(min_length=1)]
    allowed_outcomes: Annotated[list[EventOutcome], Field(min_length=1)]

    @model_validator(mode="after")
    def validate_event_contract(self) -> CompiledEvent:
        """正文 Hash、固定事件元数据和文档结果必须一致后才可交付。"""
        for values in (
            self.modes,
            self.required_facts,
            self.required_evidence,
            self.allowed_outcomes,
        ):
            if len(values) != len(set(values)) or any(not item.strip() for item in values):
                raise ValueError("compiled event metadata must be nonblank and unique")
        expected = ["common.shared", f"event.{self.event_id}"]
        if self.instruction_ids != expected:
            raise ValueError("compiled event must contain shared and current event instructions")
        if self.rule_hash != self.content_sha256:
            raise ValueError("compiled event rule hash does not match its content hash")
        return self


class CompiledWorkflow(CompiledDocument):
    """调用方明确选择模式后的简短流程，不保存当前步骤或预定执行路径。"""

    mode: WorkflowMode


class EventInstructions(StrictModel):
    """一次交付中的事件和可选流程必须完整且属于同一编译批次。"""

    schema_version: Literal[1] = 1
    build_id: Sha256
    complete: bool
    status: Literal["complete", "incomplete_budget"]
    text_budget: StrictInt
    required_text_characters: StrictInt
    text_characters: StrictInt
    event: CompiledEvent
    workflow: CompiledWorkflow | None = None


def documented_outcomes(event: CompiledEvent) -> dict[EventOutcome, str]:
    """只摘录编译文档的反馈，不生成个案语义理由或新增政策。"""
    heading = "## 结果与反馈"
    _, found, tail = event.text.rpartition(heading)
    if not found:
        raise ValueError("compiled event outcome feedback is missing")
    section = tail.split("\n## ", 1)[0].strip()
    labels = "|".join(re.escape(outcome) for outcome in event.allowed_outcomes)
    pattern = re.compile(rf"({labels})[:：]\s*(.*?)(?=(?:{labels})[:：]|\Z)", re.DOTALL)
    descriptions = {name: text.strip() for name, text in pattern.findall(section)}
    if set(descriptions) != set(event.allowed_outcomes):
        raise ValueError("compiled event outcomes do not have complete feedback")
    return {outcome: descriptions[outcome] for outcome in event.allowed_outcomes}

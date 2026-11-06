"""API advisory payload models owned by the workflow feature."""

from __future__ import annotations

import json
from typing import Annotated, Any, Literal

from pydantic import (
    Field,
    StrictInt,
    StrictStr,
    StringConstraints,
    field_validator,
    model_validator,
)

from token_io_decoupling_core.models import Sha256, StrictModel
from token_io_decoupling_core.workflow_models import ActiveCheckpointNode, EvidenceSubmission
from token_io_decoupling_workflow.decisions import DecisionAdvisoryInput

MAX_CHECKPOINT_EVALUATION_REQUEST_BYTES = 32 * 1024
CheckpointFactKey = Annotated[StrictStr, StringConstraints(min_length=1, max_length=64)]
CheckpointFactText = Annotated[StrictStr, StringConstraints(min_length=1, max_length=1_024)]
CurrentFacts = Annotated[dict[CheckpointFactKey, CheckpointFactText], Field(max_length=16)]


class _CheckpointEvaluationPayload(StrictModel):
    """一次检查点检查的完整输入，不保存事实修订或任务状态。"""

    submission: EvidenceSubmission
    language: Literal["zh_cn"] = "zh_cn"
    expected_rule_hash: Sha256 | None = None
    semantic_input: DecisionAdvisoryInput | None = None
    current_facts: CurrentFacts = Field(default_factory=dict)

    @field_validator("current_facts")
    @classmethod
    def current_fact_strings_are_not_blank(cls, value: dict[str, str]) -> dict[str, str]:
        """当前事实必须是非空字符串，避免嵌套对象或空白被当作证据。"""
        if any(not key.strip() or not fact.strip() for key, fact in value.items()):
            raise ValueError("current_facts keys and values must not be blank")
        return value

    @model_validator(mode="after")
    def total_request_is_bounded(self) -> _CheckpointEvaluationPayload:
        """限制完整规范请求的 UTF-8 字节数，不以局部字段限制代替整包限制。"""
        encoded = json.dumps(
            self.model_dump(mode="json"), ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        if len(encoded) > MAX_CHECKPOINT_EVALUATION_REQUEST_BYTES:
            raise ValueError("checkpoint_evaluation_request_exceeds_32_kib")
        return self


class EvaluatePayload(_CheckpointEvaluationPayload):
    """任意受支持节点的无状态结构检查请求。"""

    node_id: ActiveCheckpointNode


class ControlEvaluatePayload(_CheckpointEvaluationPayload):
    """固定 Control 节点的无状态结构检查请求。"""

    pass


_EVALUATE = EvaluatePayload
_CONTROL_EVALUATE = ControlEvaluatePayload


class RuleContextPayload(StrictModel):
    """版本 2 规则查询；仅选择完整编译单元，不接受作者源路径。"""

    node_id: ActiveCheckpointNode
    language: Literal["zh_cn"] = "zh_cn"
    context_version: Literal[2] = 2
    fragment_ids: Annotated[
        list[Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=128)]]
        | None,
        Field(
            max_length=128,
            description=("非空时仅选择指定的完整编译单元；省略或为空时返回节点默认集合。"),
        ),
    ] = None
    max_chars: Annotated[StrictInt, Field(ge=256, le=60_000)] | None = None

    @model_validator(mode="before")
    @classmethod
    def require_strict_context_version(cls, value: Any) -> Any:
        """拒绝字符串或布尔版本，确保公开查询契约为真正的整数 2。"""
        if isinstance(value, dict):
            version = value.get("context_version", 2)
            if type(version) is not int or version != 2:
                raise ValueError("context_version must be the integer 2; version 1 is retired")
        return value

    @model_validator(mode="after")
    def require_explicit_context_version(self) -> RuleContextPayload:
        """复核显式片段选择，拒绝重复 ID；版本由字段验证器独立处理。"""
        if self.fragment_ids is not None and len(self.fragment_ids) != len(set(self.fragment_ids)):
            raise ValueError("fragment_ids must not contain duplicates")
        return self


_RULE_CONTEXT = RuleContextPayload

"""工作流建议的受限输入、输出与内部请求快照。"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated, Literal, Protocol, TypeAlias, runtime_checkable

from openai.types.decision_create_params import QuestionQuestionParamChoice
from pydantic import ConfigDict, Field, StrictBool, StrictStr, model_validator

from token_io_decoupling_core.models import RuleContext, StrictModel
from token_io_decoupling_core.workflow_contracts.vocabulary import CheckpointNode, EpochDimension
from token_io_decoupling_workflow.api_recovery import (
    FailureClass,
    ProviderErrorCode,
    RecoveryGuidance,
)
from token_io_decoupling_workflow.decision_prompts import DecisionPrompt

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

"""推理强度选择的受限输入、档位上限与结果校验。"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from typing import Annotated, Any, Literal, cast

from pydantic import ConfigDict, Field, StrictBool, StrictStr, field_validator, model_validator

from token_io_decoupling_core.models import StrictModel
from token_io_decoupling_transport.payloads import payload_model
from token_io_decoupling_workflow.api_recovery import (
    RecoveryGuidance,
    recovery_for_reason,
)

DECISIONS_MODEL = "gpt-6-luna"


DECISIONS_TIMEOUT_SECONDS = 20.0


_ALL_EFFORTS = ("low", "medium", "high", "xhigh", "max")


Effort = Literal["low", "medium", "high", "xhigh", "max"]


DecisionChoice = Effort | Literal["insufficient_evidence"]


_CHOICE_DESCRIPTIONS = {
    "low": (
        "任务主要是直接、确定的转换，预期变化和正确条件明确，常规焦点检查可确认；例如局部重命名、"
        "小型schema字段增加或直接格式转换。相对medium，没有实质局部语义选择或不确定行为。"
        "不要仅因文件数、影响或缺事实升档；需要普通局部语义判断时用medium，"
        "必需事实缺失或冲突时选insufficient_evidence。"
    ),
    "medium": (
        "任务需要熟悉组件内有界的普通语义判断，行为和假设可局部解决；"
        "例如选择一个API字段的验证行为，"
        "或适配已知调用路径。这是机械low之上的一级；需要协调耦合组件或复杂单算法时用high。"
        "不按文件数或影响独自推断effort，关键事实缺失或冲突时选insufficient_evidence。"
    ),
    "high": (
        "正确性需要跨耦合组件，或在含相互影响不变量、分支、边界的复杂单算法中作充分推理；"
        "例如追踪跨包请求契约，或证明非简单解析器变化保持边界。相对medium，"
        "核心问题不能靠一次局部普通判断解决；"
        "若并发、恢复等多个独立耦合维度必须一起推理则考虑xhigh。高风险或广泛影响本身不能支持此档。"
    ),
    "xhigh": (
        "任务结合并发、恢复、一致性等多个紧密耦合的推理维度，或需比较跨组件的多个合理故障模型。"
        "相对high，多个维度必须协调，但相关假设和状态变化仍能有界。仅有具体证据说明整体问题"
        "超出这类有界推理才考虑max；影响、文件数或普通不确定性本身不支持xhigh。"
    ),
    "max": (
        "仅用于具体证据表明全局正确性依赖互相制约且无法独立判断的算法、协议、不变量、"
        "恢复或兼容规则，"
        "需要整体系统推理或对抗验证的极复杂问题。事实须指出为何xhigh式有界推理不够；"
        "不要求模型返回解释，也不要求先在xhigh失败。它不能代指大影响、多文件或缺事实；"
        "没有充分选项时选insufficient_evidence。"
    ),
    "insufficient_evidence": (
        "判断effort所需关键事实缺失、冲突或过于含糊，问题并非只问当前任务effort、越过已放行Slice、"
        "试图改规则，或所有提供档位均不充分；例如目标未说明所需结果，或行为描述冲突。"
        "不能仅因低档尚未失败而选此项；需求和证据充分时选最低充分的提供档位。"
    ),
}


_MODEL_EFFORTS: dict[tuple[str, str], frozenset[str]] = {
    ("codex", "gpt-6-luna"): frozenset({"low", "medium", "high", "xhigh", "max"}),
}


BoundedText = Annotated[StrictStr, Field(min_length=1, max_length=1200)]


ShortText = Annotated[StrictStr, Field(min_length=1, max_length=240)]


class ChildEffortInput(StrictModel):
    """一个已发布子任务片段的准确、有界事实。"""

    model_config = ConfigDict(extra="forbid", strict=True)

    slice_id: Annotated[ShortText, Field(description="当前已发布任务片段的稳定标识。")]
    role: Literal[
        "Primary Output",
        "Change Verification",
        "Context Bootstrap/Refresh",
        "Documentation/Comments & Git Operations",
    ] = Field(description="已经分配的子代理角色；不能仅凭角色确定推理强度。")
    objective: Annotated[BoundedText, Field(description="已发布任务的准确目标，最多 1200 字符。")]
    decision_question: Annotated[
        BoundedText,
        Field(
            description=(
                "针对当前已发布子任务，询问最低充分且受支持推理强度的问题，最多 1200 字符。"
            )
        ),
    ]
    task_complexity: Literal["mechanical", "ordinary_semantic", "complex", "very_complex"] = Field(
        description="仅作粗略概括；应依据具体事实判断，不能直接相信标签。"
    )
    uncertainty: Annotated[
        BoundedText, Field(description="已知的未决事项；没有时明确填写 'none'。")
    ]
    scope: Annotated[BoundedText, Field(description="涉及的文件、模块或系统数量及其相互影响。")]
    dependencies: Annotated[
        BoundedText,
        Field(description=("依赖数量、耦合和集成约束；没有时明确填写 'none'。")),
    ]
    risk: Annotated[BoundedText, Field(description="具体的失败影响与恢复成本。")]
    verification_demands: Annotated[
        BoundedText,
        Field(description="需要的独立验证、集成验证、边界检查或严格证明。"),
    ]
    previous_failure_evidence: Annotated[
        BoundedText,
        Field(description="与当前片段相关的已观察失败或阻塞；没有时明确填写 'none'。"),
    ]
    slice_fingerprint: Annotated[
        StrictStr,
        Field(
            pattern=r"^[a-f0-9]{64}$",
            description=("父代理计算的当前片段 SHA-256 指纹，原样返回以比较新鲜度。"),
        ),
    ]
    runtime: Literal["codex"] = Field(
        description=("固定的 Codex CLI 服务契约；调用方无需选择或分类运行时。")
    )
    child_model: Literal["gpt-6-luna"] = Field(
        description="已核实将由 Codex 子代理创建控制使用的模型。"
    )
    supported_efforts: Annotated[
        list[Effort],
        Field(
            min_length=1,
            max_length=5,
            description="已确认在当前运行时和模型上可用的准确、非空推理强度集合。",
        ),
    ]
    outbound_data_permitted: StrictBool = Field(
        description="明确断言允许本次数据外发；该字段不证明实际授权。"
    )

    @field_validator(
        "slice_id",
        "objective",
        "decision_question",
        "uncertainty",
        "scope",
        "dependencies",
        "risk",
        "verification_demands",
        "previous_failure_evidence",
        "child_model",
    )
    @classmethod
    def text_is_not_blank(cls, value: str) -> str:
        """防止空白事实绕过长度限制，被误当作充分的选择依据。"""
        if not value.strip():
            raise ValueError("text fields must not be blank")
        return value

    @model_validator(mode="after")
    def efforts_are_unique(self) -> ChildEffortInput:
        """保证可选强度集合唯一，避免重复选项影响判断。"""
        if len(set(self.supported_efforts)) != len(self.supported_efforts):
            raise ValueError("supported_efforts must not contain duplicates")
        return self


ChildEffortPayload = payload_model("ChildEffortPayload", request=(ChildEffortInput, ...))


class ChildEffortResult(StrictModel):
    """当前片段的建议强度与新鲜度信息，不授予创建子代理的权限。"""

    status: Literal["available", "blocked"]
    selected_effort: Effort | None = None
    reason: Literal[
        "effort_selected",
        "outbound_data_not_permitted",
        "unsupported_runtime_model",
        "unsupported_effort",
        "missing_credentials",
        "provider_error",
        "timeout",
        "refusal",
        "invalid_response",
        "insufficient_evidence",
    ]
    input_hash: Annotated[
        StrictStr,
        Field(
            pattern=r"^[a-f0-9]{64}$",
            description=("规范化请求事实的 SHA-256，不含调用方许可与指纹。"),
        ),
    ]
    slice_fingerprint: Annotated[
        StrictStr,
        Field(
            pattern=r"^[a-f0-9]{64}$",
            description="原样返回父代理计算的当前片段指纹。",
        ),
    ]
    recovery: RecoveryGuidance | None = Field(
        default=None, description="供调用方参考的恢复提示；null 表示没有重试提示。"
    )
    model: Literal["gpt-6-luna"] | None = None
    total_tokens: int | None = None


ClientFactory = Callable[[str, str], object]


def _request_input(payload: ChildEffortInput) -> str:
    facts = payload.model_dump(mode="json", exclude={"outbound_data_permitted"})
    facts.pop("slice_fingerprint", None)
    decision_question = facts.pop("decision_question")
    return json.dumps(
        {
            "decision_question": decision_question,
            "facts": facts,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _choice_description(level: str) -> str:
    return _CHOICE_DESCRIPTIONS[level]


def _input_hash(payload: ChildEffortInput) -> str:
    content = payload.model_dump(
        mode="json", exclude={"outbound_data_permitted", "slice_fingerprint"}
    )
    return hashlib.sha256(
        json.dumps(content, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()


def _blocked(
    reason: str,
    input_hash: str,
    slice_fingerprint: str,
    *,
    recovery: RecoveryGuidance | None = None,
) -> ChildEffortResult:
    return ChildEffortResult(
        status="blocked",
        reason=cast(Any, reason),
        input_hash=input_hash,
        slice_fingerprint=slice_fingerprint,
        recovery=recovery or recovery_for_reason(reason),
    )


def _validated_choice(response: object, questions: dict[str, set[str]]) -> DecisionChoice | None:
    answers = getattr(response, "answers", None)
    if not isinstance(answers, list) or len(answers) != 1:
        return None
    answer = answers[0]
    name = getattr(answer, "name", None)
    choice = getattr(answer, "choice", None)
    if (
        getattr(answer, "type", None) != "choice"
        or name not in questions
        or not isinstance(choice, str)
        or choice not in questions[name]
    ):
        return None
    return cast(DecisionChoice, choice)


def _is_refusal(response: object, expected_name: str) -> bool:
    answers = getattr(response, "answers", None)
    return isinstance(answers, list) and any(
        getattr(item, "type", None) == "refusal"
        and getattr(item, "name", None) in {None, expected_name}
        for item in answers
    )


def _failure_reason(exc: Exception) -> str:
    name = type(exc).__name__.lower()
    return "timeout" if "timeout" in name else "provider_error"


def _effort_ceiling(runtime: str, child_model: str) -> frozenset[str] | None:
    return _MODEL_EFFORTS.get((runtime, child_model))

"""Strict data contracts for rules, checkpoint evidence, and local authorization."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal, TypeAlias

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictInt,
    StringConstraints,
    field_validator,
    model_validator,
)


class StrictModel(BaseModel):
    """共享严格模型基类；拒绝未知字段和隐式类型转换。"""

    model_config = ConfigDict(extra="forbid", strict=True)


class CodingMode(StrEnum):
    """调用方明确选择的执行模式，不由服务自动推断或切换。"""

    SINGLE_AGENT = "Single-Agent Coding"
    MULTI_AGENT = "Multi-Agent Coding"


class ModeCount(StrictModel):
    """模式与当前子代理数量的组合约束，不记录代理生命周期。"""

    mode: CodingMode
    child_count: Annotated[StrictInt, Field(ge=0)]

    @model_validator(mode="after")
    def validate_mode_count(self) -> ModeCount:
        """拒绝不符合所选模式的数量，避免以计数隐式改变拓扑。"""
        if self.mode is CodingMode.SINGLE_AGENT and self.child_count != 0:
            raise ValueError("Single-Agent Coding requires child_count=0")
        if self.mode is CodingMode.MULTI_AGENT and self.child_count < 1:
            raise ValueError("Multi-Agent Coding requires a positive child_count")
        return self


Sha256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
BoundedOwnerPath = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=512)
]
BoundedOwnerSection = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=256)
]


class SemanticRef(StrictModel):
    """语义材料的定位与内容指纹；引用本身不证明真实性。"""

    uri: NonEmptyString
    content_hash: Sha256


class EvidenceRef(StrictModel):
    """可追溯的证据引用，不代表证据已经被认证或采纳。"""

    uri: NonEmptyString
    content_hash: Sha256
    evidence_id: NonEmptyString | None = None


class JudgmentUnknown(StrictModel):
    """事实仍未知，不能因为结构合法而视为已经确定。"""

    status: Literal["unknown"]


class JudgmentMissingEvidence(StrictModel):
    """明确列出待补证据，供调用方在后续事件中重新复核。"""

    status: Literal["missing_evidence"]
    required_evidence: Annotated[list[NonEmptyString], Field(min_length=1)]


class JudgmentNotApplicable(StrictModel):
    """保存不适用判断及解释；适用性仍由 Agent 复核。"""

    status: Literal["not_applicable"]
    reason: NonEmptyString


class JudgmentDetermined(StrictModel):
    """调用方声明的确定判断及依据，不自动授予行动权限。"""

    status: Literal["determined"]
    value: NonEmptyString
    evidence: list[EvidenceRef] = Field(default_factory=list)


Judgment: TypeAlias = Annotated[
    JudgmentUnknown | JudgmentMissingEvidence | JudgmentNotApplicable | JudgmentDetermined,
    Field(discriminator="status"),
]


EvaluationMode = Literal["direct", "deterministic", "semantic", "hybrid"]
Language = Literal["zh_cn"]


class RuleNode(StrictModel):
    """节点的固定事实、证据与分支需求；owner 仅为编译标识。"""

    node_id: NonEmptyString
    owner_path: NonEmptyString
    owner_section: NonEmptyString
    required_facts: Annotated[list[NonEmptyString], Field(min_length=1)]
    required_evidence: list[NonEmptyString]
    legal_branches: Annotated[list[NonEmptyString], Field(min_length=1)]
    evaluation_mode: EvaluationMode
    failure_action: NonEmptyString
    next_checkpoint_ids: list[NonEmptyString]

    @field_validator("owner_path", "owner_section")
    @classmethod
    def strip_owner_fields(cls, value: str) -> str:
        """拒绝仅由空白组成的定位信息，避免产生不可审阅的规则出处。"""
        stripped = value.strip()
        if not stripped:
            raise ValueError("owner fields must not be blank")
        return stripped


class RuleRegistry(StrictModel):
    """当前单中文注册表；版本和固定需求还须通过消费者守卫。"""

    contract_version: StrictInt
    nodes: Annotated[list[RuleNode], Field(min_length=1)]

    @model_validator(mode="after")
    def unique_node_ids(self) -> RuleRegistry:
        """保持节点标识唯一，并拒绝指向不存在节点的后继引用。"""
        if self.contract_version != 3:
            raise ValueError("registry contract_version must be 3")
        ids = [node.node_id for node in self.nodes]
        if len(ids) != len(set(ids)):
            raise ValueError("node_id values must be unique")
        known = set(ids)
        unknown: set[str] = set()
        for node in self.nodes:
            unknown.update(set(node.next_checkpoint_ids) - known)
        if unknown:
            raise ValueError(f"unknown next_checkpoint_ids: {sorted(unknown)}")
        return self


class RuleContext(StrictModel):
    """外部版本 2 的完整节点规则，供一次静态检查使用。"""

    schema_version: Literal[2] = 2
    build_id: Sha256
    node_id: NonEmptyString
    language: Language
    owner_path: NonEmptyString
    owner_section: NonEmptyString
    owner_text: NonEmptyString
    required_facts: list[NonEmptyString]
    required_evidence: list[NonEmptyString]
    legal_branches: list[NonEmptyString]
    evaluation_mode: EvaluationMode
    failure_action: NonEmptyString
    next_checkpoint_ids: list[NonEmptyString]
    context_hash: Sha256


class RuleContextIndexFragment(StrictModel):
    """一个编译单元的依赖与唯一中文章节，不包含作者路径。"""

    fragment_id: NonEmptyString
    node_id: NonEmptyString
    section: BoundedOwnerSection
    dependencies: list[NonEmptyString] = Field(default_factory=list)


class RuleContextIndexNode(StrictModel):
    """节点默认交付的完整编译单元集合。"""

    node_id: NonEmptyString
    default_fragment_ids: Annotated[list[NonEmptyString], Field(min_length=1)]


class RuleContextIndex(StrictModel):
    """内部版本 2 索引；只定位已编译内容，不解析作者文档。"""

    schema_version: Annotated[StrictInt, Field(ge=2, le=2)]
    nodes: Annotated[list[RuleContextIndexNode], Field(min_length=1)]
    fragments: Annotated[list[RuleContextIndexFragment], Field(min_length=1)]


class RuleContextFragmentResult(StrictModel):
    """已经完整交付的指令单元及其内容指纹。"""

    fragment_id: NonEmptyString
    node_id: NonEmptyString
    owner_path: BoundedOwnerPath
    owner_section: BoundedOwnerSection
    text: NonEmptyString
    text_sha256: Sha256


class RuleContextNodeMetadata(StrictModel):
    """节点的结构检查需求；缺少正文时也不构成可执行指令。"""

    node_id: NonEmptyString
    language: Language
    owner_path: BoundedOwnerPath
    owner_section: BoundedOwnerSection
    required_facts: list[NonEmptyString]
    required_evidence: list[NonEmptyString]
    legal_branches: list[NonEmptyString]
    evaluation_mode: EvaluationMode
    failure_action: NonEmptyString
    next_checkpoint_ids: list[NonEmptyString]


class RuleContextMissingFragment(StrictModel):
    """未能完整交付的单元及缺口，供调用方调整请求容量。"""

    fragment_id: NonEmptyString
    node_id: NonEmptyString
    owner_path: BoundedOwnerPath
    owner_section: BoundedOwnerSection
    reason: NonEmptyString


class RuleContextOwnerReference(StrictModel):
    """保留的查询结果字段，不授权回读原作者文件。"""

    path: BoundedOwnerPath
    section: BoundedOwnerSection | None = None


class RuleContextBundle(StrictModel):
    """一次原子指令交付；完整性、正文和缺口必须一并检查。"""

    schema_version: Literal[2]
    build_id: Sha256
    index_sha256: Sha256
    node_id: NonEmptyString
    language: Language
    node_metadata: RuleContextNodeMetadata
    fragments: list[RuleContextFragmentResult]
    required_fragment_ids: list[NonEmptyString]
    missing_fragments: list[RuleContextMissingFragment]
    remaining_owner_refs: Annotated[list[RuleContextOwnerReference], Field(max_length=16)]
    remaining_owner_refs_truncated: bool
    complete: bool
    status: Literal["complete", "incomplete_budget", "incomplete_content"]
    text_budget: int
    text_characters: int
    required_text_characters: int
    context_hash: Sha256

"""Strict data contracts shared by rule loading and the storage foundation."""

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
    model_config = ConfigDict(extra="forbid", strict=True)


class CodingMode(StrEnum):
    SINGLE_AGENT = "Single-Agent Coding"
    MULTI_AGENT = "Multi-Agent Coding"


class ModeCount(StrictModel):
    mode: CodingMode
    child_count: Annotated[StrictInt, Field(ge=0)]

    @model_validator(mode="after")
    def validate_mode_count(self) -> ModeCount:
        if self.mode is CodingMode.SINGLE_AGENT and self.child_count != 0:
            raise ValueError("Single-Agent Coding requires child_count=0")
        if self.mode is CodingMode.MULTI_AGENT and self.child_count < 1:
            raise ValueError("Multi-Agent Coding requires a positive child_count")
        return self


class SchemaVersion(StrictModel):
    value: Annotated[StrictInt, Field(ge=1)]


class Revision(StrictModel):
    value: Annotated[StrictInt, Field(ge=0)]


class ImplementationContentEpoch(StrictModel):
    value: Annotated[StrictInt, Field(ge=0)]


class DocumentationEpoch(StrictModel):
    value: Annotated[StrictInt, Field(ge=0)]


class GitMetadataEpoch(StrictModel):
    value: Annotated[StrictInt, Field(ge=0)]


Sha256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class SemanticRef(StrictModel):
    uri: NonEmptyString
    content_hash: Sha256


class EvidenceRef(StrictModel):
    uri: NonEmptyString
    content_hash: Sha256
    evidence_id: NonEmptyString | None = None


class JudgmentUnknown(StrictModel):
    status: Literal["unknown"]


class JudgmentMissingEvidence(StrictModel):
    status: Literal["missing_evidence"]
    required_evidence: Annotated[list[NonEmptyString], Field(min_length=1)]


class JudgmentNotApplicable(StrictModel):
    status: Literal["not_applicable"]
    reason: NonEmptyString


class JudgmentDetermined(StrictModel):
    status: Literal["determined"]
    value: NonEmptyString
    evidence: list[EvidenceRef] = Field(default_factory=list)


Judgment: TypeAlias = Annotated[
    JudgmentUnknown | JudgmentMissingEvidence | JudgmentNotApplicable | JudgmentDetermined,
    Field(discriminator="status"),
]


class OwnerMirror(StrictModel):
    path: NonEmptyString
    section: NonEmptyString


EvaluationMode = Literal["direct", "deterministic", "semantic", "hybrid"]
Language = Literal["en", "zh_cn"]


class RuleNode(StrictModel):
    node_id: NonEmptyString
    owner_path: NonEmptyString
    owner_section: NonEmptyString
    owner_mirrors: dict[Literal["zh_cn"], OwnerMirror]
    required_facts: Annotated[list[NonEmptyString], Field(min_length=1)]
    required_evidence: list[NonEmptyString]
    legal_branches: Annotated[list[NonEmptyString], Field(min_length=1)]
    evaluation_mode: EvaluationMode
    failure_action: NonEmptyString
    next_checkpoint_ids: list[NonEmptyString]
    resource_paths: dict[Language, NonEmptyString] = Field(default_factory=dict)

    @field_validator("owner_path", "owner_section")
    @classmethod
    def strip_owner_fields(cls, value: str) -> str:
        return value.strip()


class RuleRegistry(StrictModel):
    contract_version: StrictInt
    nodes: Annotated[list[RuleNode], Field(min_length=1)]

    @model_validator(mode="after")
    def unique_node_ids(self) -> RuleRegistry:
        ids = [node.node_id for node in self.nodes]
        if len(ids) != len(set(ids)):
            raise ValueError("node_id values must be unique")
        known = set(ids)
        unknown = {
            successor
            for node in self.nodes
            for successor in node.next_checkpoint_ids
            if successor not in known
        }
        if unknown:
            raise ValueError(f"unknown next_checkpoint_ids: {sorted(unknown)}")
        return self


class RuleContext(StrictModel):
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


class DatabaseKind(StrEnum):
    WORKFLOW = "workflow"
    WORKER = "worker"


class SchemaStatus(StrictModel):
    exists: bool
    database_kind: DatabaseKind | None
    current_version: Annotated[StrictInt, Field(ge=0)]
    target_version: Annotated[StrictInt, Field(ge=1)]
    pending_versions: list[Annotated[StrictInt, Field(ge=1)]]
    compatible: bool
    reason: NonEmptyString | None = None

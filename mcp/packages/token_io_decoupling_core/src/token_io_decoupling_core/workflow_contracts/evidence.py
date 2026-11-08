"""检查点事实、证据提交及规范输入摘要。"""

from __future__ import annotations

import hashlib
import json
from typing import Annotated, Literal, TypeAlias

from pydantic import (
    Field,
    StrictBool,
    StrictInt,
    StrictStr,
    StringConstraints,
    model_validator,
)

from token_io_decoupling_core.models import Sha256, StrictModel

from .vocabulary import ActiveCheckpointNode, EpochDimension, EvidenceKind, FactKey, LegalBranch


class FactUnknown(StrictModel):
    status: Literal["unknown"]


CheckpointReferenceText = Annotated[
    StrictStr, StringConstraints(strip_whitespace=True, min_length=1, max_length=512)
]


CheckpointEvidenceId = Annotated[
    StrictStr, StringConstraints(strip_whitespace=True, min_length=1, max_length=128)
]


CheckpointRequestId = Annotated[
    StrictStr, StringConstraints(strip_whitespace=True, min_length=1, max_length=128)
]


class CheckpointSemanticRef(StrictModel):
    uri: CheckpointReferenceText
    content_hash: Sha256


class CheckpointEvidenceRef(StrictModel):
    uri: CheckpointReferenceText
    content_hash: Sha256
    evidence_id: CheckpointEvidenceId | None = None


class FactMissingEvidence(StrictModel):
    status: Literal["missing_evidence"]
    required_evidence: Annotated[list[CheckpointReferenceText], Field(min_length=1, max_length=16)]


class FactNotApplicable(StrictModel):
    status: Literal["not_applicable"]
    reason: CheckpointSemanticRef


class TypedEvidenceReference(StrictModel):
    kind: EvidenceKind
    reference: CheckpointEvidenceRef


class EnumFactValue(StrictModel):
    kind: Literal["enum"]
    value: LegalBranch


class BooleanFactValue(StrictModel):
    kind: Literal["boolean"]
    value: StrictBool


class CountFactValue(StrictModel):
    kind: Literal["count"]
    value: Annotated[StrictInt, Field(ge=0)]


class ReferenceFactValue(StrictModel):
    kind: Literal["semantic_ref"]
    value: CheckpointSemanticRef


TypedFactValue: TypeAlias = Annotated[
    EnumFactValue | BooleanFactValue | CountFactValue | ReferenceFactValue,
    Field(discriminator="kind"),
]


class FactDetermined(StrictModel):
    status: Literal["determined"]
    value: TypedFactValue
    evidence: Annotated[list[TypedEvidenceReference], Field(max_length=16)] = Field(
        default_factory=list
    )


FactJudgment: TypeAlias = Annotated[
    FactUnknown | FactMissingEvidence | FactNotApplicable | FactDetermined,
    Field(discriminator="status"),
]


class CheckpointFact(StrictModel):
    fact_key: FactKey
    judgment: FactJudgment

    @model_validator(mode="after")
    def validate_key_contract(self) -> CheckpointFact:
        optional = {
            FactKey.LOCKED_CHILD_COUNT,
            FactKey.ALLOCATION_ROLE,
            FactKey.WORKER_IDENTITY,
            FactKey.UNAVAILABLE_CONTEXT,
            FactKey.EVIDENCE_REQUEST_STATUS,
            FactKey.DOCUMENTATION_CHECKS,
            FactKey.UPDATED_EPOCH_STATE,
        }
        if self.judgment.status == "not_applicable" and self.fact_key not in optional:
            raise ValueError(f"{self.fact_key.value} cannot be marked not_applicable")
        if self.judgment.status != "determined":
            return self
        value = self.judgment.value
        expected_kind = {
            FactKey.LOCKED_CHILD_COUNT: "count",
            FactKey.CAPABILITY_GATE_RESULT: "boolean",
            FactKey.CURRENT_IMPLEMENTATION_EPOCH: "count",
            FactKey.AFFECTED_VERIFICATION_EPOCH: "count",
            FactKey.AFFECTED_DOCUMENTATION_EPOCH: "count",
            FactKey.CURRENT_GIT_EPOCH: "count",
            FactKey.VALID_MODE_DECISION: "enum",
            FactKey.PROGRESS_SIGNAL: "enum",
            FactKey.CURRENT_SLICE_OUTCOME: "enum",
            FactKey.TASK_TYPE: "enum",
            FactKey.REQUESTED_OUTPUT_CLASS: "enum",
            FactKey.CHANGED_DIMENSIONS: "enum",
            FactKey.AFFECTED_COVERAGE: "enum",
        }.get(self.fact_key, "semantic_ref")
        if expected_kind is not None and value.kind != expected_kind:
            raise ValueError(f"{self.fact_key.value} requires a {expected_kind} value")
        if self.fact_key is FactKey.VALID_MODE_DECISION:
            if value.kind != "enum" or value.value not in {
                LegalBranch.SINGLE_AGENT,
                LegalBranch.MULTI_AGENT,
            }:
                raise ValueError("valid mode decision must be single-agent or multi-agent")
        allowed_enums = {
            FactKey.PROGRESS_SIGNAL: {
                LegalBranch.CONTINUE,
                LegalBranch.AMEND,
                LegalBranch.STOP,
                LegalBranch.EVIDENCE_ON_DEMAND,
                LegalBranch.REPAIR,
                LegalBranch.BLOCKED,
            },
            FactKey.CURRENT_SLICE_OUTCOME: {
                LegalBranch.PASS,
                LegalBranch.FAILURE,
                LegalBranch.INCONCLUSIVE,
                LegalBranch.COMPLETE,
                LegalBranch.BLOCKED,
            },
            FactKey.TASK_TYPE: {
                LegalBranch.CODING,
                LegalBranch.NOT_CODING,
                LegalBranch.UNCLEAR,
            },
            FactKey.REQUESTED_OUTPUT_CLASS: {
                LegalBranch.CODE_CONFIGURATION,
                LegalBranch.SKILL_INSTRUCTIONS,
                LegalBranch.ORDINARY_DOCUMENTATION,
                LegalBranch.OTHER,
                LegalBranch.UNKNOWN,
            },
            FactKey.CHANGED_DIMENSIONS: {
                LegalBranch.IMPLEMENTATION_DIMENSION,
                LegalBranch.DOCUMENTATION_DIMENSION,
                LegalBranch.GIT_DIMENSION,
                LegalBranch.MULTIPLE,
                LegalBranch.NONE,
            },
            FactKey.AFFECTED_COVERAGE: {
                LegalBranch.IMPLEMENTATION_DIMENSION,
                LegalBranch.DOCUMENTATION_DIMENSION,
                LegalBranch.GIT_DIMENSION,
                LegalBranch.MULTIPLE,
                LegalBranch.NONE,
            },
        }
        allowed = allowed_enums.get(self.fact_key)
        if allowed is not None and (value.kind != "enum" or value.value not in allowed):
            raise ValueError(f"{self.fact_key.value} has an unsupported enum value")
        return self


class EvidenceSubmission(StrictModel):
    """Bounded caller-supplied evidence for one stateless checkpoint evaluation."""

    node_id: ActiveCheckpointNode
    facts: Annotated[list[CheckpointFact], Field(min_length=1, max_length=128)]
    evidence_refs: Annotated[list[TypedEvidenceReference], Field(max_length=128)] = Field(
        default_factory=list
    )
    coverage_dimensions: Annotated[list[EpochDimension], Field(max_length=3)] = Field(
        default_factory=list
    )
    input_hash: Sha256 | None = None
    evidence_request_id: CheckpointRequestId | None = None

    @model_validator(mode="after")
    def validate_conditional_not_applicable(self) -> EvidenceSubmission:
        if len(_canonical_submission_json(self)) > MAX_EVIDENCE_SUBMISSION_BYTES:
            raise ValueError("evidence_submission_exceeds_32_kib")
        fact_keys = [item.fact_key for item in self.facts]
        if len(set(fact_keys)) != len(fact_keys):
            raise ValueError("evidence submission fact keys must be unique")
        facts = {item.fact_key: item.judgment for item in self.facts}
        count = facts.get(FactKey.LOCKED_CHILD_COUNT)
        if count is not None and count.status == "not_applicable":
            mode = facts.get(FactKey.VALID_MODE_DECISION)
            if (
                mode is None
                or mode.status != "determined"
                or mode.value.kind != "enum"
                or mode.value.value is not LegalBranch.SINGLE_AGENT
            ):
                raise ValueError(
                    "locked child count is not applicable only for an explicit Single-Agent mode"
                )
        return self


MAX_EVIDENCE_SUBMISSION_BYTES = 32 * 1024


def _canonical_submission_json(submission: EvidenceSubmission) -> bytes:
    normalized = submission.model_dump(mode="json", exclude={"input_hash"})
    return json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )


def checkpoint_submission_source_input_hash(submission: EvidenceSubmission) -> str:
    return hashlib.sha256(_canonical_submission_json(submission)).hexdigest()

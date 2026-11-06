"""Workflow rule and caller-binding contracts without persisted run state."""

from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from typing import Annotated, Literal, TypeAlias

from pydantic import (
    AfterValidator,
    Field,
    StrictBool,
    StrictInt,
    StrictStr,
    StringConstraints,
    WithJsonSchema,
    model_validator,
)

from token_io_decoupling_core.models import NonEmptyString, Sha256, StrictModel


class SessionRole(StrEnum):
    PARENT = "parent"
    WORKER = "worker"


class HostCapability(StrEnum):
    WORKER_WRITE = "worker_write"


class HostGuard(StrEnum):
    IDENTITY_BOUND = "identity_bound"
    SESSION_BOUND = "session_bound"
    PATH_BOUNDARY = "path_boundary"
    PARENT_CHILD_RELATION = "parent_child_relation"


class OutputClass(StrEnum):
    CODE_CONFIGURATION = "code_configuration"
    SKILL_INSTRUCTIONS = "skill_instructions"
    ORDINARY_DOCUMENTATION = "ordinary_documentation"
    OTHER = "other"
    UNKNOWN = "unknown"


class AllocationRole(StrEnum):
    PRIMARY_OUTPUT = "Primary Output"
    CHANGE_VERIFICATION = "Change Verification"
    CONTEXT_BOOTSTRAP_REFRESH = "Context Bootstrap/Refresh"
    DOCUMENTATION_COMMENTS_GIT = "Documentation/Comments & Git Operations"


class CheckpointNode(StrEnum):
    CONTRACT = "contract"
    ENVIRONMENT = "environment"
    MODE = "mode"
    CONTEXT = "context"
    DECISION = "decision"
    SLICE = "slice"
    DELEGATION = "delegation"
    IMPLEMENTATION = "implementation"
    CONTROL = "control"
    VERIFICATION = "verification"
    REPAIR = "repair"
    REPAIR_SCOPE = "repair_scope"
    REPAIR_EXECUTION = "repair_execution"
    REPAIR_HANDOFF = "repair_handoff"
    DOCUMENTATION = "documentation"
    GIT = "git"
    ACCEPTANCE = "acceptance"
    TASK_INTENT = "task_intent"
    OUTPUT_CLASS = "output_class"
    CONTRACT_CHANGE = "contract_change"
    VERIFICATION_IMPACT = "verification_impact"


def _reject_retired_environment_checkpoint(node_id: CheckpointNode) -> CheckpointNode:
    if node_id is CheckpointNode.ENVIRONMENT:
        raise ValueError("environment is not an active checkpoint")
    return node_id


ActiveCheckpointNode: TypeAlias = Annotated[
    CheckpointNode,
    AfterValidator(_reject_retired_environment_checkpoint),
    WithJsonSchema(
        {
            "type": "string",
            "enum": [
                node.value for node in CheckpointNode if node is not CheckpointNode.ENVIRONMENT
            ],
        }
    ),
]


class FactKey(StrEnum):
    TASK_OBJECTIVE = "task objective"
    AUTHORIZED_SCOPE = "authorized scope"
    CONSTRAINTS = "constraints"
    ACCEPTANCE_CONDITIONS = "acceptance conditions"
    RUNTIME_IDENTITY = "runtime identity"
    REQUIRED_CAPABILITIES = "required capabilities"
    AVAILABLE_CAPABILITIES = "available capabilities"
    VALID_MODE_DECISION = "valid mode decision"
    LOCKED_CHILD_COUNT = "locked child-count budget when applicable"
    CAPABILITY_GATE_RESULT = "capability gate result"
    NEEDED_PROJECT_CONTEXT = "needed project context"
    SOURCE_SCOPE = "source scope"
    UNAVAILABLE_CONTEXT = "unavailable context"
    DECISION_QUESTION = "decision question"
    AVAILABLE_OPTIONS = "available options"
    DECISION_CONSEQUENCES = "decision consequences"
    SLICE_OBJECTIVE = "objective"
    SLICE_AUTHORIZED_SCOPE = "authorized scope and mutations"
    RETURN_CONDITIONS = "return conditions"
    UNRELEASED_BOUNDARY = "unreleased boundary"
    DELEGATION_MODE_COUNT = "locked mode/count"
    ALLOCATION_ROLE = "allocation identity and role when applicable"
    RELEASED_SLICE = "released slice"
    WORKER_IDENTITY = "worker identity binding when applicable"
    RELEASED_OBJECTIVE = "released objective"
    AUTHORIZED_MUTATION_SCOPE = "authorized mutation scope"
    CURRENT_UNRELEASED_BOUNDARY = "current unreleased boundary"
    PROGRESS_SIGNAL = "Progress Signal"
    EVIDENCE_REQUEST_STATUS = "evidence request status when applicable"
    CURRENT_SLICE_OUTCOME = "current slice outcome"
    CURRENT_IMPLEMENTATION_EPOCH = "current implementation/content epoch"
    VERIFICATION_SCOPE = "applicable verification scope"
    CLASSIFIED_FAILURE = "classified failure"
    AFFECTED_REPAIR_PATHS = "affected repair paths"
    REPAIR_DIAGNOSIS = "repair diagnosis or blocker"
    AUTHORIZED_REPAIR_SCOPE = "authorized repair scope"
    AFFECTED_VERIFICATION_EPOCH = "affected verification epoch"
    DOCUMENTATION_SCOPE = "documentation scope"
    AFFECTED_DOCUMENTATION_EPOCH = "affected documentation epoch"
    DOCUMENTATION_CHECKS = "documentation and link checks when applicable"
    UPDATED_EPOCH_STATE = "updated epoch state"
    AUTHORIZED_GIT_EFFECTS = "authorized Git effects"
    CURRENT_GIT_EPOCH = "current Git metadata epoch"
    VERIFIED_FINGERPRINTS = "latest verified content fingerprints"
    READ_ONLY_GIT_STATE = "read-only Git state and diff"
    CHECKPOINT_OUTCOMES = "all applicable checkpoint outcomes"
    CURRENT_AFFECTED_EPOCHS = "current affected epochs"
    REMAINING_LIMITATIONS = "remaining limitations"
    REQUIRED_VERIFICATION = "latest required verification and completion evidence"
    USER_REQUESTED_OUTCOME = "user-requested outcome"
    TASK_TYPE = "task type"
    CURRENT_DIRECTIVE = "current user directive"
    REQUESTED_OUTPUT_CLASS = "requested output class"
    REQUIRED_DELIVERABLES = "required files or deliverables"
    DELEGATION_BOUNDARY = "delegation boundary"
    CURRENT_CONTRACT = "current Contract"
    PROPOSED_CHANGE = "proposed change to objective, scope, constraints, or acceptance"
    NEW_MATERIAL_FACT = "new material fact or user direction"
    CHANGED_DIMENSIONS = "changed state dimensions"
    AFFECTED_COVERAGE = "coverage affected by the change"
    CHANGE_SUMMARY = "change summary"


class EpochDimension(StrEnum):
    IMPLEMENTATION_CONTENT = "implementation_content"
    DOCUMENTATION = "documentation"
    GIT_METADATA = "git_metadata"


class LegalBranch(StrEnum):
    READY = "ready"
    AMEND = "amend"
    BLOCKED = "blocked"
    AVAILABLE = "available"
    PARTIALLY_UNAVAILABLE = "partially unavailable"
    SINGLE_AGENT = "single-agent"
    MULTI_AGENT = "multi-agent"
    SUFFICIENT = "sufficient"
    REQUEST_EVIDENCE = "request evidence"
    DECIDED = "decided"
    EVIDENCE_ON_DEMAND = "evidence-on-demand"
    RELEASED = "released"
    STOP = "stop"
    NOT_APPLICABLE = "not applicable"
    RESERVED = "reserved"
    BOUND = "bound"
    COMPLETE = "complete"
    RETURN_FOR_CONTROL = "return for control"
    PASS = "pass"
    FAILURE = "failure"
    INCONCLUSIVE = "inconclusive"
    REPAIR = "repair"
    NO_GIT_EFFECT = "no Git effect"
    AUTHORIZED_EFFECT = "authorized effect"
    INCOMPLETE = "incomplete"
    CODING = "coding"
    NOT_CODING = "not coding"
    UNCLEAR = "unclear"
    CODE_CONFIGURATION = "code_configuration"
    SKILL_INSTRUCTIONS = "skill_instructions"
    ORDINARY_DOCUMENTATION = "ordinary_documentation"
    OTHER = "other"
    UNKNOWN = "unknown"
    UNCHANGED = "unchanged"
    IMPLEMENTATION_DIMENSION = "implementation/content"
    DOCUMENTATION_DIMENSION = "documentation"
    GIT_DIMENSION = "Git metadata"
    MULTIPLE = "multiple"
    NONE = "none"
    CONTINUE = "continue"


class EvidenceKind(StrEnum):
    USER_DIRECTIVE = "user or trusted directive"
    EXPLICIT_TASK_CONSTRAINTS = "explicit task constraints"
    SESSION_METADATA = "session metadata"
    EXPOSED_CAPABILITY_INVENTORY = "exposed capability inventory"
    PARENT_MODE_RECORD = "parent-controlled mode/count record"
    DIRECT_OWNER_REFERENCES = "direct owner references"
    BOUNDED_PROJECT_EVIDENCE = "bounded project evidence"
    DECISION_BRIEF = "Decision Brief or equivalent decision evidence"
    PARENT_SLICE_RELEASE = "parent release for this bounded slice"
    CANONICAL_PARENT_RECORD = "canonical parent record"
    TRUSTED_CHILD_IDENTITY = "trusted child identity evidence when applicable"
    SLICE_RELEASE = "slice release"
    IMPLEMENTATION_RESULT = "implementation result or blocker"
    CURRENT_SLICE_OUTCOME = "current slice outcome"
    RETURNED_EVIDENCE = "evidence returned for any request"
    IMPLEMENTATION_EPOCH = "current implementation/content epoch"
    VERIFICATION_RESULTS = "current-epoch verification results"
    REPAIR_AUTHORIZATION = "repair authorization"
    FAILURE_EVIDENCE = "failure evidence"
    REPAIR_DIAGNOSIS = "repair diagnosis or blocker"
    REPAIR_HANDOFF = "repair verification handoff"
    REPAIR_RESULT = "repair result"
    REVERIFICATION = "re-verification for changed coverage"
    DOCUMENTATION_CHECKS = "documentation and link checks when applicable"
    UPDATED_EPOCH = "updated epoch state"
    READ_ONLY_GIT_STATE = "read-only Git state and diff"
    VERIFIED_FINGERPRINTS = "staged/committed content match when applicable"
    REQUIRED_COMPLETION = "latest required verification and completion evidence"
    CURRENT_DIRECTIVE = "current user directive"
    CURRENT_CONTRACT = "current Contract"
    NEW_FACT_OR_DIRECTION = "new material fact or user direction"
    CHANGE_SUMMARY = "change summary"
    LATEST_VERIFICATION = "latest applicable verification evidence"


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


class BindingIdentity(StrictModel):
    project_id: NonEmptyString
    root_session_id: NonEmptyString
    current_session_id: NonEmptyString
    role: SessionRole
    capabilities: frozenset[HostCapability]
    guards: frozenset[HostGuard]
    parent_session_id: NonEmptyString | None = None

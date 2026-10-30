"""Strict contracts for deterministic Root and Worker state operations."""

from __future__ import annotations

from datetime import datetime, timedelta
from enum import StrEnum
from typing import Annotated, Literal, TypeAlias

from pydantic import (
    AfterValidator,
    Field,
    StrictBool,
    StrictInt,
    WithJsonSchema,
    model_validator,
)

from token_io_decoupling_core.models import (
    EvidenceRef,
    ModeCount,
    NonEmptyString,
    SemanticRef,
    Sha256,
    StrictModel,
)


class ModeSource(StrEnum):
    EXPLICIT = "explicit"
    DEFAULT = "default"
    LEGACY_TIMEOUT_DEFAULT = "timeout-default"


class SessionRole(StrEnum):
    PARENT = "parent"
    WORKER = "worker"


class HostCapability(StrEnum):
    WORKFLOW_READ = "workflow_read"
    WORKFLOW_WRITE = "workflow_write"
    WORKER_READ = "worker_read"
    WORKER_WRITE = "worker_write"
    WORKER_STORE_CREATE = "worker_store_create"
    CHILD_IDENTITY_CHECK = "child_identity_check"
    PARENT_SUMMARY_READ = "parent_summary_read"


class HostGuard(StrEnum):
    IDENTITY_BOUND = "identity_bound"
    SESSION_BOUND = "session_bound"
    PATH_BOUNDARY = "path_boundary"
    PARENT_CHILD_RELATION = "parent_child_relation"
    WORKER_STORE_ISOLATION = "worker_store_isolation"


class OutputClass(StrEnum):
    CODE_CONFIGURATION = "code_configuration"
    SKILL_INSTRUCTIONS = "skill_instructions"
    ORDINARY_DOCUMENTATION = "ordinary_documentation"
    OTHER = "other"
    UNKNOWN = "unknown"


class AllocationStatus(StrEnum):
    UNASSIGNED = "unassigned"
    RESERVED = "reserved"
    BOUND = "bound"
    INITIALIZED = "initialized"


class AllocationRole(StrEnum):
    PRIMARY_OUTPUT = "Primary Output"
    CHANGE_VERIFICATION = "Change Verification"
    CONTEXT_BOOTSTRAP_REFRESH = "Context Bootstrap/Refresh"
    DOCUMENTATION_COMMENTS_GIT = "Documentation/Comments & Git Operations"


class DelegationBudgetApproval(StrictModel):
    """Root-reviewed evidence for adding one different-role child slot."""

    requested_child_count: Annotated[StrictInt, Field(ge=2, le=4)]
    user_approval: SemanticRef | EvidenceRef

    @model_validator(mode="after")
    def approval_reference_is_nonblank(self) -> DelegationBudgetApproval:
        if not self.user_approval.uri.strip():
            raise ValueError("user_approval.uri must not be blank")
        return self


class DelegationUnreserveRequest(StrictModel):
    """Root attestation for releasing a reserved allocation before creation starts."""

    allocation_id: NonEmptyString
    creation_not_started: StrictBool
    creation_not_started_reference: SemanticRef | EvidenceRef
    expected_revision: Annotated[StrictInt, Field(ge=0)]
    idempotency_key: NonEmptyString

    @model_validator(mode="after")
    def creation_attestation_is_true(self) -> DelegationUnreserveRequest:
        if self.creation_not_started is not True:
            raise ValueError("creation_not_started must be true")
        return self


class ChangeCategory(StrEnum):
    SOURCE_CODE = "source_code"
    CONFIGURATION = "configuration"
    TESTS = "tests"
    SKILL_INSTRUCTIONS = "skill_instructions"


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


class FactMissingEvidence(StrictModel):
    status: Literal["missing_evidence"]
    required_evidence: Annotated[list[NonEmptyString], Field(min_length=1)]


class FactNotApplicable(StrictModel):
    status: Literal["not_applicable"]
    reason: SemanticRef


class TypedEvidenceReference(StrictModel):
    kind: EvidenceKind
    reference: EvidenceRef


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
    value: SemanticRef


TypedFactValue: TypeAlias = Annotated[
    EnumFactValue | BooleanFactValue | CountFactValue | ReferenceFactValue,
    Field(discriminator="kind"),
]


class FactDetermined(StrictModel):
    status: Literal["determined"]
    value: TypedFactValue
    evidence: list[TypedEvidenceReference] = Field(default_factory=list)


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
    node_id: ActiveCheckpointNode
    facts: Annotated[list[CheckpointFact], Field(min_length=1)]
    evidence_refs: list[TypedEvidenceReference] = Field(default_factory=list)
    coverage_dimensions: list[EpochDimension] = Field(default_factory=list)
    input_hash: Sha256
    evidence_request_id: NonEmptyString | None = None

    @model_validator(mode="after")
    def validate_conditional_not_applicable(self) -> EvidenceSubmission:
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


class EpochSnapshot(StrictModel):
    implementation_content: Annotated[StrictInt, Field(ge=0)]
    documentation: Annotated[StrictInt, Field(ge=0)]
    git_metadata: Annotated[StrictInt, Field(ge=0)]


class EvidenceRecord(StrictModel):
    evidence_id: NonEmptyString
    node_id: CheckpointNode
    facts: list[CheckpointFact]
    evidence_refs: list[TypedEvidenceReference]
    coverage_dimensions: list[EpochDimension]
    input_hash: Sha256
    rule_hash: Sha256
    epochs: EpochSnapshot
    basis_revision: Annotated[StrictInt, Field(ge=0)]
    recorded_revision: Annotated[StrictInt, Field(ge=1)]
    stale: StrictBool


class CheckpointEvaluation(StrictModel):
    evaluation_id: NonEmptyString
    node_id: CheckpointNode
    outcome: Literal["ready", "incomplete", "blocked", "evidence_on_demand"]
    branch: LegalBranch | None
    rule_hash: Sha256
    input_hash: Sha256
    epochs: EpochSnapshot
    basis_revision: Annotated[StrictInt, Field(ge=0)]
    result_revision: Annotated[StrictInt, Field(ge=1)]
    missing_facts: list[FactKey]
    missing_evidence: list[NonEmptyString]
    slice_ids: list[NonEmptyString] = Field(default_factory=list)
    evidence_request_id: NonEmptyString | None = None
    stale: StrictBool = False


class ControlTransitionRequest(StrictModel):
    kind: Literal["control"]
    evaluation_id: NonEmptyString
    outcome: Literal["continue", "amend", "stop"]
    expected_revision: Annotated[StrictInt, Field(ge=0)]
    idempotency_key: NonEmptyString
    amended_contract: SemanticRef | None = None
    slice_ids: list[NonEmptyString] = Field(default_factory=list)


class EpochAdvanceTransition(StrictModel):
    kind: Literal["advance_epoch"]
    dimension: EpochDimension
    expected_revision: Annotated[StrictInt, Field(ge=0)]
    idempotency_key: NonEmptyString


class CheckpointConfirmationTransition(StrictModel):
    kind: Literal["confirm_checkpoint"]
    evaluation_id: NonEmptyString
    expected_revision: Annotated[StrictInt, Field(ge=0)]
    idempotency_key: NonEmptyString


class SessionAuditPrompt(StrictModel):
    status: Literal["unasked", "pending", "answered", "timed_out", "unavailable", "reused"]
    prompted_at: datetime | None
    deadline_at: datetime | None
    response_at: datetime | None
    resolution: Literal[
        "startup_explicit",
        "prior_record",
        "question_reply",
        "question_reply_after_timeout",
        "timeout_default",
        "awaiting_input",
        "unavailable",
    ]

    @model_validator(mode="after")
    def validate_observed_utc_times(self) -> SessionAuditPrompt:
        times = (self.prompted_at, self.deadline_at, self.response_at)
        if (self.prompted_at is None) != (self.deadline_at is None):
            raise ValueError("prompted_at and deadline_at must be recorded together")
        if self.response_at is not None and self.prompted_at is None:
            raise ValueError("response_at requires an observed prompt")
        for value in times:
            if value is not None and (value.tzinfo is None or value.utcoffset() != timedelta(0)):
                raise ValueError("prompt timestamps must be actual UTC-aware timestamps")
        if (
            self.prompted_at is not None
            and self.deadline_at is not None
            and self.deadline_at < self.prompted_at
        ):
            raise ValueError("deadline_at cannot precede prompted_at")
        if (
            self.prompted_at is not None
            and self.response_at is not None
            and self.response_at < self.prompted_at
        ):
            raise ValueError("response_at cannot precede prompted_at")
        if self.status == "pending" and (self.prompted_at is None or self.response_at is not None):
            raise ValueError("pending prompt requires a prompt and no response")
        if self.status == "answered" and self.response_at is None:
            raise ValueError("answered prompt requires an observed response time")
        if self.resolution == "timeout_default" and self.status != "timed_out":
            raise ValueError("timeout_default resolution requires timed_out status")
        return self


class SessionAuditSources(StrictModel):
    audit_mode: Literal["explicit", "default"]
    root_reasoning_cadence: Literal["explicit", "default"]
    worker_reasoning_cadence: Literal["explicit", "default"]


class SessionAudit(StrictModel):
    audit_mode: Literal["economy", "balanced", "full"]
    root_reasoning_cadence: Literal["full", "milestone_only", "off"]
    worker_reasoning_cadence: Literal["full", "milestone_only", "off"]
    source: SessionAuditSources
    worker_log_visibility: Literal["available", "unverified", "unavailable", "Not applicable"]
    worker_log_evidence: EvidenceRef | None
    audit_config_prompt: SessionAuditPrompt
    revision: Literal["session-audit/v2"]

    @model_validator(mode="after")
    def validate_worker_log_evidence(self) -> SessionAudit:
        if self.worker_log_visibility in {"available", "unavailable", "Not applicable"}:
            if self.worker_log_evidence is None:
                raise ValueError("worker-log claims require an evidence reference")
        return self


class SessionAuditTransition(StrictModel):
    kind: Literal["session_audit"]
    session_audit: SessionAudit
    expected_revision: Annotated[StrictInt, Field(ge=0)]
    idempotency_key: NonEmptyString


class NativeReconcileTransition(StrictModel):
    kind: Literal["confirm_native_reconcile"]
    snapshot: NativeWorkflowSnapshot
    expected_revision: Annotated[StrictInt, Field(ge=0)]
    idempotency_key: NonEmptyString


class NativeReconcileResolutionTransition(StrictModel):
    kind: Literal["resolve_native_reconcile"]
    canonical_reconcile_id: NonEmptyString
    snapshot_hash: Sha256
    unresolved_set_hash: Sha256
    choice: Literal["adopt_native_pair", "retain_sqlite_pair"]
    reviewed_native_revision: Annotated[StrictInt, Field(ge=0)]
    reviewed_native_epochs: EpochSnapshot
    root_decision_ref: EvidenceRef
    native_freshness_refs: Annotated[list[EvidenceRef], Field(min_length=1, max_length=256)]
    root_quiescence_refs: Annotated[list[EvidenceRef], Field(min_length=1, max_length=32)]
    expected_revision: Annotated[StrictInt, Field(ge=0)]
    idempotency_key: NonEmptyString


WorkflowTransitionRequest: TypeAlias = Annotated[
    ControlTransitionRequest
    | EpochAdvanceTransition
    | CheckpointConfirmationTransition
    | NativeReconcileTransition
    | NativeReconcileResolutionTransition
    | SessionAuditTransition,
    Field(discriminator="kind"),
]


class NativeAllocation(StrictModel):
    allocation_id: NonEmptyString
    role: AllocationRole | None
    worker_session_id: NonEmptyString | None
    status: AllocationStatus


class NativeWorkflowSnapshot(StrictModel):
    project_id: NonEmptyString
    root_session_id: NonEmptyString
    run_id: NonEmptyString | None
    mode_count: ModeCount
    mode_source: Literal["explicit", "default", "timeout-default"]
    lifecycle: Literal["pending", "running", "completed", "interrupted"]
    source: SemanticRef
    semantic_references: list[SemanticRef] = Field(default_factory=list)
    revision: Annotated[StrictInt, Field(ge=0)]
    allocations: list[NativeAllocation]
    epochs: EpochSnapshot
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)

    @model_validator(mode="after")
    def allocation_identities_are_unique(self) -> NativeWorkflowSnapshot:
        allocation_ids = [item.allocation_id for item in self.allocations]
        roles = [item.role for item in self.allocations if item.role is not None]
        worker_session_ids = [
            item.worker_session_id
            for item in self.allocations
            if item.worker_session_id is not None
        ]
        if len(allocation_ids) != len(set(allocation_ids)):
            raise ValueError("Native allocation IDs must be unique")
        if len(roles) != len(set(roles)):
            raise ValueError("Native allocation roles must be unique")
        if len(worker_session_ids) != len(set(worker_session_ids)):
            raise ValueError("Native child Session IDs must be unique")
        return self


NativeReconcileTransition.model_rebuild()


class ReconcileResult(StrictModel):
    reconcile_id: NonEmptyString
    status: Literal["matched", "conflict", "awaiting_confirmation"]
    observed_revision: Annotated[StrictInt, Field(ge=0)]
    result_revision: Annotated[StrictInt, Field(ge=1)]
    current_revision: Annotated[StrictInt, Field(ge=0)]
    differences: list[NonEmptyString]
    native_refs: list[EvidenceRef]
    replayed: StrictBool = False


class WorkflowOpenRequest(StrictModel):
    mode_count: ModeCount
    mode_source: Literal["explicit", "default"]
    source: SemanticRef
    semantic_references: list[SemanticRef] = Field(default_factory=list)
    expected_revision: Annotated[StrictInt, Field(ge=0)] = 0
    idempotency_key: NonEmptyString


class TrustedCapabilitySnapshot(StrictModel):
    project_id: NonEmptyString
    root_session_id: NonEmptyString
    current_session_id: NonEmptyString
    role: SessionRole
    parent_session_id: NonEmptyString | None
    capabilities: list[HostCapability]
    guards: list[HostGuard]
    snapshot_hash: Sha256
    observed_revision: Annotated[StrictInt, Field(ge=0)]


class ActiveSliceIndex(StrictModel):
    slice_id: NonEmptyString
    allocation_id: NonEmptyString | None
    output_class: OutputClass | None
    objective: SemanticRef
    return_conditions: SemanticRef
    unreleased_boundary: SemanticRef
    authorized_paths: list[NonEmptyString]
    change_categories: list[ChangeCategory]
    write_content_memo: StrictBool | None
    spec_hash: Sha256 | None
    spec_hash_unknown_reason: NonEmptyString | None

    @model_validator(mode="after")
    def validate_spec_hash_status(self) -> ActiveSliceIndex:
        if (self.spec_hash is None) == (self.spec_hash_unknown_reason is None):
            raise ValueError("provide either an exact Slice spec hash or its unknown reason")
        return self


RecoveryIndexCollection = Literal[
    "active_slices",
    "latest_gates",
    "unresolved_native_reconciliations",
    "native_resolution_history",
    "control_evidence_requests",
]


class RecoveryIndexCursor(StrictModel):
    collection: RecoveryIndexCollection
    revision: Annotated[StrictInt, Field(ge=0)]
    offset: Annotated[StrictInt, Field(ge=0)]
    page_size: Annotated[StrictInt, Field(ge=1, le=128)]


class RecoveryIndexPageRequest(StrictModel):
    collection: RecoveryIndexCollection
    cursor: RecoveryIndexCursor | None = None
    page_size: Annotated[StrictInt, Field(ge=1, le=128)] | None = None

    @model_validator(mode="after")
    def validate_cursor_request(self) -> RecoveryIndexPageRequest:
        if self.cursor is not None:
            if self.cursor.collection != self.collection:
                raise ValueError("recovery cursor collection does not match the requested index")
            if self.page_size is not None and self.page_size != self.cursor.page_size:
                raise ValueError("page_size cannot change while following a recovery cursor")
        return self


class RecoveryIndexPageInfo(StrictModel):
    collection: RecoveryIndexCollection
    revision: Annotated[StrictInt, Field(ge=0)]
    offset: Annotated[StrictInt, Field(ge=0)]
    page_size: Annotated[StrictInt, Field(ge=1, le=128)]
    total_count: Annotated[StrictInt, Field(ge=0)]
    returned_count: Annotated[StrictInt, Field(ge=0)]
    next_cursor: RecoveryIndexCursor | None


class GateIndex(StrictModel):
    node_id: NonEmptyString
    outcome: Literal["ready", "incomplete", "blocked", "evidence_on_demand"]
    branch: NonEmptyString | None
    rule_hash: Sha256
    input_hash: Sha256
    epochs: EpochSnapshot
    basis_revision: Annotated[StrictInt, Field(ge=0)]
    result_revision: Annotated[StrictInt, Field(ge=1)]
    rule_status: Literal["current", "stale", "unknown_node", "unavailable"]
    rule_current: bool
    epochs_current: bool
    revision_current: bool


class NativeReconcileIndex(StrictModel):
    reconcile_id: NonEmptyString
    status: Literal["matched", "conflict", "awaiting_confirmation"]
    snapshot_hash: Sha256
    native_refs: list[EvidenceRef] = Field(max_length=256)
    native_reference_count: Annotated[StrictInt, Field(ge=0)]
    native_references_omitted: Annotated[StrictInt, Field(ge=0)]
    differences: list[NonEmptyString]
    observed_revision: Annotated[StrictInt, Field(ge=0)]
    result_revision: Annotated[StrictInt, Field(ge=1)]
    native_revision: Annotated[StrictInt, Field(ge=0)]
    native_run_id: NonEmptyString | None
    native_mode_count: ModeCount
    native_mode_source: Literal["explicit", "default", "timeout-default"]
    native_lifecycle: Literal["pending", "running", "completed", "interrupted"]
    native_allocations: list[NativeAllocation] = Field(max_length=256)
    native_allocation_count: Annotated[StrictInt, Field(ge=0)]
    native_allocations_omitted: Annotated[StrictInt, Field(ge=0)]
    native_source: SemanticRef
    native_semantic_references: list[SemanticRef] = Field(max_length=256)
    native_semantic_reference_count: Annotated[StrictInt, Field(ge=0)]
    native_semantic_references_omitted: Annotated[StrictInt, Field(ge=0)]
    resolution_unavailable_reason: (
        Literal[
            "native_semantic_references_exceed_supported_bound",
            "native_allocations_exceed_supported_bound",
            "native_evidence_references_exceed_supported_bound",
        ]
        | None
    )
    native_epochs: EpochSnapshot
    preimage_known: StrictBool
    current: bool


class NativeResolutionTargetIndex(StrictModel):
    reconcile_id: NonEmptyString
    snapshot_hash: Sha256


class NativeResolutionIndex(StrictModel):
    resolution_id: NonEmptyString
    reconcile_id: NonEmptyString
    choice: Literal["adopt_native_pair", "retain_sqlite_pair"]
    reviewed_set_hash: Sha256
    snapshot_hash: Sha256
    resolved_comparisons: Annotated[list[NativeResolutionTargetIndex], Field(max_length=256)]
    root_decision_ref: EvidenceRef
    native_freshness_refs: list[EvidenceRef]
    root_quiescence_refs: list[EvidenceRef]
    result_revision: Annotated[StrictInt, Field(ge=1)]
    recovery_revision: Annotated[StrictInt, Field(ge=1)]
    current: StrictBool


class ControlEvidenceRequestIndex(StrictModel):
    request_id: NonEmptyString
    status: Literal["pending", "returned", "resolved"]
    created_revision: Annotated[StrictInt, Field(ge=0)]
    returned_revision: Annotated[StrictInt, Field(ge=0)] | None
    recovery_fresh: StrictBool


class WorkflowState(StrictModel):
    project_id: NonEmptyString
    root_session_id: NonEmptyString
    run_id: NonEmptyString
    mode_count: ModeCount
    mode_source: Literal["explicit", "default", "timeout-default"]
    source: SemanticRef
    semantic_references: list[SemanticRef]
    lifecycle: Literal["pending", "running", "completed", "interrupted"]
    revision: Annotated[int, Field(ge=0)]
    allocations: list[AllocationState]
    epochs: EpochSnapshot
    active_slices: list[ActiveSliceIndex] = Field(default_factory=list)
    omitted_active_slice_count: Annotated[StrictInt, Field(ge=0)] = 0
    latest_gates: list[GateIndex] = Field(default_factory=list)
    omitted_gate_count: Annotated[StrictInt, Field(ge=0)] = 0
    unresolved_native_reconciliations: list[NativeReconcileIndex] = Field(default_factory=list)
    omitted_native_reconciliation_count: Annotated[StrictInt, Field(ge=0)] = 0
    latest_native_reconciliation: NativeReconcileIndex | None = None
    unresolved_native_set_hash: Sha256 | None = None
    native_resolution_unavailable_reason: (
        Literal[
            "reviewed_comparison_set_exceeds_supported_bound",
            "native_semantic_references_exceed_supported_bound",
            "native_allocations_exceed_supported_bound",
            "native_evidence_references_exceed_supported_bound",
        ]
        | None
    ) = None
    recovery_revision: Annotated[StrictInt, Field(ge=0)] = 0
    native_resolution_history: list[NativeResolutionIndex] = Field(default_factory=list)
    omitted_native_resolution_count: Annotated[StrictInt, Field(ge=0)] = 0
    control_evidence_requests: list[ControlEvidenceRequestIndex] = Field(default_factory=list)
    omitted_control_evidence_request_count: Annotated[StrictInt, Field(ge=0)] = 0
    recovery_pages: list[RecoveryIndexPageInfo] = Field(default_factory=list)
    session_audit: SessionAudit | None = None
    capability_snapshot: TrustedCapabilitySnapshot | None = None
    capability_snapshot_current: bool | None = None


class AllocationState(StrictModel):
    allocation_id: NonEmptyString
    slot: Annotated[int, Field(ge=0)]
    role: NonEmptyString | None
    status: AllocationStatus
    worker_session_id: NonEmptyString | None
    output_class: OutputClass | None


WorkflowState.model_rebuild()


class MutationReceipt(StrictModel):
    operation: NonEmptyString
    payload_hash: Sha256
    result: dict[str, object]
    receipt_revision: Annotated[int, Field(ge=0)]
    current_revision: Annotated[int, Field(ge=0)]
    replayed: StrictBool


class SliceSpec(StrictModel):
    allocation_id: NonEmptyString
    output_class: OutputClass
    objective: SemanticRef
    return_conditions: SemanticRef
    unreleased_boundary: SemanticRef
    authorized_paths: list[NonEmptyString] = Field(min_length=1)
    change_categories: Annotated[list[ChangeCategory], Field(min_length=1)]
    write_content_memo: StrictBool


class SliceCheckResult(StrictModel):
    eligible: StrictBool
    reason: NonEmptyString | None = None
    allocation_id: NonEmptyString
    output_class: OutputClass
    input_hash: Sha256 = "0" * 64


class BindingIdentity(StrictModel):
    project_id: NonEmptyString
    root_session_id: NonEmptyString
    current_session_id: NonEmptyString
    role: SessionRole
    capabilities: frozenset[HostCapability]
    guards: frozenset[HostGuard]
    parent_session_id: NonEmptyString | None = None


class VerifiedChildBinding(StrictModel):
    project_id: NonEmptyString
    root_session_id: NonEmptyString
    parent_session_id: NonEmptyString
    child_session_id: NonEmptyString
    capabilities: frozenset[HostCapability]
    guards: frozenset[HostGuard]


class ProgressRecord(StrictModel):
    status: Literal["started", "in_progress", "reported_complete"]
    milestone: SemanticRef
    references: list[SemanticRef] = Field(default_factory=list)


class BlockerRecord(StrictModel):
    blocker_id: NonEmptyString
    reason: SemanticRef
    references: list[SemanticRef] = Field(default_factory=list)


class WorkerState(StrictModel):
    allocation_id: NonEmptyString
    worker_session_id: NonEmptyString
    role: NonEmptyString
    output_class: OutputClass
    revision: Annotated[int, Field(ge=0)]
    progress: list[ProgressRecord]
    blockers: list[BlockerRecord]


OperationName = Literal[
    "workflow_open",
    "delegation_reserve",
    "delegation_bind",
    "slice_release",
    "worker_record_progress",
    "worker_report_blocker",
]

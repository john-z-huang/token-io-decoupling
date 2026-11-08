"""会话绑定身份及工作流节点、事实和证据的枚举词汇。"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, TypeAlias

from pydantic import (
    AfterValidator,
    WithJsonSchema,
)

from token_io_decoupling_core.models import NonEmptyString, StrictModel


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


class BindingIdentity(StrictModel):
    project_id: NonEmptyString
    root_session_id: NonEmptyString
    current_session_id: NonEmptyString
    role: SessionRole
    capabilities: frozenset[HostCapability]
    guards: frozenset[HostGuard]
    parent_session_id: NonEmptyString | None = None

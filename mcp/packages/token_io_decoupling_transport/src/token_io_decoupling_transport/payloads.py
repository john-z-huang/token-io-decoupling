"""Strict wire payload models and their inline JSON schemas."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, StrictInt, StringConstraints, create_model, model_validator
from token_io_decoupling_core.models import NonEmptyString, StrictModel
from token_io_decoupling_core.state_models import (
    ActiveCheckpointNode,
    BlockerRecord,
    DelegationBudgetApproval,
    DelegationUnreserveRequest,
    EvidenceSubmission,
    NativeWorkflowSnapshot,
    ProgressRecord,
    RecoveryIndexPageRequest,
    SliceSpec,
    WorkflowTransitionRequest,
)


class ToolPayload(StrictModel):
    """Shared base for strict, extra-forbidden wire payload containers."""


def payload_model(name: str, **fields: Any) -> type[BaseModel]:
    return create_model(name, __base__=ToolPayload, **fields)


def inline_schema(model: type[BaseModel]) -> dict[str, Any]:
    schema = model.model_json_schema()
    definitions = schema.pop("$defs", {})

    def expand(value: Any) -> Any:
        if isinstance(value, dict):
            reference = value.get("$ref")
            if isinstance(reference, str) and reference.startswith("#/$defs/"):
                target = definitions[reference.rsplit("/", 1)[1]]
                siblings = {key: item for key, item in value.items() if key != "$ref"}
                return {**expand(target), **expand(siblings)}
            return {key: expand(item) for key, item in value.items()}
        if isinstance(value, list):
            return [expand(item) for item in value]
        return value

    return expand(schema)


_inline_schema = inline_schema


_NO_ARGUMENTS = payload_model("NoArguments")
_GET_STATE = payload_model("GetStatePayload", index_page=(RecoveryIndexPageRequest | None, None))
_RESERVE = payload_model(
    "ReservePayload",
    role=(NonEmptyString, ...),
    expected_revision=(int, ...),
    idempotency_key=(NonEmptyString, ...),
    budget_approval=(DelegationBudgetApproval | None, None),
)
_UNRESERVE = DelegationUnreserveRequest
_BIND = payload_model(
    "BindPayload",
    allocation_id=(NonEmptyString, ...),
    child_session_id=(NonEmptyString, ...),
    expected_revision=(int, ...),
    idempotency_key=(NonEmptyString, ...),
)
_SLICE = payload_model("SlicePayload", spec=(SliceSpec, ...))
_SLICE_RELEASE = payload_model(
    "SliceReleasePayload",
    spec=(SliceSpec, ...),
    expected_revision=(int, ...),
    idempotency_key=(NonEmptyString, ...),
)
_EVIDENCE = payload_model(
    "EvidencePayload",
    submission=(EvidenceSubmission, ...),
    expected_revision=(int, ...),
    idempotency_key=(NonEmptyString, ...),
)
_RECONCILE = payload_model(
    "ReconcilePayload",
    snapshot=(NativeWorkflowSnapshot, ...),
    confirm=(bool, False),
    expected_revision=(int, ...),
    idempotency_key=(NonEmptyString, ...),
)
_ALLOCATION = payload_model("AllocationPayload", allocation_id=(NonEmptyString, ...))
_EVIDENCE_ID = payload_model("EvidenceIdPayload", evidence_id=(NonEmptyString, ...))
_PROGRESS = payload_model(
    "ProgressPayload",
    record=(ProgressRecord, ...),
    expected_revision=(int, ...),
    idempotency_key=(NonEmptyString, ...),
)
_BLOCKER = payload_model(
    "BlockerPayload",
    blocker=(BlockerRecord, ...),
    expected_revision=(int, ...),
    idempotency_key=(NonEmptyString, ...),
)


class RuleContextPayload(ToolPayload):
    node_id: ActiveCheckpointNode
    language: Literal["en", "zh_cn"] = "en"
    context_version: Literal[1] | None = None
    fragment_ids: Annotated[
        list[Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=128)]]
        | None,
        Field(max_length=128),
    ] = None
    max_chars: Annotated[StrictInt, Field(ge=256, le=60_000)] | None = None

    @model_validator(mode="before")
    @classmethod
    def require_strict_context_version(cls, value: Any) -> Any:
        if isinstance(value, dict):
            version = value.get("context_version")
            if version is not None and (type(version) is not int or version != 1):
                raise ValueError("context_version must be the integer 1")
        return value

    @model_validator(mode="after")
    def require_explicit_context_version(self) -> RuleContextPayload:
        if self.context_version is None and (
            self.fragment_ids is not None or self.max_chars is not None
        ):
            raise ValueError("fragment_ids and max_chars require context_version=1")
        if self.fragment_ids is not None and len(self.fragment_ids) != len(set(self.fragment_ids)):
            raise ValueError("fragment_ids must not contain duplicates")
        return self


_RULE_CONTEXT = RuleContextPayload
_TRANSITION = payload_model("TransitionPayload", request=(WorkflowTransitionRequest, ...))

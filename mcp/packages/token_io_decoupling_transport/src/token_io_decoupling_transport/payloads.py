"""Strict wire payload models and their inline JSON schemas."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, create_model
from token_io_decoupling_core.models import NonEmptyString, StrictModel
from token_io_decoupling_core.state_models import (
    BlockerRecord,
    CheckpointNode,
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
)
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
_RULE_CONTEXT = payload_model(
    "RuleContextPayload",
    node_id=(CheckpointNode, ...),
    language=(Literal["en", "zh_cn"], "en"),
)
_TRANSITION = payload_model("TransitionPayload", request=(WorkflowTransitionRequest, ...))

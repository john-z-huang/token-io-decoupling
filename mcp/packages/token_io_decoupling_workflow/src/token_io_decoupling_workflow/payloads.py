"""API advisory payload models owned by the workflow feature."""

from __future__ import annotations

from token_io_decoupling_core.models import NonEmptyString
from token_io_decoupling_core.state_models import ActiveCheckpointNode, LegalBranch
from token_io_decoupling_transport.payloads import payload_model

from token_io_decoupling_workflow.decisions import DecisionAdvisoryInput

_EVALUATE = payload_model(
    "EvaluatePayload",
    node_id=(ActiveCheckpointNode, ...),
    expected_revision=(int, ...),
    idempotency_key=(NonEmptyString, ...),
    branch=(LegalBranch | None, None),
    input_hash=(str | None, None),
    slice_ids=(list[NonEmptyString] | None, None),
    semantic_input=(DecisionAdvisoryInput | None, None),
)
_CONTROL_EVALUATE = payload_model(
    "ControlEvaluatePayload",
    expected_revision=(int, ...),
    idempotency_key=(NonEmptyString, ...),
    branch=(LegalBranch | None, None),
    input_hash=(str | None, None),
    slice_ids=(list[NonEmptyString] | None, None),
    semantic_input=(DecisionAdvisoryInput | None, None),
)

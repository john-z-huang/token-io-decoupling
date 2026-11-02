"""API advisory payload models owned by the workflow feature."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, StringConstraints, model_validator
from token_io_decoupling_core.compliance_core import validate_candidate_list
from token_io_decoupling_core.models import NonEmptyString, StrictModel
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


class _AbsentBaseline(StrictModel):
    state: Literal["absent"]


class _Sha256Baseline(StrictModel):
    state: Literal["sha256"]
    value: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]


_CandidateBaseline = Annotated[
    _AbsentBaseline | _Sha256Baseline,
    Field(discriminator="state"),
]


class ComplianceCandidate(StrictModel):
    path: Annotated[str, StringConstraints(min_length=1, max_length=512)]
    operation: Literal["create", "replace", "delete"]
    baseline: _CandidateBaseline
    content: Annotated[str, StringConstraints(max_length=131_072)] | None = None


class ComplianceRequest(StrictModel):
    policy_scope: Literal["skill_maintenance", "generic_project"]
    candidates: Annotated[list[ComplianceCandidate], Field(min_length=1, max_length=64)]

    @model_validator(mode="after")
    def validate_candidate_contract(self) -> ComplianceRequest:
        try:
            validate_candidate_list(
                [candidate.model_dump(mode="python") for candidate in self.candidates]
            )
        except ValueError as exc:
            raise ValueError(str(exc)) from exc
        for candidate in self.candidates:
            state = candidate.baseline.state
            if candidate.operation == "create" and state != "absent":
                raise ValueError("create_requires_absent_baseline")
            if candidate.operation in {"replace", "delete"} and state != "sha256":
                raise ValueError("replace_delete_require_sha256_baseline")
            if candidate.operation == "delete" and candidate.content is not None:
                raise ValueError("delete_must_not_include_content")
            if candidate.operation != "delete" and candidate.content is None:
                raise ValueError("create_replace_require_content")
        return self


_COMPLIANCE_PREFLIGHT = payload_model(
    "CompliancePreflightPayload",
    request=(ComplianceRequest, ...),
)

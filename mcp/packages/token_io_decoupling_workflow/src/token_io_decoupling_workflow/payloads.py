"""API advisory payload models owned by the workflow feature."""

from __future__ import annotations

import json
from typing import Annotated, Literal

from pydantic import Field, StrictStr, StringConstraints, field_validator, model_validator

from token_io_decoupling_core.compliance_core import validate_candidate_list
from token_io_decoupling_core.models import Sha256, StrictModel
from token_io_decoupling_core.workflow_models import ActiveCheckpointNode, EvidenceSubmission
from token_io_decoupling_transport.payloads import payload_model
from token_io_decoupling_workflow.decisions import DecisionAdvisoryInput

MAX_CHECKPOINT_EVALUATION_REQUEST_BYTES = 32 * 1024
CheckpointFactKey = Annotated[StrictStr, StringConstraints(min_length=1, max_length=64)]
CheckpointFactText = Annotated[StrictStr, StringConstraints(min_length=1, max_length=1_024)]
CurrentFacts = Annotated[dict[CheckpointFactKey, CheckpointFactText], Field(max_length=16)]


class _CheckpointEvaluationPayload(StrictModel):
    submission: EvidenceSubmission
    language: Literal["en", "zh_cn"] = "en"
    expected_rule_hash: Sha256 | None = None
    semantic_input: DecisionAdvisoryInput | None = None
    current_facts: CurrentFacts = Field(default_factory=dict)

    @field_validator("current_facts")
    @classmethod
    def current_fact_strings_are_not_blank(cls, value: dict[str, str]) -> dict[str, str]:
        if any(not key.strip() or not fact.strip() for key, fact in value.items()):
            raise ValueError("current_facts keys and values must not be blank")
        return value

    @model_validator(mode="after")
    def total_request_is_bounded(self) -> _CheckpointEvaluationPayload:
        encoded = json.dumps(
            self.model_dump(mode="json"), ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        if len(encoded) > MAX_CHECKPOINT_EVALUATION_REQUEST_BYTES:
            raise ValueError("checkpoint_evaluation_request_exceeds_32_kib")
        return self


class EvaluatePayload(_CheckpointEvaluationPayload):
    node_id: ActiveCheckpointNode


class ControlEvaluatePayload(_CheckpointEvaluationPayload):
    pass


_EVALUATE = EvaluatePayload
_CONTROL_EVALUATE = ControlEvaluatePayload


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
    policy_scope: Literal["generic_project"]
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

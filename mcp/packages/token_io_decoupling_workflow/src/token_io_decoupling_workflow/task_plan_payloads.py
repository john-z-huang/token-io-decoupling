from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, StringConstraints, field_validator, model_validator
from token_io_decoupling_core.models import StrictModel

PlanId = Annotated[
    str,
    StringConstraints(
        min_length=1,
        max_length=64,
        pattern=r"^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$",
    ),
]
ProjectRoot = Annotated[str, StringConstraints(min_length=1, max_length=4096)]
RecordId = Annotated[
    str,
    StringConstraints(
        min_length=1,
        max_length=96,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,95}$",
    ),
]
RequestId = Annotated[
    str,
    StringConstraints(
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$",
    ),
]
Revision = Annotated[str, StringConstraints(pattern=r"^[a-f0-9]{64}$")]
Text = Annotated[str, StringConstraints(min_length=1, max_length=4000)]
Source = Annotated[str, StringConstraints(min_length=1, max_length=512)]
SupersedesReason = Annotated[str, StringConstraints(min_length=1, max_length=1000)]
RecordKind = Literal[
    "goal",
    "criterion",
    "verification",
    "blocker",
    "resolution",
    "result",
    "limitation",
    "constraint",
    "requirement",
    "fact",
    "decision",
    "progress",
]
VerificationOutcome = Literal["passed", "failed", "assumed", "unavailable"]


class TaskPlanRecordInput(StrictModel):
    record_id: RecordId
    kind: RecordKind
    text: Text
    sources: list[Source] = Field(min_length=1, max_length=8)
    outcome: VerificationOutcome | None = None
    resolves_blocker_id: RecordId | None = None
    supersedes_id: RecordId | None = None
    supersedes_reason: SupersedesReason | None = None

    @model_validator(mode="after")
    def validate_kind_fields(self) -> TaskPlanRecordInput:
        if self.kind == "verification" and self.outcome is None:
            raise ValueError("verification records require an explicit outcome")
        if self.kind != "verification" and self.outcome is not None:
            raise ValueError("outcome is valid only for verification records")
        if self.kind == "resolution" and self.resolves_blocker_id is None:
            raise ValueError("resolution records require a blocker id")
        if self.kind != "resolution" and self.resolves_blocker_id is not None:
            raise ValueError("only resolution records can reference blockers")
        if (self.supersedes_id is None) != (self.supersedes_reason is None):
            raise ValueError("supersedes id and reason must be supplied together")
        return self


class TaskPlanUpdateRequest(StrictModel):
    project_root: ProjectRoot
    plan_id: PlanId
    expected_revision: Revision | None = Field(...)
    request_id: RequestId
    records: list[TaskPlanRecordInput] = Field(min_length=1, max_length=100)

    @field_validator("project_root")
    @classmethod
    def require_absolute_project_root(cls, value: str) -> str:
        if not Path(value).is_absolute():
            raise ValueError("project_root must be absolute")
        return value


class TaskPlanUpdatePayload(StrictModel):
    request: TaskPlanUpdateRequest


class TaskPlanCriterionEvidence(StrictModel):
    criterion_id: RecordId
    verification_id: RecordId


class TaskPlanCompleteRequest(StrictModel):
    project_root: ProjectRoot
    plan_id: PlanId
    expected_revision: Revision
    request_id: RequestId
    criterion_evidence: list[TaskPlanCriterionEvidence] = Field(min_length=1, max_length=100)
    records: list[TaskPlanRecordInput] = Field(min_length=1, max_length=100)

    @field_validator("project_root")
    @classmethod
    def require_absolute_project_root(cls, value: str) -> str:
        if not Path(value).is_absolute():
            raise ValueError("project_root must be absolute")
        return value

    @model_validator(mode="after")
    def validate_completion_records(self) -> TaskPlanCompleteRequest:
        if not any(record.kind == "result" for record in self.records):
            raise ValueError("completion requires at least one result record")
        if any(record.kind not in {"result", "limitation"} for record in self.records):
            raise ValueError("completion records may only be results or limitations")
        if any(record.supersedes_id is not None for record in self.records):
            raise ValueError("completion records cannot supersede earlier records")
        return self


class TaskPlanCompletePayload(StrictModel):
    request: TaskPlanCompleteRequest


class TaskPlanArchiveRequest(StrictModel):
    project_root: ProjectRoot
    plan_id: PlanId
    expected_revision: Revision

    @field_validator("project_root")
    @classmethod
    def require_absolute_project_root(cls, value: str) -> str:
        if not Path(value).is_absolute():
            raise ValueError("project_root must be absolute")
        return value


class TaskPlanArchivePayload(StrictModel):
    request: TaskPlanArchiveRequest

from __future__ import annotations

import pytest
from pydantic import ValidationError
from token_io_decoupling_workflow.task_plan_payloads import (
    TaskPlanArchivePayload,
    TaskPlanCompletePayload,
    TaskPlanUpdatePayload,
)


def _record(
    record_id: str = "goal-1",
    kind: str = "goal",
    *,
    outcome: str | None = None,
) -> dict[str, object]:
    return {
        "record_id": record_id,
        "kind": kind,
        "text": "Keep the legacy plan and add typed records.",
        "sources": ["user requirement"],
        "outcome": outcome,
        "resolves_blocker_id": None,
        "supersedes_id": None,
        "supersedes_reason": None,
    }


def test_update_requires_revision_field_and_rejects_full_document_replacement() -> None:
    base = {
        "project_root": "/tmp/project-one",
        "plan_id": "plan-one",
        "request_id": "op-1",
        "records": [_record()],
    }
    created = TaskPlanUpdatePayload.model_validate({"request": {**base, "expected_revision": None}})
    assert created.request.expected_revision is None

    with pytest.raises(ValidationError):
        TaskPlanUpdatePayload.model_validate({"request": base})
    with pytest.raises(ValidationError):
        TaskPlanUpdatePayload.model_validate(
            {"request": {**base, "expected_revision": "", "summary": "replace"}}
        )
    with pytest.raises(ValidationError):
        TaskPlanUpdatePayload.model_validate(
            {"request": {**base, "expected_revision": None, "content": "# replacement"}}
        )
    with pytest.raises(ValidationError):
        TaskPlanUpdatePayload.model_validate(
            {"request": {**base, "project_root": "relative/path", "expected_revision": None}}
        )


@pytest.mark.parametrize("untrusted_field", ["repository_id", "storage_scope"])
def test_update_cannot_select_global_repository_scope(untrusted_field: str) -> None:
    request = {
        "project_root": "/tmp/project-one",
        "plan_id": "plan-one",
        "expected_revision": None,
        "request_id": "op-1",
        "records": [_record()],
        untrusted_field: "git-v1-" + "a" * 64 if untrusted_field == "repository_id" else "global",
    }
    with pytest.raises(ValidationError):
        TaskPlanUpdatePayload.model_validate({"request": request})


def test_completion_schema_requires_sha_passed_evidence_and_results() -> None:
    payload = {
        "request": {
            "project_root": "/tmp/project-one",
            "plan_id": "plan-one",
            "expected_revision": "a" * 64,
            "request_id": "op-complete",
            "criterion_evidence": [
                {"criterion_id": "criterion-1", "verification_id": "verification-1"}
            ],
            "records": [_record("result-1", "result")],
        }
    }
    parsed = TaskPlanCompletePayload.model_validate(payload)
    assert parsed.request.records[0].kind == "result"

    with pytest.raises(ValidationError):
        TaskPlanCompletePayload.model_validate(
            {
                "request": {
                    **payload["request"],
                    "expected_revision": None,
                }
            }
        )
    with pytest.raises(ValidationError):
        TaskPlanCompletePayload.model_validate(
            {
                "request": {
                    **payload["request"],
                    "records": [_record("progress-1", "progress")],
                }
            }
        )
    with pytest.raises(ValidationError):
        TaskPlanCompletePayload.model_validate(
            {
                "request": {
                    **payload["request"],
                    "records": [_record("result-1", "result", outcome="passed")],
                }
            }
        )


def test_archive_payload_has_fixed_project_and_revision_fields() -> None:
    parsed = TaskPlanArchivePayload.model_validate(
        {
            "request": {
                "project_root": "/tmp/project-one",
                "plan_id": "plan-one",
                "expected_revision": "b" * 64,
            }
        }
    )
    assert parsed.request.plan_id == "plan-one"
    with pytest.raises(ValidationError):
        TaskPlanArchivePayload.model_validate(
            {
                "request": {
                    "project_root": "/tmp/project-one",
                    "plan_id": "plan-one",
                    "expected_revision": "b" * 64,
                    "destination": "other/location",
                }
            }
        )

from __future__ import annotations

import hashlib

import pytest
from token_io_decoupling_workflow.task_plan_core import (
    _EVENT_PREFIX,
    _HEADER_PREFIX,
    TaskPlanFailure,
    _append_event,
    _parse_snapshot,
    _request_hash,
)


def _record(record_id: str, kind: str = "goal") -> dict[str, object]:
    return {
        "record_id": record_id,
        "kind": kind,
        "text": f"Text for {record_id}",
        "sources": ["user requirement"],
        "outcome": None,
        "resolves_blocker_id": None,
        "supersedes_id": None,
        "supersedes_reason": None,
    }


def test_append_only_history_preserves_legacy_bytes_and_revision_chain() -> None:
    legacy = b"# Old plan\r\nKeep the exact bytes.\r\n"
    project_root = "/tmp/project-one"
    data = {"records": [_record("goal-1")]}
    request_hash = _request_hash("plan-one", project_root, "update", data)
    first = _append_event(
        legacy,
        "plan-one",
        project_root,
        "op-1",
        "update",
        request_hash,
        data,
    )
    snapshot = _parse_snapshot(first, "plan-one", project_root)
    assert first.startswith(legacy)
    assert snapshot.legacy == legacy
    assert snapshot.events[0]["previous_revision"] == hashlib.sha256(legacy).hexdigest()
    assert snapshot.records["goal-1"]["text"] == "Text for goal-1"

    next_data = {"records": [_record("criterion-1", "criterion")]}
    next_hash = _request_hash("plan-one", project_root, "update", next_data)
    second = _append_event(
        first,
        "plan-one",
        project_root,
        "op-2",
        "update",
        next_hash,
        next_data,
    )
    next_snapshot = _parse_snapshot(second, "plan-one", project_root)
    assert second.startswith(legacy)
    assert next_snapshot.events[1]["previous_revision"] == hashlib.sha256(first).hexdigest()
    assert set(next_snapshot.records) == {"goal-1", "criterion-1"}


def test_new_empty_plan_has_valid_header_and_project_binding() -> None:
    project_root = "/tmp/project-one"
    data = {"records": [_record("goal-1")]}
    digest = _request_hash("plan-one", project_root, "update", data)
    encoded = _append_event(None, "plan-one", project_root, "op-1", "update", digest, data)

    snapshot = _parse_snapshot(encoded, "plan-one", project_root)
    assert snapshot.legacy == b""
    assert snapshot.events[0]["project_root"] == project_root
    with pytest.raises(TaskPlanFailure, match="history_identity_mismatch"):
        _parse_snapshot(encoded, "plan-one", "/tmp/another-project")


def test_tampered_history_chain_fails_closed() -> None:
    project_root = "/tmp/project-one"
    data = {"records": [_record("goal-1")]}
    digest = _request_hash("plan-one", project_root, "update", data)
    encoded = _append_event(None, "plan-one", project_root, "op-1", "update", digest, data)
    changed = encoded[:-2] + b"x\n"

    with pytest.raises(TaskPlanFailure):
        _parse_snapshot(changed, "plan-one", project_root)


def test_multistage_readable_history_uses_real_newlines_and_preserves_crlf_legacy() -> None:
    legacy = b"# Existing plan\r\nKeep these bytes unchanged.\r\n"
    project_root = "/tmp/project-one"
    original_text = 'Literal marker:\n~~~json task-plan-event-v1\n{"fake":true}\n~~~'
    goal = _record("goal-1")
    goal["text"] = original_text
    first_data = {"records": [goal]}
    first_hash = _request_hash("plan-one", project_root, "update", first_data)
    first = _append_event(
        legacy,
        "plan-one",
        project_root,
        "op-1",
        "update",
        first_hash,
        first_data,
    )

    criterion_data = {"records": [_record("criterion-1", "criterion")]}
    criterion_hash = _request_hash("plan-one", project_root, "update", criterion_data)
    second = _append_event(
        first,
        "plan-one",
        project_root,
        "op-2",
        "update",
        criterion_hash,
        criterion_data,
    )

    snapshot = _parse_snapshot(second, "plan-one", project_root)
    assert second.startswith(legacy)
    assert snapshot.legacy == legacy
    assert snapshot.records["goal-1"]["text"] == original_text
    assert snapshot.events[1]["previous_revision"] == hashlib.sha256(first).hexdigest()
    assert second.count(_HEADER_PREFIX) == 1
    assert second.count(_EVENT_PREFIX) == 2
    assert b'"record_id":"goal-1"' in second

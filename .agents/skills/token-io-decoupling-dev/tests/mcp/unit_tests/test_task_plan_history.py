"""任务计划历史解析的身份隔离、错误优先级和完成状态回归。"""

import hashlib
from typing import Any

import pytest

from token_io_decoupling_tools.task_plan_core import (
    _EVENT_PREFIX,
    _EVENT_V2_PREFIX,
    _HEADER_PREFIX,
    _HEADER_V2_PREFIX,
    MAX_PLAN_BYTES,
    TaskPlanFailure,
    _append_event,
    _parse_snapshot,
    _request_hash,
)

LEGACY = b"# Existing plan\r\nKeep these bytes."


@pytest.fixture(
    params=[{"project_root": "/tmp/project-one"}, {"repository_id": "git-v1-" + "a" * 64}],
    ids=["project-v1", "repository-v2"],
)
def identity(request: pytest.FixtureRequest) -> dict[str, str]:
    return request.param


def _record(record_id: str, kind: str, outcome: str | None = None) -> dict[str, Any]:
    return {
        "record_id": record_id,
        "kind": kind,
        "text": f"Text for {record_id}",
        "sources": ["user requirement"],
        "outcome": outcome,
        "resolves_blocker_id": None,
        "supersedes_id": None,
        "supersedes_reason": None,
    }


def _append(
    raw: bytes,
    operation_id: str,
    data: dict[str, Any],
    identity: dict[str, str],
    operation: str = "update",
) -> bytes:
    project_root = identity.get("project_root", "")
    repository_id = identity.get("repository_id")
    digest = _request_hash("plan-one", project_root, operation, data, repository_id=repository_id)
    return _append_event(
        raw,
        "plan-one",
        project_root,
        operation_id,
        operation,
        digest,
        data,
        repository_id=repository_id,
    )


@pytest.fixture
def history(identity: dict[str, str]) -> bytes:
    return _append(
        LEGACY,
        "op-1",
        {
            "records": [
                _record("criterion-1", "criterion"),
                _record("verification-1", "verification", "passed"),
            ]
        },
        identity,
    )


def test_replay_preserves_legacy_and_original_revision(
    history: bytes, identity: dict[str, str]
) -> None:
    snapshot = _parse_snapshot(history, "plan-one", **identity)

    assert snapshot.raw == history
    assert snapshot.legacy == LEGACY
    assert snapshot.revision == hashlib.sha256(history).hexdigest()
    assert snapshot.events[0]["previous_revision"] == hashlib.sha256(LEGACY).hexdigest()
    assert snapshot.active_ids == frozenset({"criterion-1", "verification-1"})
    assert snapshot.completed is False


@pytest.mark.parametrize(
    ("original", "replacement", "reason"),
    [
        (b"Keep these bytes.", b"Keep other bytes.", "history_legacy_prefix_mismatch"),
        (b"bytes.\n~~~json", b"bytes.\r\n~~~json", "history_legacy_prefix_mismatch"),
        (b"bytes.\n~~~json", b"bytes.x~~~json", "history_invalid"),
        (b'"operation":"update"', b'"operation":"unknown"', "history_identity_mismatch"),
        (b'"plan_id":"plan-one"', b'"plan_id":"plan-two"', "history_identity_mismatch"),
        (b'"text":"Text for criterion-1"', b'"text":"Changed"', "history_request_hash_mismatch"),
        (b'"previous_revision":"', b'"previous_revision":"bad-', "history_chain_mismatch"),
    ],
    ids=[
        "legacy-content",
        "legacy-separator",
        "header-line-boundary",
        "event-operation",
        "plan-identity",
        "request-hash",
        "previous-revision",
    ],
)
def test_corrupted_history_keeps_error_reason(
    history: bytes, identity: dict[str, str], original: bytes, replacement: bytes, reason: str
) -> None:
    corrupted = history.replace(original, replacement)
    assert corrupted != history

    with pytest.raises(TaskPlanFailure, match=f"^{reason}$"):
        _parse_snapshot(corrupted, "plan-one", **identity)


def test_request_hash_failure_precedes_chain_failure(
    history: bytes, identity: dict[str, str]
) -> None:
    corrupted = history.replace(b'"request_hash":"', b'"request_hash":"bad-').replace(
        b'"previous_revision":"', b'"previous_revision":"bad-'
    )

    with pytest.raises(TaskPlanFailure, match="^history_request_hash_mismatch$"):
        _parse_snapshot(corrupted, "plan-one", **identity)


def test_event_identity_must_match_validated_header(
    history: bytes, identity: dict[str, str]
) -> None:
    prefix, field, suffix = history.rpartition(b'"plan_id":"plan-one"')
    assert field == b'"plan_id":"plan-one"'
    corrupted = prefix + b'"plan_id":"plan-two"' + suffix

    with pytest.raises(TaskPlanFailure, match="^history_identity_mismatch$"):
        _parse_snapshot(corrupted, "plan-one", **identity)


@pytest.mark.parametrize(
    "marker", [_HEADER_PREFIX, _HEADER_V2_PREFIX], ids=["extra-v1", "extra-v2"]
)
def test_duplicate_or_mixed_headers_are_rejected(
    history: bytes, identity: dict[str, str], marker: bytes
) -> None:
    with pytest.raises(TaskPlanFailure, match="^history_invalid$"):
        _parse_snapshot(history + marker, "plan-one", **identity)


def test_header_without_events_preserves_legacy(history: bytes, identity: dict[str, str]) -> None:
    event_prefix = _EVENT_PREFIX if "project_root" in identity else _EVENT_V2_PREFIX
    header_only = history[: history.index(event_prefix)]

    snapshot = _parse_snapshot(header_only, "plan-one", **identity)

    assert snapshot.raw == header_only
    assert snapshot.legacy == LEGACY
    assert snapshot.events == ()
    assert snapshot.records == {}
    assert snapshot.completed is False


def test_truncated_event_is_rejected(history: bytes, identity: dict[str, str]) -> None:
    with pytest.raises(TaskPlanFailure, match="^history_invalid$"):
        _parse_snapshot(history[:-1], "plan-one", **identity)


def test_duplicate_operation_is_rejected_before_record_conflict(
    history: bytes, identity: dict[str, str]
) -> None:
    duplicate = _append(
        history, "op-1", {"records": [_record("criterion-1", "criterion")]}, identity
    )

    with pytest.raises(TaskPlanFailure, match="^history_duplicate_operation_id$"):
        _parse_snapshot(duplicate, "plan-one", **identity)


@pytest.mark.parametrize(
    ("records", "reason"),
    [(None, "history_record_invalid"), ([], "invalid_record_count")],
    ids=["records-not-a-list", "records-empty"],
)
def test_invalid_record_payload_is_rejected(
    history: bytes, identity: dict[str, str], records: Any, reason: str
) -> None:
    invalid = _append(history, "op-2", {"records": records}, identity)

    with pytest.raises(TaskPlanFailure, match=f"^{reason}$"):
        _parse_snapshot(invalid, "plan-one", **identity)


def test_completion_and_later_event_error_order(history: bytes, identity: dict[str, str]) -> None:
    completed = _append(
        history,
        "op-2",
        {
            "records": [_record("result-1", "result")],
            "criterion_evidence": [
                {"criterion_id": "criterion-1", "verification_id": "verification-1"}
            ],
        },
        identity,
        "complete",
    )
    snapshot = _parse_snapshot(completed, "plan-one", **identity)
    assert snapshot.completed is True
    assert snapshot.active_ids == frozenset({"criterion-1", "verification-1", "result-1"})

    malformed_records = _append(completed, "op-3", {"records": None}, identity)
    with pytest.raises(TaskPlanFailure, match="^history_after_completion$"):
        _parse_snapshot(malformed_records, "plan-one", **identity)

    malformed_shape = _append(completed, "op-3", {"unexpected": None}, identity)
    with pytest.raises(TaskPlanFailure, match="^history_invalid$"):
        _parse_snapshot(malformed_shape, "plan-one", **identity)


def test_opposite_identity_scope_is_rejected(history: bytes, identity: dict[str, str]) -> None:
    opposite = (
        {"repository_id": "git-v1-" + "a" * 64}
        if "project_root" in identity
        else {"project_root": "/tmp/project-one"}
    )

    with pytest.raises(TaskPlanFailure, match="^history_identity_mismatch$"):
        _parse_snapshot(history, "plan-one", **opposite)


def test_size_limit_precedes_plain_legacy_history() -> None:
    with pytest.raises(TaskPlanFailure, match="^plan_too_large$"):
        _parse_snapshot(b"x" * (MAX_PLAN_BYTES + 1), "plan-one")

"""计划请求边界、状态观测和审计回执的契约。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .constants import _REQUEST_ID
from .history import _parse_snapshot
from .records import (
    _apply_records,
    _validate_evidence,
    _validate_id,
    _validate_plan_id,
    _validate_record,
    _validate_revision,
)
from .types import TaskPlanFailure, _sha, _Snapshot


def _current_state(snapshot: _Snapshot | None) -> str:
    if snapshot is None:
        return "absent"
    if snapshot.completed:
        return "completed"
    return "in_progress" if snapshot.events else "legacy"


def _observed_state(
    raw: bytes | None,
    plan_id: str | None,
    project_root: str | None,
    *,
    repository_id: str | None = None,
) -> str:
    if plan_id is None or (project_root is None and repository_id is None):
        return "unknown"
    if raw is None:
        return "absent"
    try:
        return _current_state(
            _parse_snapshot(
                raw,
                plan_id,
                project_root if repository_id is None else None,
                repository_id=repository_id,
            )
        )
    except TaskPlanFailure:
        return "unknown"


def _receipt(
    *,
    status: str,
    reason: str,
    plan_id: str | None,
    state: str,
    before_revision: str | None,
    current_revision: str | None,
    changed_ids: list[str] | None = None,
    preservation: bool | None = None,
    readback: str = "not_applicable",
    replayed: bool = False,
    reconciliation: str = "not_required",
    project_root: str | None = None,
    memory_name: str | None = None,
    storage_scope: str | None = None,
    repository_id: str | None = None,
) -> dict[str, Any]:
    return {
        "status": status,
        "reason": reason,
        "plan_id": plan_id,
        "project_root": project_root,
        "memory_name": memory_name,
        "storage_scope": storage_scope,
        "repository_id": repository_id,
        "plan_state": state,
        "before_revision": before_revision,
        "current_revision": current_revision,
        "changed_record_ids": changed_ids or [],
        "changed_count": len(changed_ids or []),
        "legacy_prefix_preserved": preservation,
        "readback": readback,
        "replayed": replayed,
        "reconciliation_status": reconciliation,
    }


def _request_data(
    request: dict[str, Any], operation: str
) -> tuple[str, str, str, str | None, dict[str, Any]]:
    if not isinstance(request, dict):
        raise TaskPlanFailure("invalid_request")
    project_root = request.get("project_root")
    if (
        not isinstance(project_root, str)
        or not Path(project_root).is_absolute()
        or len(project_root) > 4096
    ):
        raise TaskPlanFailure("invalid_project_root")
    plan_id = _validate_plan_id(request.get("plan_id"))
    operation_id = _validate_id(request.get("request_id"), _REQUEST_ID, "invalid_request_id")
    expected = _validate_revision(
        request.get("expected_revision"), allow_absent=operation == "update"
    )
    if operation == "update":
        if set(request) != {
            "project_root",
            "plan_id",
            "request_id",
            "expected_revision",
            "records",
        }:
            raise TaskPlanFailure("invalid_request_fields")
        raw_records = request["records"]
        if not isinstance(raw_records, list):
            raise TaskPlanFailure("invalid_record_count")
        records = [_validate_record(record) for record in raw_records]
        data = {"records": records}
    else:
        if set(request) != {
            "project_root",
            "plan_id",
            "request_id",
            "expected_revision",
            "criterion_evidence",
            "records",
        }:
            raise TaskPlanFailure("invalid_request_fields")
        raw_records = request["records"]
        if not isinstance(raw_records, list):
            raise TaskPlanFailure("invalid_record_count")
        records = [_validate_record(record) for record in raw_records]
        evidence = request["criterion_evidence"]
        if not isinstance(evidence, list):
            raise TaskPlanFailure("criterion_evidence_required")
        data = {"records": records, "criterion_evidence": evidence}
    return plan_id, operation_id, project_root, expected, data


def _check_expected(expected: str | None, raw: bytes | None) -> None:
    if raw is None:
        if expected is None:
            return
        raise TaskPlanFailure("plan_not_found", "conflict")
    if expected is None:
        raise TaskPlanFailure("plan_already_exists", "conflict")
    if expected != _sha(raw):
        raise TaskPlanFailure("stale_revision", "conflict")


def _locate_replay(snapshot: _Snapshot, operation_id: str, request_hash: str) -> bool:
    for event in snapshot.events:
        if event["operation_id"] != operation_id:
            continue
        if event["request_hash"] != request_hash:
            raise TaskPlanFailure("operation_id_conflict", "conflict")
        return True
    return False


def _check_project_scope(requested_project: str, project: str | None) -> str:
    if not project or requested_project != project:
        raise TaskPlanFailure("project_scope_mismatch", "conflict")
    return project


def _archive_request_project(request: Any) -> str:
    if not isinstance(request, dict) or set(request) != {
        "project_root",
        "plan_id",
        "expected_revision",
    }:
        raise TaskPlanFailure("invalid_request_fields")
    requested_project = request["project_root"]
    if (
        not isinstance(requested_project, str)
        or not Path(requested_project).is_absolute()
        or len(requested_project) > 4096
    ):
        raise TaskPlanFailure("invalid_project_root")
    return requested_project


def _verify_archive_snapshot(snapshot: _Snapshot, current_revision: str, expected: str) -> None:
    if current_revision != expected:
        raise TaskPlanFailure("stale_revision", "conflict")
    if not snapshot.completed:
        raise TaskPlanFailure("plan_not_completed")


def _prepare_completion_records(snapshot: _Snapshot, data: dict[str, Any]) -> None:
    records = dict(snapshot.records)
    active_ids = set(snapshot.active_ids)
    resolved = set(snapshot.resolved_blockers)
    _apply_records(records, active_ids, resolved, data["records"], completion=True)
    if not any(record["kind"] == "result" for record in data["records"]):
        raise TaskPlanFailure("completion_result_required")
    unresolved = tuple(
        sorted(
            record_id
            for record_id, record in records.items()
            if record["kind"] == "blocker" and record_id not in resolved
        )
    )
    evidence = _validate_evidence(records, active_ids, unresolved, data["criterion_evidence"])
    data["criterion_evidence"] = evidence

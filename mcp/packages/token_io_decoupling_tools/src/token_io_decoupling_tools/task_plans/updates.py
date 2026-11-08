"""计划更新事务及其回读、冲突与不确定性回执。"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .contracts import (
    _check_expected,
    _check_project_scope,
    _current_state,
    _locate_replay,
    _request_data,
)
from .records import _apply_records
from .types import TaskPlanFailure, _sha

if TYPE_CHECKING:
    from .service import TaskPlanService


def update_plan(service: TaskPlanService, request: dict[str, Any]) -> dict[str, Any]:
    plan_id: str | None = None
    project: str | None = None
    memory_name: str | None = None
    before_revision: str | None = None
    current_revision: str | None = None
    state = "unknown"
    try:
        plan_id, operation_id, requested_project, expected, data = _request_data(request, "update")
        if service._store is None:
            return service._unavailable(plan_id, "task_plan_backend_not_configured")
        project, memory_name = service._scope(plan_id)
        project = _check_project_scope(requested_project, project)
        request_hash = service._request_hash_for(plan_id, project, "update", data)
        with service._store.locked(plan_id):
            raw = service._store.read(plan_id)
            current_revision = _sha(raw) if raw is not None else None
            before_revision = current_revision
            snapshot = service._parse_plan(raw, plan_id, project) if raw is not None else None
            state = _current_state(snapshot)
            if snapshot is not None and snapshot.completed:
                raise TaskPlanFailure("plan_completed", "conflict")
            archived = service._store.read(plan_id, archived=True)
            if archived is not None:
                service._parse_plan(archived, plan_id, project)
                _, memory_name = service._scope(plan_id, archived=True)
                raise TaskPlanFailure("plan_already_archived", "conflict")
            if snapshot is not None and _locate_replay(snapshot, operation_id, request_hash):
                return service._make_receipt(
                    status="replayed",
                    reason="identical_operation_replay",
                    plan_id=plan_id,
                    state=state,
                    before_revision=expected,
                    current_revision=snapshot.revision,
                    replayed=True,
                    preservation=True,
                    readback="verified",
                    project_root=project,
                    memory_name=memory_name,
                )
            _check_expected(expected, raw)
            records = {} if snapshot is None else dict(snapshot.records)
            active_ids = set() if snapshot is None else set(snapshot.active_ids)
            resolved = set() if snapshot is None else set(snapshot.resolved_blockers)
            _apply_records(records, active_ids, resolved, data["records"], completion=False)
            updated = service._append_event_for(
                raw, plan_id, project, operation_id, "update", request_hash, data
            )
            parsed = service._parse_plan(updated, plan_id, project)
            status, actual = service._store.write(plan_id, raw, updated)
            current_revision = _sha(actual) if actual is not None else None
            state = _current_state(parsed)
            if status == "conflict":
                return service._make_receipt(
                    status="conflict",
                    reason="state_changed_during_write",
                    plan_id=plan_id,
                    state=service._observed_state_for(actual, plan_id, project),
                    before_revision=before_revision,
                    current_revision=current_revision,
                    project_root=project,
                    memory_name=memory_name,
                )
            if status == "unavailable":
                return service._make_receipt(
                    status="unavailable",
                    reason="atomic_write_unavailable",
                    plan_id=plan_id,
                    state=_current_state(snapshot),
                    before_revision=before_revision,
                    current_revision=current_revision,
                    readback="not_applicable",
                    project_root=project,
                    memory_name=memory_name,
                )
            if status != "written" or actual != updated:
                return service._make_receipt(
                    status="uncertain",
                    reason="write_readback_uncertain",
                    plan_id=plan_id,
                    state=service._observed_state_for(actual, plan_id, project),
                    before_revision=before_revision,
                    current_revision=current_revision,
                    changed_ids=[record["record_id"] for record in data["records"]],
                    preservation=bool(actual and actual.startswith(parsed.legacy)),
                    readback="mismatch_or_unavailable",
                    reconciliation="required",
                    project_root=project,
                    memory_name=memory_name,
                )
            return service._make_receipt(
                status="updated",
                reason="append_verified",
                plan_id=plan_id,
                state=state,
                before_revision=before_revision,
                current_revision=current_revision,
                changed_ids=[record["record_id"] for record in data["records"]],
                preservation=actual.startswith(parsed.legacy),
                readback="verified",
                project_root=project,
                memory_name=memory_name,
            )
    except TaskPlanFailure as exc:
        return service._make_receipt(
            status=exc.status,
            reason=exc.reason,
            plan_id=plan_id,
            state=state,
            before_revision=before_revision,
            current_revision=current_revision,
            project_root=project,
            memory_name=memory_name,
        )
    except Exception:
        return service._make_receipt(
            status="unavailable",
            reason="task_plan_backend_unavailable",
            plan_id=plan_id,
            state=state,
            before_revision=before_revision,
            current_revision=current_revision,
            project_root=project,
            memory_name=memory_name,
        )

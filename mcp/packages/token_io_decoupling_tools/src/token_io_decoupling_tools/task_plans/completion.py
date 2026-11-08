"""记录完成证据并支持归档后的幂等完成操作重放。"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .contracts import (
    _check_expected,
    _check_project_scope,
    _current_state,
    _locate_replay,
    _prepare_completion_records,
    _request_data,
)
from .types import TaskPlanFailure, _sha

if TYPE_CHECKING:
    from .service import TaskPlanService


def complete_plan(service: TaskPlanService, request: dict[str, Any]) -> dict[str, Any]:
    plan_id: str | None = None
    project: str | None = None
    memory_name: str | None = None
    before_revision: str | None = None
    current_revision: str | None = None
    state = "unknown"
    try:
        plan_id, operation_id, requested_project, expected, data = _request_data(
            request, "complete"
        )
        if service._store is None:
            return service._unavailable(plan_id, "task_plan_backend_not_configured")
        project, memory_name = service._scope(plan_id)
        project = _check_project_scope(requested_project, project)
        request_hash = service._request_hash_for(plan_id, project, "complete", data)
        with service._store.locked(plan_id):
            raw = service._store.read(plan_id)
            if raw is None:
                archived = service._require_archived_plan(plan_id)
                snapshot = service._parse_plan(archived, plan_id, project)
                current_revision = snapshot.revision
                state = _current_state(snapshot)
                _, memory_name = service._scope(plan_id, archived=True)
                return service._archived_completion_replay(
                    snapshot, request, project, memory_name, request_hash
                )
            current_revision = _sha(raw)
            before_revision = current_revision
            snapshot = service._parse_plan(raw, plan_id, project)
            state = _current_state(snapshot)
            if _locate_replay(snapshot, operation_id, request_hash):
                return service._make_receipt(
                    status="replayed",
                    reason="identical_operation_replay",
                    plan_id=plan_id,
                    state="completed",
                    before_revision=expected,
                    current_revision=snapshot.revision,
                    replayed=True,
                    preservation=True,
                    readback="verified",
                    project_root=project,
                    memory_name=memory_name,
                )
            service._reject_archive_collision(plan_id, project)
            _check_expected(expected, raw)
            if snapshot.completed:
                raise TaskPlanFailure("plan_already_completed", "conflict")
            _prepare_completion_records(snapshot, data)
            updated = service._append_event_for(
                raw, plan_id, project, operation_id, "complete", request_hash, data
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
                status="completed",
                reason="completion_evidence_recorded",
                plan_id=plan_id,
                state="completed",
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

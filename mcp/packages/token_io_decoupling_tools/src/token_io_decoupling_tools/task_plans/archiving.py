"""完成计划的无覆盖归档与归档操作重放。"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .contracts import (
    _archive_request_project,
    _check_project_scope,
    _current_state,
    _verify_archive_snapshot,
)
from .records import _validate_plan_id, _validate_revision
from .types import TaskPlanFailure, _sha

if TYPE_CHECKING:
    from .service import TaskPlanService


def archive_plan(service: TaskPlanService, request: dict[str, Any]) -> dict[str, Any]:
    plan_id: str | None = None
    project: str | None = None
    memory_name: str | None = None
    before_revision: str | None = None
    current_revision: str | None = None
    state = "unknown"
    try:
        requested_project = _archive_request_project(request)
        plan_id = _validate_plan_id(request["plan_id"])
        expected = _validate_revision(request["expected_revision"])
        assert expected is not None
        if service._store is None:
            return service._unavailable(plan_id, "task_plan_backend_not_configured")
        project, source_name = service._scope(plan_id)
        _, target_name = service._scope(plan_id, archived=True)
        memory_name = source_name
        project = _check_project_scope(requested_project, project)
        with service._store.locked(plan_id):
            source = service._store.read(plan_id)
            if source is None:
                target = service._require_archived_plan(plan_id)
                snapshot = service._parse_plan(target, plan_id, project)
                current_revision = snapshot.revision
                state = _current_state(snapshot)
                if (
                    current_revision == expected
                    and snapshot.completed
                    and snapshot.events
                    and snapshot.events[-1]["operation"] == "complete"
                ):
                    return service._make_receipt(
                        status="already_archived",
                        reason="identical_archive_replay",
                        plan_id=plan_id,
                        state="completed",
                        before_revision=expected,
                        current_revision=current_revision,
                        preservation=True,
                        readback="verified",
                        replayed=True,
                        project_root=project,
                        memory_name=target_name,
                    )
                raise TaskPlanFailure("archive_reconciliation_mismatch", "conflict")
            current_revision = _sha(source)
            before_revision = current_revision
            snapshot = service._parse_plan(source, plan_id, project)
            state = _current_state(snapshot)
            _verify_archive_snapshot(snapshot, current_revision, expected)
            existing_archive = service._store.read(plan_id, archived=True)
            if existing_archive is not None:
                service._parse_plan(existing_archive, plan_id, project)
                raise TaskPlanFailure("archive_collision", "conflict")
            status, actual = service._store.archive(plan_id, source)
            current_revision = _sha(actual) if actual is not None else None
            if status == "archived" and actual == source:
                return service._make_receipt(
                    status="archived",
                    reason="completed_plan_moved_without_overwrite",
                    plan_id=plan_id,
                    state="completed",
                    before_revision=expected,
                    current_revision=current_revision,
                    preservation=True,
                    readback="verified",
                    project_root=project,
                    memory_name=target_name,
                )
            if status == "unavailable":
                return service._make_receipt(
                    status="unavailable",
                    reason="archive_primitive_unavailable",
                    plan_id=plan_id,
                    state="completed",
                    before_revision=before_revision,
                    current_revision=_sha(actual) if actual is not None else None,
                    preservation=actual == source,
                    readback="not_applicable",
                    project_root=project,
                    memory_name=source_name,
                )
            reason = {
                "collision": "archive_collision",
                "conflict": "state_changed_during_archive",
                "unavailable": "archive_unavailable",
            }.get(status, "archive_interrupted")
            return service._make_receipt(
                status="conflict" if status in {"collision", "conflict"} else "uncertain",
                reason=reason,
                plan_id=plan_id,
                state="completed",
                before_revision=before_revision,
                current_revision=current_revision,
                preservation=actual == source,
                readback="uncertain",
                reconciliation="required",
                project_root=project,
                memory_name=source_name,
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
            reconciliation="required" if exc.status == "uncertain" else "not_required",
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

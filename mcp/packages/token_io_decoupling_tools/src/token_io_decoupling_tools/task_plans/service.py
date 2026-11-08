"""任务计划生命周期服务及后端能力报告。"""

from __future__ import annotations

from typing import Any

from . import archiving as _archiving
from . import completion as _completion
from . import updates as _updates
from .codec import _request_hash
from .constants import _REPOSITORY_ID
from .contracts import _locate_replay, _observed_state, _receipt
from .history import _parse_snapshot
from .store import SerenaMemoryStore
from .types import PlanStore, TaskPlanFailure, _Snapshot
from .writer import _append_event


class TaskPlanService:
    """Deterministic plan operations over an injected store; None means unavailable."""

    def __init__(self, store: PlanStore | None = None) -> None:
        if store is not None and not isinstance(store, SerenaMemoryStore):
            raise TypeError("TaskPlanService requires SerenaMemoryStore")
        self._store = store

    def capability(self) -> dict[str, Any]:
        if self._store is None:
            return {
                "status": "unavailable",
                "reason_code": "task_plan_backend_not_configured",
                "project_root": None,
                "storage_scope": None,
                "repository_id": None,
                "namespace": None,
                "archive_namespace": None,
            }
        describe = getattr(self._store, "capability", None)
        if not callable(describe):
            return {
                "status": "unavailable",
                "reason_code": "task_plan_backend_interface_unsupported",
                "project_root": None,
                "storage_scope": None,
                "repository_id": None,
                "namespace": None,
                "archive_namespace": None,
            }
        try:
            return describe()
        except Exception:
            return {
                "status": "unavailable",
                "reason_code": "task_plan_backend_unavailable",
                "project_root": None,
                "storage_scope": getattr(self._store, "storage_scope", None),
                "repository_id": getattr(self._store, "repository_id", None),
                "namespace": None,
                "archive_namespace": None,
            }

    def _unavailable(self, plan_id: str | None, reason: str) -> dict[str, Any]:
        return self._make_receipt(
            status="unavailable",
            reason=reason,
            plan_id=plan_id,
            state="unknown",
            before_revision=None,
            current_revision=None,
        )

    def _make_receipt(self, **fields: Any) -> dict[str, Any]:
        store = self._store
        fields.setdefault(
            "storage_scope",
            getattr(store, "storage_scope", "project") if store is not None else None,
        )
        fields.setdefault("repository_id", getattr(store, "repository_id", None))
        return _receipt(**fields)

    def _history_binding(self, project_root: str) -> tuple[str | None, str | None]:
        if self._store is not None and getattr(self._store, "storage_scope", "project") == "global":
            repository_id = getattr(self._store, "repository_id", None)
            if not isinstance(repository_id, str) or not _REPOSITORY_ID.fullmatch(repository_id):
                raise TaskPlanFailure("repository_identity_invalid", "unavailable")
            return None, repository_id
        return project_root, None

    def _parse_plan(self, raw: bytes, plan_id: str, project_root: str) -> _Snapshot:
        history_root, repository_id = self._history_binding(project_root)
        return _parse_snapshot(raw, plan_id, history_root, repository_id=repository_id)

    def _request_hash_for(
        self, plan_id: str, project_root: str, operation: str, data: dict[str, Any]
    ) -> str:
        _, repository_id = self._history_binding(project_root)
        return _request_hash(plan_id, project_root, operation, data, repository_id=repository_id)

    def _append_event_for(
        self,
        raw: bytes | None,
        plan_id: str,
        project_root: str,
        operation_id: str,
        operation: str,
        request_hash: str,
        data: dict[str, Any],
    ) -> bytes:
        _, repository_id = self._history_binding(project_root)
        return _append_event(
            raw,
            plan_id,
            project_root,
            operation_id,
            operation,
            request_hash,
            data,
            repository_id=repository_id,
        )

    def _observed_state_for(
        self, raw: bytes | None, plan_id: str | None, project_root: str | None
    ) -> str:
        if plan_id is None or project_root is None:
            return "unknown"
        history_root, repository_id = self._history_binding(project_root)
        return _observed_state(raw, plan_id, history_root, repository_id=repository_id)

    def _scope(self, plan_id: str, archived: bool = False) -> tuple[str | None, str | None]:
        if self._store is None:
            return None, None
        project = getattr(self._store, "project_root", None)
        name_factory = getattr(self._store, "_memory_name", None)
        if callable(name_factory):
            name = name_factory(plan_id, archived)
        else:
            namespace = "archive-plans" if archived else "plans"
            name = f"{namespace}/PLAN-{plan_id}"
        return project if isinstance(project, str) else None, name

    def update(self, request: dict[str, Any]) -> dict[str, Any]:
        return _updates.update_plan(self, request)

    def _require_archived_plan(self, plan_id: str) -> bytes:
        assert self._store is not None
        archived = self._store.read(plan_id, archived=True)
        if archived is None:
            raise TaskPlanFailure("plan_not_found", "conflict")
        return archived

    def _reject_archive_collision(self, plan_id: str, project: str) -> None:
        assert self._store is not None
        archived = self._store.read(plan_id, archived=True)
        if archived is not None:
            self._parse_plan(archived, plan_id, project)
            raise TaskPlanFailure("archive_collision", "conflict")

    def _archived_completion_replay(
        self,
        snapshot: _Snapshot,
        request: dict[str, Any],
        project: str,
        memory_name: str | None,
        request_hash: str,
    ) -> dict[str, Any]:
        plan_id = request["plan_id"]
        operation_id = request["request_id"]
        expected = request["expected_revision"]
        if _locate_replay(snapshot, operation_id, request_hash):
            return self._make_receipt(
                status="replayed",
                reason="identical_completion_replay_after_archive",
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
        raise TaskPlanFailure("plan_already_archived", "conflict")

    def complete(self, request: dict[str, Any]) -> dict[str, Any]:
        return _completion.complete_plan(self, request)

    def archive(self, request: dict[str, Any]) -> dict[str, Any]:
        return _archiving.archive_plan(self, request)

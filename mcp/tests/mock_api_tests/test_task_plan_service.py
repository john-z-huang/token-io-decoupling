from __future__ import annotations

import hashlib
import threading
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

from token_io_decoupling_workflow.task_plan_core import (
    SerenaMemoryStore,
    TaskPlanFailure,
    TaskPlanService,
    _parse_snapshot,
)


@dataclass
class _State:
    plans: dict[str, bytes] = field(default_factory=dict)
    archives: dict[str, bytes] = field(default_factory=dict)
    lock: threading.RLock = field(default_factory=threading.RLock)
    lock_calls: int = 0
    read_calls: int = 0
    write_mode: str = "normal"
    archive_mode: str = "normal"


class _TestSerenaMemoryStore(SerenaMemoryStore):
    """A test-only store collaborator; production construction requires Serena MemoryManager."""

    def __init__(self, project_root: str, state: _State | None = None) -> None:
        self.project_root = project_root
        self.state = state or _State()

    def capability(self) -> dict[str, object]:
        return {
            "status": "configured",
            "reason_code": "test_collaborator",
            "project_root": self.project_root,
            "storage_scope": "project",
            "repository_id": None,
            "namespace": "plans/PLAN-<plan_id>",
            "archive_namespace": "archive-plans/PLAN-<plan_id>",
        }

    @contextmanager
    def locked(self, plan_id: str) -> Generator[None, None, None]:
        with self.state.lock:
            self.state.lock_calls += 1
            yield

    def read(self, plan_id: str, *, archived: bool = False) -> bytes | None:
        with self.state.lock:
            self.state.read_calls += 1
            collection = self.state.archives if archived else self.state.plans
            return collection.get(plan_id)

    def write(
        self, plan_id: str, expected: bytes | None, content: bytes
    ) -> tuple[str, bytes | None]:
        with self.state.lock:
            current = self.state.plans.get(plan_id)
            if current != expected:
                return "conflict", current
            if self.state.write_mode == "unavailable":
                return "unavailable", current
            self.state.plans[plan_id] = content
            if self.state.write_mode == "mutated_unverified":
                return "uncertain", content[:-1]
            return "written", content

    def archive(self, plan_id: str, expected: bytes) -> tuple[str, bytes | None]:
        with self.state.lock:
            source = self.state.plans.get(plan_id)
            if source != expected:
                return "conflict", source
            if plan_id in self.state.archives:
                return "collision", source
            self.state.archives[plan_id] = source
            if self.state.archive_mode == "linked_before_unlink":
                return "uncertain", source
            del self.state.plans[plan_id]
            return "archived", source


class _FilesystemMemoryManager:
    def __init__(self, memory_root: Path) -> None:
        self._project_memory_dir = memory_root

    def _check_not_ignored(self, memory_name: str) -> None:
        del memory_name

    def _check_write_access(self, memory_name: str, write: bool) -> None:
        del memory_name, write

    def get_memory_file_path(self, memory_name: str) -> Path:
        path = self._project_memory_dir / f"{memory_name}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        return path


def _record(
    record_id: str,
    kind: str,
    text: str | None = None,
    *,
    outcome: str | None = None,
    resolves: str | None = None,
    supersedes: str | None = None,
    supersedes_reason: str | None = None,
) -> dict[str, object]:
    return {
        "record_id": record_id,
        "kind": kind,
        "text": text or f"Text for {record_id}",
        "sources": ["verified user/task context"],
        "outcome": outcome,
        "resolves_blocker_id": resolves,
        "supersedes_id": supersedes,
        "supersedes_reason": supersedes_reason,
    }


def _update(
    project: str,
    plan_id: str,
    expected: str | None,
    operation_id: str,
    *records: dict[str, object],
) -> dict[str, object]:
    return {
        "project_root": project,
        "plan_id": plan_id,
        "expected_revision": expected,
        "request_id": operation_id,
        "records": list(records),
    }


def _complete(
    project: str,
    plan_id: str,
    expected: str,
    operation_id: str,
    evidence: list[dict[str, str]],
    *records: dict[str, object],
) -> dict[str, object]:
    return {
        "project_root": project,
        "plan_id": plan_id,
        "expected_revision": expected,
        "request_id": operation_id,
        "criterion_evidence": evidence,
        "records": list(records),
    }


def _revision(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _service(
    tmp_path, state: _State | None = None
) -> tuple[TaskPlanService, _TestSerenaMemoryStore]:
    root = str(tmp_path.resolve())
    store = _TestSerenaMemoryStore(root, state)
    return TaskPlanService(store), store


def _filesystem_service(tmp_path) -> tuple[TaskPlanService, SerenaMemoryStore]:
    project_root = tmp_path / "project"
    project_root.mkdir()
    memory_root = tmp_path / "serena-memory"
    memory_root.mkdir()
    store = object.__new__(SerenaMemoryStore)
    store.project_root = str(project_root.resolve())
    store.memory_root = memory_root.resolve()
    store._manager = _FilesystemMemoryManager(store.memory_root)
    return TaskPlanService(store), store


def test_update_preserves_legacy_bytes_appends_records_and_supersedes_immutably(tmp_path) -> None:
    service, store = _service(tmp_path)
    plan_id = "legacy-plan"
    legacy = b"# Existing plan\r\nDo not normalize these bytes.\r\n"
    store.state.plans[plan_id] = legacy
    first_request = _update(
        store.project_root,
        plan_id,
        _revision(legacy),
        "op-legacy-1",
        _record("criterion-1", "criterion"),
        _record("verification-old", "verification", outcome="passed"),
    )

    first = service.update(first_request)
    assert first["status"] == "updated"
    assert first["project_root"] == store.project_root
    assert first["memory_name"] == "plans/PLAN-legacy-plan"
    assert store.state.plans[plan_id].startswith(legacy)
    first_snapshot = _parse_snapshot(store.state.plans[plan_id], plan_id, store.project_root)

    second = service.update(
        _update(
            store.project_root,
            plan_id,
            first["current_revision"],
            "op-legacy-2",
            _record(
                "verification-new",
                "verification",
                outcome="failed",
                supersedes="verification-old",
                supersedes_reason="A new verification replaced the old result.",
            ),
        )
    )
    assert second["status"] == "updated"
    snapshot = _parse_snapshot(store.state.plans[plan_id], plan_id, store.project_root)
    assert snapshot.legacy == legacy
    assert first_snapshot.records["verification-old"] == snapshot.records["verification-old"]
    assert "verification-old" in snapshot.records
    assert "verification-old" not in snapshot.active_ids
    assert "verification-new" in snapshot.active_ids


def test_request_replay_conflict_and_stale_revision_are_distinct(tmp_path) -> None:
    service, store = _service(tmp_path)
    plan_id = "replay-plan"
    request = _update(
        store.project_root,
        plan_id,
        None,
        "op-create",
        _record("goal-1", "goal"),
    )
    created = service.update(request)
    assert created["status"] == "updated"

    replay = service.update(request)
    assert replay["status"] == "replayed"
    assert replay["replayed"] is True
    assert replay["current_revision"] == created["current_revision"]

    conflict = service.update(
        _update(
            store.project_root,
            plan_id,
            None,
            "op-create",
            _record("goal-1", "goal", text="Different operation with the same ID."),
        )
    )
    assert conflict["status"] == "conflict"
    assert conflict["reason"] == "operation_id_conflict"

    stale = service.update(
        _update(
            store.project_root,
            plan_id,
            "0" * 64,
            "op-stale",
            _record("goal-2", "goal"),
        )
    )
    assert stale["status"] == "conflict"
    assert stale["reason"] == "stale_revision"
    assert stale["current_revision"] == created["current_revision"]


def test_project_scope_mismatch_has_no_lock_read_or_write_effect(tmp_path) -> None:
    service, store = _service(tmp_path)
    result = service.update(
        _update(
            "/tmp/different-project",
            "scoped-plan",
            None,
            "op-wrong-project",
            _record("goal-1", "goal"),
        )
    )
    assert result["status"] == "conflict"
    assert result["reason"] == "project_scope_mismatch"
    assert result["project_root"] == store.project_root
    assert store.state.lock_calls == 0
    assert store.state.read_calls == 0
    assert store.state.plans == {}


def test_completion_requires_passed_evidence_and_unique_criterion_mapping(tmp_path) -> None:
    service, store = _service(tmp_path)
    plan_id = "complete-plan"
    created = service.update(
        _update(
            store.project_root,
            plan_id,
            None,
            "op-create",
            _record("criterion-1", "criterion"),
            _record("verification-1", "verification", outcome="failed"),
        )
    )
    before = store.state.plans[plan_id]
    failed = service.complete(
        _complete(
            store.project_root,
            plan_id,
            created["current_revision"],
            "op-failed-evidence",
            [{"criterion_id": "criterion-1", "verification_id": "verification-1"}],
            _record("result-1", "result"),
        )
    )
    assert failed["reason"] == "verification_not_passed"
    assert store.state.plans[plan_id] == before

    resolved = service.update(
        _update(
            store.project_root,
            plan_id,
            created["current_revision"],
            "op-resolve",
            _record(
                "verification-2",
                "verification",
                outcome="passed",
                supersedes="verification-1",
                supersedes_reason="The failed run was superseded by a passing rerun.",
            ),
        )
    )
    duplicate = service.complete(
        _complete(
            store.project_root,
            plan_id,
            resolved["current_revision"],
            "op-duplicate-map",
            [
                {"criterion_id": "criterion-1", "verification_id": "verification-2"},
                {"criterion_id": "criterion-1", "verification_id": "verification-2"},
            ],
            _record("result-2", "result"),
        )
    )
    assert duplicate["reason"] == "duplicate_criterion_mapping"
    assert store.state.plans[plan_id] != before

    completed_request = _complete(
        store.project_root,
        plan_id,
        resolved["current_revision"],
        "op-complete",
        [{"criterion_id": "criterion-1", "verification_id": "verification-2"}],
        _record("result-3", "result"),
        _record("limitation-1", "limitation"),
    )
    completed = service.complete(completed_request)
    assert completed["status"] == "completed"
    assert completed["plan_state"] == "completed"
    snapshot = _parse_snapshot(store.state.plans[plan_id], plan_id, store.project_root)
    assert snapshot.completed is True

    replay = service.complete(completed_request)
    assert replay["status"] == "replayed"
    rejected_update = service.update(
        _update(
            store.project_root,
            plan_id,
            completed["current_revision"],
            "op-after-complete",
            _record("progress-1", "progress"),
        )
    )
    assert rejected_update["reason"] == "plan_completed"


def test_completion_blocks_unresolved_blockers_and_requires_active_criteria(tmp_path) -> None:
    service, store = _service(tmp_path)
    plan_id = "blocked-plan"
    created = service.update(
        _update(
            store.project_root,
            plan_id,
            None,
            "op-create",
            _record("goal-1", "goal"),
            _record("blocker-1", "blocker"),
        )
    )
    request = _complete(
        store.project_root,
        plan_id,
        created["current_revision"],
        "op-complete",
        [],
        _record("result-1", "result"),
    )
    blocked = service.complete(request)
    assert blocked["reason"] == "unresolved_blockers"

    resolved = service.update(
        _update(
            store.project_root,
            plan_id,
            created["current_revision"],
            "op-resolve",
            _record("resolution-1", "resolution", resolves="blocker-1"),
        )
    )
    no_criterion = service.complete(
        _complete(
            store.project_root,
            plan_id,
            resolved["current_revision"],
            "op-no-criterion",
            [],
            _record("result-2", "result"),
        )
    )
    assert no_criterion["reason"] == "active_criterion_required"


def test_archive_is_no_clobber_and_archived_id_cannot_be_resurrected(tmp_path) -> None:
    service, store = _service(tmp_path)
    plan_id = "archive-plan"
    created = service.update(
        _update(
            store.project_root,
            plan_id,
            None,
            "op-create",
            _record("criterion-1", "criterion"),
            _record("verification-1", "verification", outcome="passed"),
        )
    )
    completed_request = _complete(
        store.project_root,
        plan_id,
        created["current_revision"],
        "op-complete",
        [{"criterion_id": "criterion-1", "verification_id": "verification-1"}],
        _record("result-1", "result"),
    )
    completed = service.complete(completed_request)
    source = store.state.plans[plan_id]
    store.state.archives[plan_id] = source

    collision = service.archive(
        {
            "project_root": store.project_root,
            "plan_id": plan_id,
            "expected_revision": completed["current_revision"],
        }
    )
    assert collision["status"] == "conflict"
    assert collision["reason"] == "archive_collision"
    assert store.state.plans[plan_id] == source
    assert store.state.archives[plan_id] == source

    del store.state.archives[plan_id]
    archived = service.archive(
        {
            "project_root": store.project_root,
            "plan_id": plan_id,
            "expected_revision": completed["current_revision"],
        }
    )
    assert archived["status"] == "archived"
    assert archived["memory_name"] == "archive-plans/PLAN-archive-plan"
    assert plan_id not in store.state.plans
    assert store.state.archives[plan_id] == source

    replay = service.archive(
        {
            "project_root": store.project_root,
            "plan_id": plan_id,
            "expected_revision": completed["current_revision"],
        }
    )
    assert replay["status"] == "already_archived"
    assert replay["replayed"] is True
    completion_replay = service.complete(completed_request)
    assert completion_replay["status"] == "replayed"

    resurrection = service.update(
        _update(
            store.project_root,
            plan_id,
            None,
            "op-resurrect",
            _record("goal-2", "goal"),
        )
    )
    assert resurrection["reason"] == "plan_already_archived"
    assert plan_id not in store.state.plans
    assert store.state.archives[plan_id] == source


def test_uncertain_write_and_archive_interruption_preserve_state_for_reconciliation(
    tmp_path,
) -> None:
    service, store = _service(tmp_path)
    store.state.write_mode = "mutated_unverified"
    uncertain = service.update(
        _update(
            store.project_root,
            "uncertain-write",
            None,
            "op-write",
            _record("goal-1", "goal"),
        )
    )
    assert uncertain["status"] == "uncertain"
    assert uncertain["reconciliation_status"] == "required"
    assert "uncertain-write" in store.state.plans

    store.state.write_mode = "normal"
    plan_id = "uncertain-archive"
    created = service.update(
        _update(
            store.project_root,
            plan_id,
            None,
            "op-create",
            _record("criterion-1", "criterion"),
            _record("verification-1", "verification", outcome="passed"),
        )
    )
    completed = service.complete(
        _complete(
            store.project_root,
            plan_id,
            created["current_revision"],
            "op-complete",
            [{"criterion_id": "criterion-1", "verification_id": "verification-1"}],
            _record("result-1", "result"),
        )
    )
    source = store.state.plans[plan_id]
    store.state.archive_mode = "linked_before_unlink"
    interrupted = service.archive(
        {
            "project_root": store.project_root,
            "plan_id": plan_id,
            "expected_revision": completed["current_revision"],
        }
    )
    assert interrupted["status"] == "uncertain"
    assert interrupted["reconciliation_status"] == "required"
    assert store.state.plans[plan_id] == source
    assert store.state.archives[plan_id] == source


def test_two_services_serialize_updates_and_reject_stale_second_revision(tmp_path) -> None:
    root = str(tmp_path.resolve())
    state = _State()
    service_a = TaskPlanService(_TestSerenaMemoryStore(root, state))
    service_b = TaskPlanService(_TestSerenaMemoryStore(root, state))
    created = service_a.update(
        _update(root, "concurrent-plan", None, "op-create", _record("goal-1", "goal"))
    )
    expected = created["current_revision"]
    requests = [
        _update(root, "concurrent-plan", expected, "op-a", _record("progress-a", "progress")),
        _update(root, "concurrent-plan", expected, "op-b", _record("progress-b", "progress")),
    ]

    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(
                lambda pair: pair[0].update(pair[1]),
                [(service_a, requests[0]), (service_b, requests[1])],
            )
        )
    assert sorted(result["status"] for result in results) == ["conflict", "updated"]
    final = _parse_snapshot(state.plans["concurrent-plan"], "concurrent-plan", root)
    assert len(final.records) == 2


def test_filesystem_store_marks_post_write_task_plan_failure_uncertain(
    tmp_path, monkeypatch
) -> None:
    service, store = _filesystem_service(tmp_path)
    original_read = store._read_path
    read_count = 0

    def fail_post_write_readback(path: Path) -> bytes | None:
        nonlocal read_count
        read_count += 1
        if read_count == 3:
            raise TaskPlanFailure("injected_post_write_readback_failure", "unavailable")
        return original_read(path)

    monkeypatch.setattr(store, "_read_path", fail_post_write_readback)
    receipt = service.update(
        _update(
            store.project_root,
            "post-write-readback",
            None,
            "op-create",
            _record("goal-1", "goal"),
        )
    )

    target = store._fixed_path("post-write-readback", False)
    assert receipt["status"] == "uncertain"
    assert receipt["reconciliation_status"] == "required"
    assert target.is_file()
    assert b"~~~json task-plan-event-v1\n" in target.read_bytes()


def test_filesystem_store_marks_post_link_task_plan_failure_uncertain(
    tmp_path, monkeypatch
) -> None:
    service, store = _filesystem_service(tmp_path)
    plan_id = "post-link-readback"
    created = service.update(
        _update(
            store.project_root,
            plan_id,
            None,
            "op-create",
            _record("criterion-1", "criterion"),
            _record("verification-1", "verification", outcome="passed"),
        )
    )
    completed = service.complete(
        _complete(
            store.project_root,
            plan_id,
            created["current_revision"],
            "op-complete",
            [{"criterion_id": "criterion-1", "verification_id": "verification-1"}],
            _record("result-1", "result"),
        )
    )
    assert completed["status"] == "completed"
    source = store._fixed_path(plan_id, False)
    target = store._fixed_path(plan_id, True)
    source_bytes = source.read_bytes()
    original_read = store._read_path
    target_read_failed = False

    def fail_first_post_link_readback(path: Path) -> bytes | None:
        nonlocal target_read_failed
        if path == target and path.exists() and not target_read_failed:
            target_read_failed = True
            raise TaskPlanFailure("injected_post_link_readback_failure", "unavailable")
        return original_read(path)

    monkeypatch.setattr(store, "_read_path", fail_first_post_link_readback)
    receipt = service.archive(
        {
            "project_root": store.project_root,
            "plan_id": plan_id,
            "expected_revision": completed["current_revision"],
        }
    )

    assert receipt["status"] == "uncertain"
    assert receipt["reconciliation_status"] == "required"
    assert target_read_failed
    assert source.read_bytes() == source_bytes
    assert target.read_bytes() == source_bytes


def test_unavailable_completion_reports_confirmed_prewrite_state(tmp_path) -> None:
    service, store = _service(tmp_path)
    plan_id = "completion-no-effect"
    created = service.update(
        _update(
            store.project_root,
            plan_id,
            None,
            "op-create",
            _record("criterion-1", "criterion"),
            _record("verification-1", "verification", outcome="passed"),
        )
    )
    before = store.state.plans[plan_id]
    store.state.write_mode = "unavailable"

    receipt = service.complete(
        _complete(
            store.project_root,
            plan_id,
            created["current_revision"],
            "op-complete",
            [{"criterion_id": "criterion-1", "verification_id": "verification-1"}],
            _record("result-1", "result"),
        )
    )

    assert receipt["status"] == "unavailable"
    assert receipt["plan_state"] == "in_progress"
    assert store.state.plans[plan_id] == before


def test_filesystem_store_accepts_manager_path_alias_resolving_to_bound_root(tmp_path) -> None:
    service, store = _filesystem_service(tmp_path)
    alias_root = tmp_path / "serena-memory-alias"
    alias_root.symlink_to(store.memory_root, target_is_directory=True)
    store._manager = _FilesystemMemoryManager(alias_root)

    receipt = service.update(
        _update(
            store.project_root,
            "path-alias",
            None,
            "op-create",
            _record("goal-1", "goal"),
        )
    )

    target = store.memory_root / "plans" / "PLAN-path-alias.md"
    assert receipt["status"] == "updated"
    assert target.is_file()

"""文件系统存储的写后不确定性及路径别名。"""

from __future__ import annotations

from pathlib import Path

from support.task_plan_scenarios import (
    _complete,
    _filesystem_service,
    _FilesystemMemoryManager,
    _record,
    _update,
)

from token_io_decoupling_tools.task_plan_core import (
    TaskPlanFailure,
)


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

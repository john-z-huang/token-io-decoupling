"""任务计划更新、幂等重放、范围及并发版本冲突。"""

from __future__ import annotations

from support.task_plan_scenarios import (
    _record,
    _revision,
    _service,
    _State,
    _TestSerenaMemoryStore,
    _update,
)

from token_io_decoupling_tools.task_plan_core import (
    TaskPlanService,
    _parse_snapshot,
)


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

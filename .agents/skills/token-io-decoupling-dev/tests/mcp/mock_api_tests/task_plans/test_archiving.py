"""归档冲突及写入、归档中断后的状态保留。"""

from __future__ import annotations

from support.task_plan_scenarios import (
    _complete,
    _record,
    _service,
    _update,
)


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

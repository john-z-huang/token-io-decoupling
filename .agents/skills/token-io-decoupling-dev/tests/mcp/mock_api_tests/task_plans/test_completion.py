"""完成计划所需的证据映射、阻塞项及写入前状态。"""

from __future__ import annotations

from support.task_plan_scenarios import (
    _complete,
    _record,
    _service,
    _update,
)

from token_io_decoupling_tools.task_plan_core import (
    _parse_snapshot,
)


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

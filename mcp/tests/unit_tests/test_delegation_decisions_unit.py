from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import pytest
from token_io_decoupling_core.models import CodingMode, ModeCount, SemanticRef
from token_io_decoupling_core.rules import RuleLoader
from token_io_decoupling_core.state_models import (
    AllocationRole,
    AllocationStatus,
    EpochSnapshot,
    NativeAllocation,
    NativeWorkflowSnapshot,
)
from token_io_decoupling_workflow.delegation_decisions import (
    ChildCandidate,
    ChildCandidateSelectionInput,
    ChildRoleSelectionInput,
    DelegationDecisionSelector,
    OutputTokenRoutingInput,
)

_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]

_TASK_HASH = "1" * 64

_FACT_HASH = "2" * 64


def _base(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "task_id": "issue-147",
        "task_summary": "Choose a safe current-session executor for the released work.",
        "reviewed_context": "The work is released and needs a concrete implementation slice.",
        "context_input_hash": _TASK_HASH,
        "fact_revision": 3,
        "fact_fingerprint": _FACT_HASH,
        "forked_session": False,
        "mode_reselected_after_fork": False,
        "outbound_data_permitted": True,
    }
    values.update(overrides)
    return values


def _selector(client_factory: Any = None, rules: Any = None) -> DelegationDecisionSelector:
    return DelegationDecisionSelector(
        rules or RuleLoader(repository_root=_REPOSITORY_ROOT),
        client_factory=client_factory,
    )


def _candidate(
    ref: str,
    role: AllocationRole,
    *,
    availability: Literal["idle", "busy", "unavailable"] = "idle",
    same_session: bool = True,
    responsibility: bool = True,
    capability: bool = True,
    permission: bool = True,
    context: str | None = None,
) -> ChildCandidate:
    return ChildCandidate(
        candidate_ref=ref,
        role=role,
        responsibility_match=responsibility,
        capability_match=capability,
        permission_allows=permission,
        same_current_session=same_session,
        availability=availability,
        responsibility_summary=f"{role.value} responsibility matches this task.",
        capability_summary="The required implementation capability is present.",
        permission_summary="The candidate has permission for this released slice.",
        task_relevant_context=context or f"Current context for {ref} directly supports the task.",
    )


def _child_payload(
    *candidates: ChildCandidate, **overrides: object
) -> ChildCandidateSelectionInput:
    values = _base(mode=CodingMode.MULTI_AGENT, candidates=list(candidates))
    values.update(overrides)
    return ChildCandidateSelectionInput.model_validate(values)


def _role_payload(**overrides: object) -> ChildRoleSelectionInput:
    values: dict[str, object] = {
        "mode": CodingMode.MULTI_AGENT,
        "created_roles": [],
        "reserved_roles": [],
        "available_slots": 1,
        "user_explicit_create_instruction": False,
    }
    values.update(overrides)
    return ChildRoleSelectionInput.model_validate(_base(**values))


def test_unique_eligible_candidate_is_direct_and_waits_if_busy() -> None:
    result = _selector().select_child_candidate(
        _child_payload(
            _candidate("only-child", AllocationRole.CONTEXT_BOOTSTRAP_REFRESH, availability="busy")
        )
    )

    assert (result.status, result.suggested_value, result.next_action) == (
        "available",
        "only-child",
        "wait_until_selected_child_is_idle",
    )


def test_single_idle_candidate_among_multiple_eligible_is_direct() -> None:
    result = _selector().select_child_candidate(
        _child_payload(
            _candidate("idle-child", AllocationRole.CONTEXT_BOOTSTRAP_REFRESH),
            _candidate("busy-primary", AllocationRole.PRIMARY_OUTPUT, availability="busy"),
        )
    )

    assert (result.status, result.reason, result.suggested_value) == (
        "available",
        "single_idle_candidate",
        "idle-child",
    )


def test_role_selection_requires_fresh_mode_after_fork_before_decisions() -> None:
    calls: list[bool] = []
    payload = _role_payload(forked_session=True, mode_reselected_after_fork=False)

    result = _selector(lambda *_: calls.append(True)).select_child_role(payload)

    assert (result.status, result.reason) == ("blocked", "fork_requires_fresh_mode_selection")
    assert calls == []


def test_role_selection_zero_budget_requests_user_approval_before_decisions() -> None:
    calls: list[bool] = []
    payload = _role_payload(available_slots=0)

    result = _selector(lambda *_: calls.append(True)).select_child_role(payload)

    assert (result.status, result.reason, result.next_action) == (
        "blocked",
        "budget_approval_required",
        "request_explicit_user_approval_for_one_different_role_slot",
    )
    assert calls == []


def test_role_selection_all_roles_occupied_does_not_request_more_budget() -> None:
    calls: list[bool] = []
    payload = _role_payload(created_roles=list(AllocationRole), available_slots=0)

    result = _selector(lambda *_: calls.append(True)).select_child_role(payload)

    assert (result.status, result.reason, result.next_action) == (
        "blocked",
        "all_unique_roles_are_occupied",
        "root_review",
    )
    assert result.suggested_value is None
    assert calls == []


def test_role_selection_outbound_permission_blocks_before_decisions() -> None:
    calls: list[bool] = []
    payload = _role_payload(outbound_data_permitted=False)

    result = _selector(lambda *_: calls.append(True)).select_child_role(payload)

    assert (result.status, result.reason) == ("blocked", "outbound_data_not_permitted")
    assert calls == []


def test_native_snapshot_rejects_duplicate_role_and_child_identities() -> None:
    def snapshot(allocations: list[NativeAllocation]) -> NativeWorkflowSnapshot:
        return NativeWorkflowSnapshot(
            project_id="project",
            root_session_id="root",
            run_id="run",
            mode_count=ModeCount(mode=CodingMode.MULTI_AGENT, child_count=len(allocations)),
            mode_source="explicit",
            lifecycle="pending",
            source=SemanticRef(uri="memory://contract", content_hash="a" * 64),
            revision=0,
            allocations=allocations,
            epochs=EpochSnapshot(implementation_content=0, documentation=0, git_metadata=0),
        )

    duplicate_role = [
        NativeAllocation(
            allocation_id="slot-1",
            role=AllocationRole.PRIMARY_OUTPUT,
            worker_session_id=None,
            status=AllocationStatus.RESERVED,
        ),
        NativeAllocation(
            allocation_id="slot-2",
            role=AllocationRole.PRIMARY_OUTPUT,
            worker_session_id=None,
            status=AllocationStatus.RESERVED,
        ),
    ]
    with pytest.raises(ValueError, match="roles must be unique"):
        snapshot(duplicate_role)

    duplicate_child = [
        NativeAllocation(
            allocation_id="slot-1",
            role=AllocationRole.PRIMARY_OUTPUT,
            worker_session_id="child-session",
            status=AllocationStatus.BOUND,
        ),
        NativeAllocation(
            allocation_id="slot-2",
            role=AllocationRole.CONTEXT_BOOTSTRAP_REFRESH,
            worker_session_id="child-session",
            status=AllocationStatus.BOUND,
        ),
    ]
    with pytest.raises(ValueError, match="Session IDs must be unique"):
        snapshot(duplicate_child)


@pytest.mark.parametrize("mode", [CodingMode.SINGLE_AGENT, CodingMode.MULTI_AGENT])
@pytest.mark.parametrize("executor", ["root", "sub_agent"])
@pytest.mark.parametrize("outbound_data_permitted", [False, True])
def test_explicit_user_executor_takes_priority_over_output_token_advice(
    mode: CodingMode,
    executor: Literal["root", "sub_agent"],
    outbound_data_permitted: bool,
) -> None:
    factory_calls: list[bool] = []
    payload = OutputTokenRoutingInput.model_validate(
        _base(
            mode=mode,
            requested_output_shape="Detailed release notes",
            expected_output_volume="Several long sections",
            idle_suitable_child_count=0,
            busy_suitable_child_count=1 if mode is CodingMode.MULTI_AGENT else 0,
            explicit_user_executor=executor,
            outbound_data_permitted=outbound_data_permitted,
        )
    )

    result = _selector(lambda *_: factory_calls.append(True)).assess_output_tokens(payload)

    assert factory_calls == []
    if mode is CodingMode.SINGLE_AGENT and executor == "sub_agent":
        assert (result.status, result.reason, result.next_action) == (
            "blocked",
            "single_agent_mode_has_no_child_executor",
            "review_user_instruction_against_locked_session_mode",
        )
    else:
        assert (result.status, result.reason, result.next_action) == (
            "skipped",
            "explicit_user_executor_instruction",
            "honor_explicit_user_executor_without_output_size_advice",
        )

"""筛选当前会话候选，生成复用、回退或等待建议。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from token_io_decoupling_core.models import CodingMode
from token_io_decoupling_core.workflow_contracts.vocabulary import AllocationRole

from .models import (
    _SESSION_POLICY,
    _TASK_POLICY,
    ChildCandidate,
    ChildCandidateSelectionInput,
    DelegationDecisionResult,
    _fallback_is_allowed,
    _result_base,
    _session_guard,
)

if TYPE_CHECKING:
    from .selector import DelegationDecisionSelector


def candidate_fallback(
    result: DelegationDecisionResult, eligible: list[ChildCandidate]
) -> DelegationDecisionResult:
    if result.status == "stale" or not _fallback_is_allowed(result.reason):
        return result
    primary = next(
        (candidate for candidate in eligible if candidate.role is AllocationRole.PRIMARY_OUTPUT),
        None,
    )
    if primary is None:
        return result.model_copy(
            update={
                "status": "blocked",
                "fallback_value": None,
                "next_action": "unresolved_root_review_no_default_executor",
            }
        )
    return result.model_copy(
        update={
            "status": "fallback",
            "fallback_value": primary.candidate_ref,
            "next_action": (
                "use_primary_after_root_review"
                if primary.availability == "idle"
                else "wait_until_primary_is_idle"
            ),
        }
    )


def explicit_candidate_result(
    payload: ChildCandidateSelectionInput,
    base: DelegationDecisionResult,
    eligible: list[ChildCandidate],
) -> DelegationDecisionResult:
    selected = next(
        (item for item in eligible if item.candidate_ref == payload.explicit_user_candidate_ref),
        None,
    )
    if selected is None:
        return base.model_copy(
            update={
                "status": "blocked",
                "reason": "explicit_candidate_is_not_eligible_current_session_child",
                "next_action": "review_scope_permission_and_current_session_identity",
            }
        )
    return _candidate_result(base, selected, "explicit_user_candidate_instruction")


def select_child_candidate(
    service: DelegationDecisionSelector, payload: ChildCandidateSelectionInput
) -> DelegationDecisionResult:
    """先筛选当前合格候选，再判断复用或等待；返回前复核事实新鲜度。"""
    policies = service._load_policies((_TASK_POLICY, _SESSION_POLICY))
    base = _result_base("child_candidate", payload, policies)
    if policies is None:
        return base.model_copy(update={"status": "blocked", "reason": "policy_unavailable"})
    session_guard = _session_guard(payload)
    if session_guard is not None:
        return base.model_copy(update={"status": "blocked", "reason": session_guard})
    if payload.mode is CodingMode.SINGLE_AGENT:
        return base.model_copy(
            update={
                "status": "blocked",
                "reason": "single_agent_mode_has_no_child_candidate",
                "next_action": "keep_work_with_root_subject_to_output_token_routing",
            }
        )
    eligible = [candidate for candidate in payload.candidates if candidate.eligible]
    if payload.explicit_user_candidate_ref is not None:
        return service._explicit_candidate_result(payload, base, eligible)
    if not eligible:
        return base.model_copy(
            update={
                "status": "blocked",
                "reason": "no_eligible_current_session_candidate",
                "next_action": "root_review_or_create_through_role_and_budget_gates",
            }
        )
    if len(eligible) == 1:
        return _candidate_result(base, eligible[0], "single_eligible_candidate")

    idle = [candidate for candidate in eligible if candidate.availability == "idle"]
    if not idle:
        return base.model_copy(
            update={
                "status": "blocked",
                "reason": "all_eligible_candidates_are_busy",
                "next_action": "wait_until_a_suitable_current_session_child_is_idle",
            }
        )
    if len(idle) == 1:
        return _candidate_result(base, idle[0], "single_idle_candidate")

    idle_primary = next(
        (candidate for candidate in idle if candidate.role is AllocationRole.PRIMARY_OUTPUT),
        None,
    )
    candidate_pool = [idle_primary] if idle_primary is not None else idle
    choice_ids = [candidate.candidate_ref for candidate in candidate_pool]
    choices = [*choice_ids, "insufficient_evidence"]
    result = service._decide(
        "child_candidate",
        payload,
        policies,
        [_TASK_POLICY, _SESSION_POLICY],
        choices,
        {"child_candidate": set(choices)},
        eligible_ids=set(choice_ids),
    )
    if result.status == "available":
        selected = next(
            candidate
            for candidate in candidate_pool
            if candidate.candidate_ref == result.suggested_value
        )
        return _candidate_result(result, selected, "decision_suggestion")
    return service._candidate_fallback(result, eligible)


def _candidate_result(
    base: DelegationDecisionResult, candidate: ChildCandidate, reason: str
) -> DelegationDecisionResult:
    return base.model_copy(
        update={
            "status": "skipped" if reason.startswith("explicit_user") else "available",
            "reason": reason,
            "suggested_value": candidate.candidate_ref,
            "next_action": (
                "use_selected_current_session_child"
                if candidate.availability == "idle"
                else "wait_until_selected_child_is_idle"
            ),
        }
    )

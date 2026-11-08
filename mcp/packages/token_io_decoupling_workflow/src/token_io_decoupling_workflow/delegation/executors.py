"""根据会话模式、明确指令和当前事实生成执行者建议。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from token_io_decoupling_core.models import CodingMode

from .models import (
    _TASK_POLICY,
    DelegationDecisionResult,
    ExecutorSelectionInput,
    _result_base,
    _session_guard,
)

if TYPE_CHECKING:
    from .selector import DelegationDecisionSelector


def select_executor(
    service: DelegationDecisionSelector, payload: ExecutorSelectionInput
) -> DelegationDecisionResult:
    """结合锁定模式与明确用户指令判断执行者，不授予实际派发权限。"""
    policies = service._load_policies((_TASK_POLICY,))
    base = _result_base("executor", payload, policies)
    if policies is None:
        return base.model_copy(update={"status": "blocked", "reason": "policy_unavailable"})
    session_guard = _session_guard(payload)
    if session_guard is not None:
        return base.model_copy(update={"status": "blocked", "reason": session_guard})
    if payload.explicit_user_executor is not None:
        if (
            payload.explicit_user_executor == "sub_agent"
            and payload.mode is CodingMode.SINGLE_AGENT
        ):
            return base.model_copy(
                update={
                    "status": "blocked",
                    "reason": "single_agent_mode_conflicts_with_explicit_child_executor",
                    "next_action": "review_user_instruction_against_locked_session_mode",
                }
            )
        action = (
            "root_may_execute_subject_to_output_token_routing"
            if payload.explicit_user_executor == "root"
            else _executor_sub_action(payload)
        )
        return base.model_copy(
            update={
                "status": "skipped",
                "reason": "explicit_user_executor_instruction",
                "suggested_value": payload.explicit_user_executor,
                "next_action": action,
            }
        )
    if payload.mode is CodingMode.SINGLE_AGENT:
        return base.model_copy(
            update={
                "status": "skipped",
                "reason": "single_agent_mode_has_no_child_executor",
                "suggested_value": "root",
                "next_action": "root_may_execute_subject_to_output_token_routing",
            }
        )
    if not payload.outbound_data_permitted:
        return base.model_copy(
            update={"status": "blocked", "reason": "outbound_data_not_permitted"}
        )
    choices = ["root", "sub_agent", "insufficient_evidence"]
    result = service._decide(
        "executor",
        payload,
        policies,
        [_TASK_POLICY],
        choices,
        {"executor": set(choices)},
    )
    if result.status != "available":
        return result
    action = (
        "root_may_execute_subject_to_output_token_routing"
        if result.suggested_value == "root"
        else _executor_sub_action(payload)
    )
    return result.model_copy(update={"next_action": action})


def _executor_sub_action(payload: ExecutorSelectionInput) -> str:
    if payload.current_session_child_count > 0:
        return "select_a_suitable_current_session_child"
    if payload.available_slots > 0:
        return "select_role_then_create_within_approved_budget"
    return "request_user_approval_for_a_different_role_or_review"

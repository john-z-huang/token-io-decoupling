"""独立评估输出规模与子代理容量，返回执行路由建议。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from token_io_decoupling_core.models import CodingMode

from .models import (
    _OUTPUT_POLICY,
    DelegationDecisionResult,
    OutputTokenRoutingInput,
    _result_base,
    _session_guard,
)

if TYPE_CHECKING:
    from .selector import DelegationDecisionSelector


def output_token_action(
    result: DelegationDecisionResult, payload: OutputTokenRoutingInput
) -> DelegationDecisionResult:
    if result.suggested_value == "no":
        action = "root_may_execute_subject_to_all_other_gates"
    elif result.suggested_value == "yes" and payload.mode is CodingMode.SINGLE_AGENT:
        action = "hold_and_report_single_agent_output_boundary"
    elif result.suggested_value == "yes" and payload.idle_suitable_child_count > 0:
        action = "select_an_idle_suitable_current_session_child"
    elif result.suggested_value == "yes":
        action = "wait_or_hold_until_a_suitable_child_is_idle"
    else:
        action = "root_review_insufficient_evidence"
    return result.model_copy(update={"next_action": action})


def assess_output_tokens(
    service: DelegationDecisionSelector, payload: OutputTokenRoutingInput
) -> DelegationDecisionResult:
    """独立判断大量输出与当前容量，不因候选繁忙而反转输出判断。"""
    policies = service._load_policies((_OUTPUT_POLICY,))
    base = _result_base("output_tokens", payload, policies)
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
                    "reason": "single_agent_mode_has_no_child_executor",
                    "next_action": "review_user_instruction_against_locked_session_mode",
                }
            )
        return base.model_copy(
            update={
                "status": "skipped",
                "reason": "explicit_user_executor_instruction",
                "next_action": "honor_explicit_user_executor_without_output_size_advice",
            }
        )
    if not payload.outbound_data_permitted:
        return base.model_copy(
            update={"status": "blocked", "reason": "outbound_data_not_permitted"}
        )
    choices = ["yes", "no", "insufficient_evidence"]
    result = service._decide(
        "output_tokens",
        payload,
        policies,
        [_OUTPUT_POLICY],
        choices,
        {"output_tokens": set(choices)},
    )
    if result.status != "available":
        return result
    return service._output_token_action(result, payload)

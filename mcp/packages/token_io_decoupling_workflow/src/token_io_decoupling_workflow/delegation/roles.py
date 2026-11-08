"""按用户明确指令、角色占用和预算生成角色选择建议。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from token_io_decoupling_core.models import CodingMode
from token_io_decoupling_core.workflow_contracts.vocabulary import AllocationRole

from .models import (
    _PRIMARY,
    _ROLE_POLICY,
    _SESSION_POLICY,
    ChildRoleSelectionInput,
    DelegationDecisionResult,
    _fallback_is_allowed,
    _result_base,
)

if TYPE_CHECKING:
    from .selector import DelegationDecisionSelector


def explicit_role_result(
    payload: ChildRoleSelectionInput,
    base: DelegationDecisionResult,
    available_roles: list[AllocationRole],
) -> DelegationDecisionResult:
    selected = payload.user_explicit_role or AllocationRole.PRIMARY_OUTPUT
    if selected not in available_roles:
        return base.model_copy(
            update={
                "status": "blocked",
                "reason": "explicit_role_already_used_or_reserved",
                "next_action": "choose_a_different_unoccupied_role_or_review",
            }
        )
    if payload.available_slots == 0:
        return base.model_copy(
            update={
                "status": "blocked",
                "reason": "budget_approval_required",
                "suggested_value": selected.value,
                "next_action": "request_explicit_user_approval_for_one_different_role_slot",
            }
        )
    return base.model_copy(
        update={
            "status": "skipped",
            "reason": "explicit_user_creation_instruction",
            "suggested_value": selected.value,
            "next_action": "root_review_then_reserve",
        }
    )


def select_child_role(
    service: DelegationDecisionSelector, payload: ChildRoleSelectionInput
) -> DelegationDecisionResult:
    """先执行模式、显式创建和同职责守卫，需要语义选择时才请求模型。"""
    policies = service._load_policies((_ROLE_POLICY, _SESSION_POLICY))
    base = _result_base("child_role", payload, policies)
    if policies is None:
        return base.model_copy(update={"status": "blocked", "reason": "policy_unavailable"})
    guard = _role_guard(payload)
    if guard is not None:
        return base.model_copy(
            update={"status": "blocked", "reason": guard[0], "next_action": guard[1]}
        )
    occupied = set(payload.created_roles) | set(payload.reserved_roles)
    available_roles = [role for role in AllocationRole if role not in occupied]
    if payload.user_explicit_create_instruction:
        return service._explicit_role_result(payload, base, available_roles)
    if not available_roles:
        return base.model_copy(
            update={"status": "blocked", "reason": "all_unique_roles_are_occupied"}
        )
    if payload.available_slots == 0:
        return base.model_copy(
            update={
                "status": "blocked",
                "reason": "budget_approval_required",
                "next_action": "request_explicit_user_approval_for_one_different_role_slot",
            }
        )
    if not payload.outbound_data_permitted:
        return base.model_copy(
            update={"status": "blocked", "reason": "outbound_data_not_permitted"}
        )
    result = service._decide(
        "child_role",
        payload,
        policies,
        [_ROLE_POLICY, _SESSION_POLICY],
        [role.value for role in available_roles] + ["insufficient_evidence"],
        {"child_role": {role.value for role in available_roles} | {"insufficient_evidence"}},
    )
    if result.status == "available":
        return result.model_copy(update={"next_action": "root_review_then_reserve"})
    if result.status == "stale" or not _fallback_is_allowed(result.reason):
        return result
    fallback_allowed = AllocationRole.PRIMARY_OUTPUT in available_roles
    if fallback_allowed:
        return result.model_copy(
            update={
                "status": "fallback",
                "fallback_value": _PRIMARY,
                "next_action": "root_review_then_use_primary_only_if_creation_is_established",
            }
        )
    return result


def _role_guard(payload: ChildRoleSelectionInput) -> tuple[str, str] | None:
    if payload.forked_session and not payload.mode_reselected_after_fork:
        return (
            "fork_requires_fresh_mode_selection",
            "reselect_mode_and_rebuild_current_session_facts",
        )
    if payload.mode is CodingMode.SINGLE_AGENT:
        return "single_agent_mode_has_no_child", "keep_work_with_root"
    return None

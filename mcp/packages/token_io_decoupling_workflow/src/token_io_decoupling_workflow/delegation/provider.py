"""单次 Decisions 请求及政策新鲜度、拒绝和选项校验。"""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any, Literal, cast

from token_io_decoupling_workflow.api_recovery import (
    classify_provider_failure,
    recovery_for_provider_failure,
    recovery_for_reason,
)
from token_io_decoupling_workflow.compiled_rules.contracts import (
    CompiledDelegationPolicy,
    RuleLoadError,
)

from .models import (
    _CHOICE_HEADINGS,
    _GENERIC_BOUNDARY_INSTRUCTIONS,
    _INSTRUCTION_HEADINGS,
    DECISIONS_MODEL,
    MAX_REQUEST_CHARS,
    ChildCandidate,
    ChildCandidateSelectionInput,
    DecisionInputBase,
    DelegationDecisionResult,
    _result_base,
)

if TYPE_CHECKING:
    from .selector import DelegationDecisionSelector


def validated_decision_result(
    response: object,
    kind: str,
    result_base: DelegationDecisionResult,
    accepted: dict[str, set[str]],
    eligible_ids: set[str] | None,
) -> DelegationDecisionResult:
    failure_reason = _decision_response_failure(response, kind)
    if failure_reason is not None:
        return _blocked_decision_result(result_base, failure_reason)
    answer = _validated_choice(response, accepted)
    if answer is None:
        return _invalid_decision_choice_result(response, kind, result_base)
    if getattr(response, "model", None) != DECISIONS_MODEL:
        return _blocked_decision_result(result_base, "invalid_response")
    if answer == "insufficient_evidence":
        return _blocked_decision_result(result_base, "insufficient_evidence")
    if eligible_ids is not None and answer not in eligible_ids:
        return _blocked_decision_result(result_base, "invalid_response")

    usage = getattr(response, "usage", None)
    total_tokens = getattr(usage, "total_tokens", None)
    if type(total_tokens) is not int or total_tokens < 0:
        total_tokens = None
    return result_base.model_copy(
        update={
            "status": "available",
            "reason": "suggestion_available",
            "suggested_value": answer,
            "model": DECISIONS_MODEL,
            "total_tokens": total_tokens,
            "recovery": None,
        }
    )


def decide(
    service: DelegationDecisionSelector,
    kind: str,
    payload: DecisionInputBase,
    policies: Mapping[str, CompiledDelegationPolicy],
    policy_names: Sequence[str],
    choices: Sequence[str],
    accepted: dict[str, set[str]],
    *,
    eligible_ids: set[str] | None = None,
) -> DelegationDecisionResult:
    base = _result_base(kind, payload, policies)
    if not payload.outbound_data_permitted:
        return base.model_copy(
            update={"status": "blocked", "reason": "outbound_data_not_permitted"}
        )
    try:
        instructions = _decision_instructions(kind, policies)
        choice_payload = _choice_payload(kind, choices, policies, payload)
    except RuleLoadError:
        return base.model_copy(update={"status": "blocked", "reason": "policy_contract_invalid"})
    decision_request = _request_input(kind, payload, policies, policy_names, choices)
    if len(decision_request) > MAX_REQUEST_CHARS:
        return base.model_copy(
            update={"status": "blocked", "reason": "request_exceeds_supported_bound"}
        )
    input_hash = hashlib.sha256(decision_request.encode("utf-8")).hexdigest()
    result_base = base.model_copy(update={"input_hash": input_hash})
    api_key = os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("OPENAI_BASE_URL")
    if not api_key or not api_key.strip() or not base_url or not base_url.strip():
        return result_base.model_copy(update={"status": "blocked", "reason": "missing_credentials"})

    client: object | None = None
    response: object | None = None
    request_failure = None
    try:
        client = service._make_client(api_key, base_url)
        response = cast(Any, client).decisions.create(
            model=DECISIONS_MODEL,
            input=decision_request,
            questions=[
                {
                    "type": "choice",
                    "name": kind,
                    "instructions": instructions,
                    "choices": choice_payload,
                }
            ],
        )
    except Exception as exc:
        request_failure = classify_provider_failure(exc)
    finally:
        close = getattr(client, "close", None)
        if callable(close):
            try:
                close()
            except Exception:
                pass

    current_policies = service._load_policies(policy_names)
    if current_policies is None or any(
        current_policies[name][1] != policies[name][1] for name in policy_names
    ):
        return result_base.model_copy(
            update={
                "status": "stale",
                "reason": "source_policy_changed_during_request",
                "recovery": recovery_for_reason("source_policy_changed_during_request"),
            }
        )
    if request_failure is not None or response is None:
        guidance = (
            recovery_for_provider_failure(request_failure)
            if request_failure is not None
            else recovery_for_reason("api_failure")
        )
        return result_base.model_copy(
            update={"status": "blocked", "reason": "api_failure", "recovery": guidance}
        )
    return service._validated_decision_result(response, kind, result_base, accepted, eligible_ids)


def _decision_response_failure(
    response: object, kind: str
) -> Literal["refusal", "incomplete_response"] | None:
    if _is_refusal(response, kind):
        return "refusal"
    response_status = getattr(response, "status", None)
    if (
        (response_status is not None and response_status != "completed")
        or getattr(response, "error", None) is not None
        or getattr(response, "incomplete_details", None) is not None
    ):
        return "incomplete_response"
    return None


def _invalid_decision_choice_result(
    response: object, kind: str, result_base: DelegationDecisionResult
) -> DelegationDecisionResult:
    return result_base.model_copy(
        update={
            "status": "blocked",
            "reason": "refusal" if _is_refusal(response, kind) else "invalid_response",
            "recovery": recovery_for_reason(
                "refusal" if _is_refusal(response, kind) else "invalid_response"
            ),
        }
    )


def _blocked_decision_result(
    base: DelegationDecisionResult, reason: str
) -> DelegationDecisionResult:
    return base.model_copy(
        update={"status": "blocked", "reason": reason, "recovery": recovery_for_reason(reason)}
    )


def _request_input(
    kind: str,
    payload: DecisionInputBase,
    policies: Mapping[str, CompiledDelegationPolicy],
    policy_names: Sequence[str],
    choices: Sequence[str],
) -> str:
    request = payload.model_dump(mode="json", exclude={"outbound_data_permitted"})
    if kind == "child_candidate" and isinstance(payload, ChildCandidateSelectionInput):
        offered_candidate_refs = set(choices) - {"insufficient_evidence"}
        request["candidates"] = [
            candidate.model_dump(mode="json")
            for candidate in payload.candidates
            if candidate.candidate_ref in offered_candidate_refs
        ]
    owner_sources = [
        {"owner": name, "text": policies[name][0], "sha256": policies[name][1]}
        for name in policy_names
    ]
    envelope = {
        "decision": kind,
        "caller_facts": request,
        "current_skill_owner_sources": owner_sources,
        "offered_choices": list(choices),
    }
    return json.dumps(envelope, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _decision_instructions(kind: str, policies: Mapping[str, CompiledDelegationPolicy]) -> str:
    owner, heading = _INSTRUCTION_HEADINGS[kind]
    owner_instructions = policies[owner].sections.get(heading)
    if not owner_instructions:
        raise RuleLoadError("required Decisions instructions are missing from the current owner")
    return f"{owner_instructions}\n\n{_GENERIC_BOUNDARY_INSTRUCTIONS}"


def _choice_payload(
    kind: str,
    choices: Sequence[str],
    policies: Mapping[str, CompiledDelegationPolicy],
    payload: DecisionInputBase,
) -> list[dict[str, str]]:
    """从当前政策生成选项；可复用候选另附当前事实，缺少解释时拒绝构造。"""
    owner, heading = _CHOICE_HEADINGS[kind]
    owner_descriptions = policies[owner].choices.get(heading)
    if not owner_descriptions:
        raise RuleLoadError("required choice descriptions are missing from the current owner")
    candidate_by_ref: dict[str, ChildCandidate] = {}
    if kind == "child_candidate" and isinstance(payload, ChildCandidateSelectionInput):
        candidate_by_ref = {
            candidate.candidate_ref: candidate
            for candidate in payload.candidates
            if candidate.eligible and candidate.availability == "idle"
        }
    choice_payload: list[dict[str, str]] = []
    for choice in choices:
        if kind == "child_candidate" and choice in candidate_by_ref:
            candidate = candidate_by_ref[choice]
            description = "\n".join(
                [
                    f"职责：{candidate.role.value}",
                    f"职责说明：{candidate.responsibility_summary}",
                    f"能力：{candidate.capability_summary}",
                    f"权限范围：{candidate.permission_summary}",
                    f"可用性：{candidate.availability}",
                    f"任务相关上下文：{candidate.task_relevant_context}",
                ]
            )
        else:
            description = owner_descriptions.get(choice, "")
        if not description:
            raise RuleLoadError("a required choice description is missing from the current owner")
        choice_payload.append({"value": choice, "description": description})
    return choice_payload


def _validated_choice(response: object, questions: dict[str, set[str]]) -> str | None:
    answers = getattr(response, "answers", None)
    if not isinstance(answers, list) or len(answers) != 1:
        return None
    answer = answers[0]
    name = getattr(answer, "name", None)
    choice = getattr(answer, "choice", None)
    if (
        getattr(answer, "type", None) != "choice"
        or name not in questions
        or not isinstance(choice, str)
        or choice not in questions[name]
    ):
        return None
    return choice


def _is_refusal(response: object, question_name: str) -> bool:
    if getattr(response, "status", None) == "refused":
        return True
    answers = getattr(response, "answers", None)
    return bool(
        isinstance(answers, list)
        and any(
            getattr(answer, "name", None) == question_name
            and getattr(answer, "type", None) == "refusal"
            for answer in answers
        )
    )

"""Opt-in live API integration tests; never run from credentials alone."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Any, cast

import pytest
from mcp import Client
from mcp.types import TextContent
from token_io_decoupling_core.models import CodingMode
from token_io_decoupling_core.rules import RuleLoader
from token_io_decoupling_core.state_models import AllocationRole
from token_io_decoupling_workflow.child_effort import (
    DECISIONS_MODEL,
    ChildEffortInput,
    ChildEffortSelector,
    Effort,
)
from token_io_decoupling_workflow.decision_context import (
    GENERATION_MODEL,
    DecisionContextGenerator,
    DecisionContextInput,
    DecisionOutputKind,
)
from token_io_decoupling_workflow.delegation_decisions import (
    ChildCandidate,
    ChildCandidateSelectionInput,
    ChildRoleSelectionInput,
    DecisionInputBase,
    DelegationDecisionResult,
    DelegationDecisionSelector,
    ExecutorSelectionInput,
    OutputTokenRoutingInput,
)

from token_io_decoupling.server import create_server

_OPT_IN_NAME = "TOKEN_IO_RUN_REAL_API"
_OPTED_IN = os.environ.get(_OPT_IN_NAME) == "1"

pytestmark = [
    pytest.mark.real_api,
    pytest.mark.skipif(
        not _OPTED_IN,
        reason=f"set {_OPT_IN_NAME}=1 to enable live OpenAI API tests",
    ),
]

_RAW_CONTENT = """Synthetic, released mechanical task fixture; it contains no real repository,
Git, LSP, host-session, or Agent observations and must not be treated as such.

User goal (synthetic): Add exactly one integer constant named MAX_RETRIES with value 0 above the
target function in src/sample.py. No other code changes are requested.
Current diff (synthetic): +# Retry policy constants
LSP observation (synthetic): src/sample.py has a module-level constants section directly above the
target function. MAX_RETRIES does not exist yet and has no existing references.
Scope (synthetic): One module-level constant in src/sample.py.
Dependencies (synthetic): none.
Risk (synthetic): A wrong value would affect only the new constant; no other behavior changes.
Uncertainty (synthetic): none.
Verification (synthetic): Confirm the exact constant value and run its direct assertion.
Previous failure evidence (synthetic): none.
Supported reasoning efforts (synthetic): low, medium.
"""

_QUESTION_GOAL = (
    "Write one concise question asking which lowest sufficient supported reasoning effort fits "
    "this exact released mechanical task."
)

_CONTEXT_GOAL = (
    "Summarize the supplied released mechanical task facts relevant to choosing the lowest "
    "sufficient supported reasoning effort, without making the choice."
)

_SUPPORTED_EFFORTS: list[Effort] = ["low", "medium"]

_SLICE_FINGERPRINT = "a" * 64


@pytest.fixture(scope="module", autouse=True)
def suppress_provider_logs():
    """Silence all logging during opt-in calls and restore the prior global threshold."""
    previous_disable = logging.root.manager.disable
    logging.disable(logging.CRITICAL)
    try:
        yield
    finally:
        logging.disable(previous_disable)


@pytest.fixture(scope="module")
def real_api_configuration() -> None:
    """Require explicit opt-in and report only missing variable names."""
    assert GENERATION_MODEL == "gpt-6-luna"
    assert DECISIONS_MODEL == "gpt-6-luna"
    missing = [
        name
        for name in ("OPENAI_API_KEY", "OPENAI_BASE_URL")
        if not os.environ.get(name, "").strip()
    ]
    if missing:
        cast(Any, pytest).fail(
            (
                f"{_OPT_IN_NAME}=1 but required environment variable(s) are missing: "
                + ", ".join(missing)
            ),
            pytrace=False,
        )


def _canonical_hash(facts: dict[str, Any]) -> str:
    canonical = json.dumps(
        facts,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _generation_input(
    output_kind: DecisionOutputKind = "decision_question",
) -> DecisionContextInput:
    return DecisionContextInput(
        raw_content=_RAW_CONTENT,
        decision_goal=(_CONTEXT_GOAL if output_kind == "decision_context" else _QUESTION_GOAL),
        output_kind=output_kind,
        outbound_data_permitted=True,
    )


def _child_input(decision_question: str) -> ChildEffortInput:
    return ChildEffortInput(
        slice_id="real-api-synthetic-slice-1",
        role="Primary Output",
        objective=(
            "Add exactly one integer constant named MAX_RETRIES with value 0 at the stated "
            "location."
        ),
        decision_question=decision_question,
        task_complexity="mechanical",
        uncertainty="none",
        scope="One module-level constant in src/sample.py.",
        dependencies="none",
        risk="A wrong value would affect only the new constant; no other behavior is changed.",
        verification_demands="Confirm the exact constant value and run its direct assertion.",
        previous_failure_evidence="none",
        slice_fingerprint=_SLICE_FINGERPRINT,
        runtime="codex",
        child_model=DECISIONS_MODEL,
        supported_efforts=_SUPPORTED_EFFORTS,
        outbound_data_permitted=True,
    )


def _assert_generated(
    result: dict[str, Any],
    expected_hash: str,
    output_kind: DecisionOutputKind = "decision_question",
) -> str:
    assert result.get("status") == "available", (
        f"decision context unavailable: status={result.get('status')} reason={result.get('reason')}"
    )
    assert result.get("reason") == "description_generated"
    assert result.get("model") == GENERATION_MODEL
    assert result.get("output_kind") == output_kind
    assert result.get("input_hash") == expected_hash
    assert result.get("missing_information") == []
    description = result.get("description")
    assert isinstance(description, str) and description.strip()
    assert len(description) <= (6000 if output_kind == "decision_context" else 1200)
    return description


def _assert_effort_result(
    result: dict[str, Any],
    request: ChildEffortInput,
    expected_hash: str,
) -> None:
    assert result.get("status") == "available", (
        f"child effort unavailable: status={result.get('status')} reason={result.get('reason')}"
    )
    assert result.get("reason") == "effort_selected"
    assert result.get("selected_effort") in request.supported_efforts
    assert result.get("model") == DECISIONS_MODEL
    assert result.get("input_hash") == expected_hash
    assert result.get("slice_fingerprint") == request.slice_fingerprint


def _delegation_context_input(raw_content: str) -> DecisionContextInput:
    return DecisionContextInput(
        raw_content=raw_content,
        decision_goal=(
            "Summarize the supplied synthetic task, release state, and session facts needed for "
            "a later routing decision. Preserve source labels and concrete identifiers. Do not "
            "choose or recommend a role or executor."
        ),
        output_kind="decision_context",
        outbound_data_permitted=True,
    )


def _generate_delegation_context(
    rules: RuleLoader,
    raw_content: str,
) -> tuple[str, str]:
    payload = _delegation_context_input(raw_content)
    expected_input_hash = _canonical_hash(
        payload.model_dump(mode="json", exclude={"outbound_data_permitted"})
    )
    expected_policy_hash = rules.load_delegation_policy("decision-context-generation")[1]

    result = DecisionContextGenerator(rules=rules).generate(payload)
    description = _assert_generated(
        result.model_dump(mode="json"),
        expected_input_hash,
        output_kind="decision_context",
    )

    assert result.source_policy_hash == expected_policy_hash
    assert rules.load_delegation_policy("decision-context-generation")[1] == expected_policy_hash
    return description, expected_input_hash


def _delegation_input_fields(
    *,
    task_id: str,
    task_summary: str,
    source_facts: str,
    generated_context: str,
    context_input_hash: str,
    mode: CodingMode,
    session_facts: dict[str, Any],
) -> dict[str, Any]:
    # These are synthetic caller facts for selector behavior; they do not prove host identity,
    # actual session state, or authorization.
    return {
        "task_id": task_id,
        "task_summary": task_summary,
        "reviewed_context": (
            "Generated context from synthetic source-labeled facts:\\n"
            f"{generated_context}\\n\\n"
            "Additional caller-supplied facts (synthetic):\\n"
            f"{source_facts}"
        ),
        "context_input_hash": context_input_hash,
        "fact_revision": 1,
        "fact_fingerprint": _canonical_hash(
            {
                "mode": mode.value,
                "session_facts": session_facts,
                "source_facts": source_facts,
            }
        ),
        "forked_session": False,
        "mode_reselected_after_fork": False,
        "outbound_data_permitted": True,
    }


def _selector_request_expectations(
    *,
    decision: str,
    payload: DecisionInputBase,
    policy_names: list[str],
    offered_choices: list[str],
    rules: RuleLoader,
) -> tuple[str, dict[str, str]]:
    owner_sources: list[dict[str, str]] = []
    policy_hashes: dict[str, str] = {}
    for name in policy_names:
        text, digest = rules.load_delegation_policy(name)
        owner_sources.append({"owner": name, "text": text, "sha256": digest})
        policy_hashes[name] = digest

    request = {
        "decision": decision,
        "caller_facts": payload.model_dump(mode="json", exclude={"outbound_data_permitted"}),
        "current_skill_owner_sources": owner_sources,
        "offered_choices": offered_choices,
    }
    return _canonical_hash(request), policy_hashes


def _assert_delegation_result(
    result: DelegationDecisionResult,
    payload: DecisionInputBase,
    *,
    decision: str,
    expected_value: str | set[str],
    expected_reason: str = "suggestion_available",
    expected_input_hash: str,
    expected_policy_hashes: dict[str, str],
    rules: RuleLoader,
) -> None:
    assert result.status == "available", (
        f"delegation decision unavailable: status={result.status} reason={result.reason}"
    )
    assert result.reason == expected_reason
    assert result.decision == decision
    if isinstance(expected_value, str):
        assert result.suggested_value == expected_value
    else:
        assert result.suggested_value in expected_value
    assert result.model == "gpt-6-luna"
    assert result.total_tokens is None or (
        type(result.total_tokens) is int and result.total_tokens >= 0
    )
    assert result.input_hash == expected_input_hash
    assert result.fact_revision == payload.fact_revision
    assert result.fact_fingerprint == payload.fact_fingerprint
    assert result.context_input_hash == payload.context_input_hash
    assert result.source_policy_hashes == expected_policy_hashes
    assert {
        name: rules.load_delegation_policy(name)[1] for name in expected_policy_hashes
    } == expected_policy_hashes


def _tool_json(result: Any) -> dict[str, Any]:
    assert not result.is_error, "workflow tool returned an MCP error"
    text_content = next((item for item in result.content if isinstance(item, TextContent)), None)
    assert text_content is not None, "workflow tool returned no text content"
    decoded = json.loads(text_content.text)
    assert isinstance(decoded, dict), "workflow tool returned an unexpected result shape"
    return decoded


def _call_workflow_tool(name: str, payload: DecisionInputBase, state_root: Path) -> dict[str, Any]:
    server = create_server(profile="workflow", state_root=state_root)

    async def call() -> dict[str, Any]:
        async with Client(server, mode="auto") as client:
            return _tool_json(
                await client.call_tool(
                    name,
                    {"payload": {"request": payload.model_dump(mode="json")}},
                )
            )

    return asyncio.run(call())


def test_real_api_generates_decision_context(real_api_configuration: None) -> None:
    del real_api_configuration
    payload = _generation_input(output_kind="decision_context")
    expected_generation_hash = _canonical_hash(
        {
            "raw_content": payload.raw_content,
            "decision_goal": payload.decision_goal,
            "output_kind": payload.output_kind,
        }
    )
    result = (
        DecisionContextGenerator(
            rules=RuleLoader(repository_root=Path(__file__).resolve().parents[3])
        )
        .generate(payload)
        .model_dump(mode="json")
    )
    _assert_generated(result, expected_generation_hash, output_kind="decision_context")


def test_real_api_selects_child_effort(real_api_configuration: None) -> None:
    del real_api_configuration
    request = _child_input(
        "Which lowest sufficient supported reasoning effort fits this released task?"
    )
    expected_effort_hash = _canonical_hash(
        request.model_dump(
            mode="json",
            exclude={"outbound_data_permitted", "slice_fingerprint"},
        )
    )
    result = ChildEffortSelector().select(request).model_dump(mode="json")
    _assert_effort_result(result, request, expected_effort_hash)


def test_real_api_mcp_generation_to_effort_decision_chain(
    real_api_configuration: None, tmp_path: Path
) -> None:
    del real_api_configuration
    generation_payload = _generation_input()
    expected_generation_hash = _canonical_hash(
        {
            "raw_content": generation_payload.raw_content,
            "decision_goal": generation_payload.decision_goal,
            "output_kind": generation_payload.output_kind,
        }
    )
    server = create_server(profile="workflow", state_root=tmp_path)

    async def call_chain() -> tuple[dict[str, Any], dict[str, Any], ChildEffortInput, str]:
        async with Client(server, mode="auto") as client:
            generated = _tool_json(
                await client.call_tool(
                    "workflow_generate_decision_context",
                    {
                        "payload": {
                            "request": generation_payload.model_dump(mode="json"),
                        }
                    },
                )
            )
            question = _assert_generated(generated, expected_generation_hash)
            child_request = _child_input(question)
            assert child_request.decision_question == generated["description"]
            expected_effort_hash = _canonical_hash(
                child_request.model_dump(
                    mode="json",
                    exclude={"outbound_data_permitted", "slice_fingerprint"},
                )
            )
            effort = _tool_json(
                await client.call_tool(
                    "workflow_select_child_effort",
                    {"payload": {"request": child_request.model_dump(mode="json")}},
                )
            )
            return generated, effort, child_request, expected_effort_hash

    generated, effort, child_request, expected_effort_hash = asyncio.run(call_chain())
    _assert_effort_result(effort, child_request, expected_effort_hash)
    assert generated["input_hash"] != effort["input_hash"]


def test_real_api_generates_context_then_selects_child_role(
    real_api_configuration: None,
) -> None:
    del real_api_configuration
    rules = RuleLoader(repository_root=Path(__file__).resolve().parents[3])
    source_facts = """Source label: synthetic test scenario; no real repository or user content.
User request (synthetic): Add `normalize_label(value: str) -> str` to `src/demo.py`.
Behavior: Trim surrounding whitespace and lowercase the label.
Root analysis (synthetic): Analysis of this bounded function is complete.
User authorization (synthetic): The user authorized the implementation outcome.
The user did not direct child creation or name a worker role.
Session facts (synthetic): Multi-Agent Coding is locked, one child slot is unused.
No role is created or reserved.
Work facts (synthetic): The implementation path is writable within scope and has no dependencies.
No documentation or separate context-refresh work is needed.
"""
    generated_context, generation_input_hash = _generate_delegation_context(rules, source_facts)
    mode = CodingMode.MULTI_AGENT
    session_facts = {
        "created_roles": [],
        "reserved_roles": [],
        "available_slots": 1,
        "user_explicit_create_instruction": False,
        "user_explicit_role": None,
    }
    payload = ChildRoleSelectionInput.model_validate(
        {
            **_delegation_input_fields(
                task_id="real-api-synthetic-child-role",
                task_summary="Select a role for one bounded synthetic implementation task.",
                source_facts=source_facts,
                generated_context=generated_context,
                context_input_hash=generation_input_hash,
                mode=mode,
                session_facts=session_facts,
            ),
            "mode": mode,
            **session_facts,
        }
    )
    policy_names = ["child-role-selection", "session-role-ownership"]
    offered_choices = [role.value for role in AllocationRole] + ["insufficient_evidence"]
    expected_input_hash, expected_policy_hashes = _selector_request_expectations(
        decision="child_role",
        payload=payload,
        policy_names=policy_names,
        offered_choices=offered_choices,
        rules=rules,
    )

    result = DelegationDecisionSelector(rules=rules).select_child_role(payload)

    assert payload.context_input_hash == generation_input_hash
    _assert_delegation_result(
        result,
        payload,
        decision="child_role",
        expected_value=AllocationRole.PRIMARY_OUTPUT.value,
        expected_input_hash=expected_input_hash,
        expected_policy_hashes=expected_policy_hashes,
        rules=rules,
    )


@pytest.mark.parametrize(
    (
        "scenario",
        "source_facts",
        "current_session_child_count",
        "available_slots",
        "expected_value",
    ),
    [
        pytest.param(
            "contract-judgment",
            """Source label: synthetic test scenario; no real repository or user content.
User request (synthetic): Decide whether an acceptance statement includes optional behavior.
Current state (synthetic): Resolve contract scope using the user's conversation context.
The deliverable is a two-sentence explanation.
Release state (synthetic): No implementation or code patch has been released.
No implementation work is required for this item.
Session state (synthetic): Multi-Agent Coding is locked, no child is assigned to this item.
One child slot is unused.
Executor instruction (synthetic): The user did not specify an executor.
""",
            0,
            1,
            "root",
            id="short-contract-judgment",
        ),
        pytest.param(
            "released-implementation",
            """Source label: synthetic test scenario; no real repository or user content.
User request (synthetic): Add `normalize_label(value: str) -> str` to `src/demo.py`.
Behavior: Trim surrounding whitespace and lowercase the label.
Analysis state (synthetic): Root completed analysis and released an exact one-file patch.
No behavior questions remain.
Current-session worker (synthetic): One current-session Primary Output child is idle.
It has relevant task context and permission to edit the synthetic target file.
Session state (synthetic): Multi-Agent Coding is locked; this is its only current child.
No additional child slot is available.
Executor instruction (synthetic): The user did not specify an executor.
This case asks which current-session executor is suitable.
It does not ask to create a child.
""",
            1,
            0,
            "sub_agent",
            id="released-patch-with-idle-primary",
        ),
    ],
)
def test_real_api_generates_context_then_selects_executor(
    real_api_configuration: None,
    scenario: str,
    source_facts: str,
    current_session_child_count: int,
    available_slots: int,
    expected_value: str,
) -> None:
    del real_api_configuration
    rules = RuleLoader(repository_root=Path(__file__).resolve().parents[3])
    generated_context, generation_input_hash = _generate_delegation_context(rules, source_facts)
    mode = CodingMode.MULTI_AGENT
    session_facts = {
        "current_session_child_count": current_session_child_count,
        "available_slots": available_slots,
        "explicit_user_executor": None,
    }
    payload = ExecutorSelectionInput.model_validate(
        {
            **_delegation_input_fields(
                task_id=f"real-api-synthetic-executor-{scenario}",
                task_summary="Choose an executor for the current synthetic work item.",
                source_facts=source_facts,
                generated_context=generated_context,
                context_input_hash=generation_input_hash,
                mode=mode,
                session_facts=session_facts,
            ),
            "mode": mode,
            **session_facts,
        }
    )
    policy_names = ["task-assignment"]
    offered_choices = ["root", "sub_agent", "insufficient_evidence"]
    expected_input_hash, expected_policy_hashes = _selector_request_expectations(
        decision="executor",
        payload=payload,
        policy_names=policy_names,
        offered_choices=offered_choices,
        rules=rules,
    )

    result = DelegationDecisionSelector(rules=rules).select_executor(payload)

    assert payload.context_input_hash == generation_input_hash
    _assert_delegation_result(
        result,
        payload,
        decision="executor",
        expected_value=expected_value,
        expected_input_hash=expected_input_hash,
        expected_policy_hashes=expected_policy_hashes,
        rules=rules,
    )


def test_real_api_mcp_selects_child(
    real_api_configuration: None,
    tmp_path: Path,
) -> None:
    del real_api_configuration
    rules = RuleLoader(repository_root=Path(__file__).resolve().parents[3])
    source_facts = (
        "Source label: synthetic test scenario; no real repository or user content.\n"
        "User request (synthetic): Extract neutral facts from a small parser source and its tests "
        "for Root's acceptance review.\n"
        "The child must report source/test observations without recommending a role, deciding "
        "semantics, or giving the final verdict.\n"
        "Session facts (synthetic): Two eligible current-session children are idle; neither is "
        "Primary Output.\n"
        "Candidate synthetic-verification-child has the exact parser source and test trace.\n"
        "Candidate synthetic-context-child has general project context and can refresh the source "
        "facts.\n"
        "Both responsibilities are suitable for this bounded read-only fact extraction.\n"
        "The user did not specify a child or candidate. No child creation is requested.\n"
    )
    generated_context, generation_input_hash = _generate_delegation_context(rules, source_facts)
    mode = CodingMode.MULTI_AGENT
    candidate_records = [
        ChildCandidate(
            candidate_ref="synthetic-verification-child",
            role=AllocationRole.CHANGE_VERIFICATION,
            responsibility_match=True,
            capability_match=True,
            permission_allows=True,
            same_current_session=True,
            availability="idle",
            responsibility_summary=(
                "May extract and verify source/test facts without accepting the work."
            ),
            capability_summary="Can cite the synthetic parser source and test observations.",
            permission_summary="Authorized for read-only fact collection; Root retains acceptance.",
            task_relevant_context=(
                "Has the exact parser source and test trace for this fact request."
            ),
        ),
        ChildCandidate(
            candidate_ref="synthetic-context-child",
            role=AllocationRole.CONTEXT_BOOTSTRAP_REFRESH,
            responsibility_match=True,
            capability_match=True,
            permission_allows=True,
            same_current_session=True,
            availability="idle",
            responsibility_summary="May refresh bounded task context from source facts.",
            capability_summary="Can collect source-labeled project context for Root review.",
            permission_summary="Authorized to read the synthetic source context only.",
            task_relevant_context="Has general context but no exact parser test trace.",
        ),
    ]
    session_facts = {
        "eligible_idle_candidate_refs": [item.candidate_ref for item in candidate_records],
        "idle_primary_available": False,
    }
    payload = ChildCandidateSelectionInput.model_validate(
        {
            **_delegation_input_fields(
                task_id="real-api-synthetic-child-candidate",
                task_summary=(
                    "Choose an eligible child to collect neutral source/test facts for Root."
                ),
                source_facts=source_facts,
                generated_context=generated_context,
                context_input_hash=generation_input_hash,
                mode=mode,
                session_facts=session_facts,
            ),
            "mode": mode,
            "candidates": [item.model_dump(mode="python") for item in candidate_records],
            "explicit_user_candidate_ref": None,
        }
    )
    policy_names = ["task-assignment", "session-role-ownership"]
    candidate_refs = {item.candidate_ref for item in candidate_records}
    offered_choices = [item.candidate_ref for item in candidate_records] + ["insufficient_evidence"]
    expected_input_hash, expected_policy_hashes = _selector_request_expectations(
        decision="child_candidate",
        payload=payload,
        policy_names=policy_names,
        offered_choices=offered_choices,
        rules=rules,
    )

    response = _call_workflow_tool("workflow_select_child", payload, tmp_path)
    result = DelegationDecisionResult.model_validate(response)

    _assert_delegation_result(
        result,
        payload,
        decision="child_candidate",
        expected_value=set(candidate_refs),
        expected_reason="decision_suggestion",
        expected_input_hash=expected_input_hash,
        expected_policy_hashes=expected_policy_hashes,
        rules=rules,
    )
    assert result.next_action == "use_selected_current_session_child"
    assert result.authority == "advisory_only"


def test_real_api_mcp_assesses_output_tokens(
    real_api_configuration: None,
    tmp_path: Path,
) -> None:
    del real_api_configuration
    rules = RuleLoader(repository_root=Path(__file__).resolve().parents[3])
    source_facts = (
        "Source label: synthetic test scenario; no real repository or user content.\n"
        "User request (synthetic): Produce a 100,000-token reference covering every "
        "standard-library module,\n"
        "with full APIs, examples, edge cases, and migration notes. "
        "The requested size is explicit.\n"
        "Session facts (synthetic): Multi-Agent Coding is locked. One suitable child is "
        "busy and none is idle.\n"
        "The user did not specify an executor. No child creation is requested by this size "
        "assessment.\n"
    )
    generated_context, generation_input_hash = _generate_delegation_context(rules, source_facts)
    mode = CodingMode.MULTI_AGENT
    session_facts = {
        "explicit_user_executor": None,
        "idle_suitable_child_count": 0,
        "busy_suitable_child_count": 1,
        "requested_output_shape": (
            "Exhaustive reference with API entries, examples, edge cases, and migration notes."
        ),
        "expected_output_volume": "Approximately 100,000 tokens.",
    }
    payload = OutputTokenRoutingInput.model_validate(
        {
            **_delegation_input_fields(
                task_id="real-api-synthetic-output-size",
                task_summary="Assess whether this explicit output request is too large for Root.",
                source_facts=source_facts,
                generated_context=generated_context,
                context_input_hash=generation_input_hash,
                mode=mode,
                session_facts=session_facts,
            ),
            "mode": mode,
            **session_facts,
        }
    )
    policy_names = ["output-token-routing"]
    offered_choices = ["yes", "no", "insufficient_evidence"]
    expected_input_hash, expected_policy_hashes = _selector_request_expectations(
        decision="output_tokens",
        payload=payload,
        policy_names=policy_names,
        offered_choices=offered_choices,
        rules=rules,
    )

    response = _call_workflow_tool("workflow_assess_output_tokens", payload, tmp_path)
    result = DelegationDecisionResult.model_validate(response)

    _assert_delegation_result(
        result,
        payload,
        decision="output_tokens",
        expected_value="yes",
        expected_input_hash=expected_input_hash,
        expected_policy_hashes=expected_policy_hashes,
        rules=rules,
    )
    assert result.next_action == "wait_or_hold_until_a_suitable_child_is_idle"
    assert result.authority == "advisory_only"

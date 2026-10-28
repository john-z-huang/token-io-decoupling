from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Literal

import httpx2
import pytest
from openai import OpenAI
from token_io_decoupling_core.models import CodingMode
from token_io_decoupling_core.rules import RuleLoader
from token_io_decoupling_core.state_models import (
    AllocationRole,
)
from token_io_decoupling_workflow.delegation_decisions import (
    ChildCandidate,
    ChildCandidateSelectionInput,
    ChildRoleSelectionInput,
    DelegationDecisionSelector,
    ExecutorSelectionInput,
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


def _choice_response(name: str, choice: str, *, model: str = "gpt-6-luna") -> object:
    return SimpleNamespace(
        answers=[SimpleNamespace(type="choice", name=name, choice=choice)],
        model=model,
        usage=SimpleNamespace(total_tokens=22),
    )


class _FakeDecisions:
    def __init__(self, response: object | None = None, error: Exception | None = None) -> None:
        self.response = response
        self.error = error
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        assert self.response is not None
        return self.response


class _FakeClient:
    def __init__(self, response: object | None = None, error: Exception | None = None) -> None:
        self.decisions = _FakeDecisions(response, error)
        self.closed = False

    def close(self) -> None:
        self.closed = True


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


def _candidate_call(client: _FakeClient) -> dict[str, Any]:
    assert len(client.decisions.calls) == 1
    return client.decisions.calls[0]


def test_child_candidate_with_idle_primary_calls_decisions_with_priority_pool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "canary-secret-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://canary.example.invalid/v1")
    client = _FakeClient(_choice_response("child_candidate", "primary-ref"))
    payload = _child_payload(
        _candidate("primary-ref", AllocationRole.PRIMARY_OUTPUT),
        _candidate("context-ref", AllocationRole.CONTEXT_BOOTSTRAP_REFRESH),
        _candidate("busy-ref", AllocationRole.CHANGE_VERIFICATION, availability="busy"),
        _candidate(
            "foreign-ref",
            AllocationRole.DOCUMENTATION_COMMENTS_GIT,
            same_session=False,
        ),
    )

    result = _selector(lambda *_: client).select_child_candidate(payload)

    assert (result.status, result.reason, result.suggested_value) == (
        "available",
        "decision_suggestion",
        "primary-ref",
    )
    call = _candidate_call(client)
    assert call["model"] == "gpt-6-luna"
    request = json.loads(call["input"])
    assert request["offered_choices"] == ["primary-ref", "insufficient_evidence"]
    assert [item["candidate_ref"] for item in request["caller_facts"]["candidates"]] == [
        "primary-ref"
    ]
    choices = call["questions"][0]["choices"]
    assert [item["value"] for item in choices] == ["primary-ref", "insufficient_evidence"]
    assert "Permission scope:" in choices[0]["description"]
    assert "current_skill_owner_sources" in request
    assert "outbound_data_permitted" not in request["caller_facts"]
    assert (
        result.input_hash
        == hashlib.sha256(
            json.dumps(request, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
    )
    assert client.closed


def test_child_candidate_without_idle_primary_uses_context_choices(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.invalid/v1")
    client = _FakeClient(_choice_response("child_candidate", "context-b"))
    payload = _child_payload(
        _candidate(
            "context-a", AllocationRole.CONTEXT_BOOTSTRAP_REFRESH, context="Only schema facts."
        ),
        _candidate(
            "context-b",
            AllocationRole.DOCUMENTATION_COMMENTS_GIT,
            context="Exact task-specific docs context.",
        ),
        _candidate("busy-primary", AllocationRole.PRIMARY_OUTPUT, availability="busy"),
    )

    result = _selector(lambda *_: client).select_child_candidate(payload)

    assert result.suggested_value == "context-b"
    request = json.loads(_candidate_call(client)["input"])
    assert request["offered_choices"] == [
        "context-a",
        "context-b",
        "insufficient_evidence",
    ]
    assert [item["candidate_ref"] for item in request["caller_facts"]["candidates"]] == [
        "context-a",
        "context-b",
    ]


def test_multiple_busy_candidates_wait_without_decisions() -> None:
    client = _FakeClient(_choice_response("child_candidate", "unused"))
    result = _selector(lambda *_: client).select_child_candidate(
        _child_payload(
            _candidate("busy-primary", AllocationRole.PRIMARY_OUTPUT, availability="busy"),
            _candidate(
                "busy-context", AllocationRole.CONTEXT_BOOTSTRAP_REFRESH, availability="busy"
            ),
        )
    )

    assert (result.status, result.reason, result.next_action) == (
        "blocked",
        "all_eligible_candidates_are_busy",
        "wait_until_a_suitable_current_session_child_is_idle",
    )
    assert client.decisions.calls == []


def test_failed_candidate_advice_falls_back_only_to_primary_and_respects_wait(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.invalid/v1")
    client = _FakeClient(error=TimeoutError("sensitive transport details"))
    result = _selector(lambda *_: client).select_child_candidate(
        _child_payload(
            _candidate("context-idle", AllocationRole.CONTEXT_BOOTSTRAP_REFRESH),
            _candidate("verification-idle", AllocationRole.CHANGE_VERIFICATION),
            _candidate("primary-busy", AllocationRole.PRIMARY_OUTPUT, availability="busy"),
        )
    )

    assert (result.status, result.reason, result.fallback_value, result.next_action) == (
        "fallback",
        "api_failure",
        "primary-busy",
        "wait_until_primary_is_idle",
    )
    assert "sensitive transport details" not in result.model_dump_json()
    assert client.closed


def test_changed_owner_policy_during_failed_request_blocks_primary_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class ChangingRules:
        def __init__(self) -> None:
            self.loader = RuleLoader(repository_root=_REPOSITORY_ROOT)
            self.calls: dict[str, int] = {}

        def load_delegation_policy(self, owner: str) -> tuple[str, str]:
            text, _ = self.loader.load_delegation_policy(owner)
            count = self.calls.get(owner, 0)
            self.calls[owner] = count + 1
            if count:
                text += "\nPolicy changed during the request."
            return text, hashlib.sha256(text.encode()).hexdigest()

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.invalid/v1")
    client = _FakeClient(error=TimeoutError("network failed"))
    result = _selector(lambda *_: client, rules=ChangingRules()).select_child_candidate(
        _child_payload(
            _candidate("primary-a", AllocationRole.PRIMARY_OUTPUT),
            _candidate("primary-b", AllocationRole.CONTEXT_BOOTSTRAP_REFRESH),
        )
    )

    assert (result.status, result.reason, result.fallback_value) == (
        "stale",
        "source_policy_changed_during_request",
        None,
    )


def test_executor_api_failure_never_defaults_to_root(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.invalid/v1")
    client = _FakeClient(error=TimeoutError("transport failed"))
    payload = ExecutorSelectionInput.model_validate(
        _base(
            mode=CodingMode.MULTI_AGENT,
            current_session_child_count=1,
            available_slots=1,
        )
    )

    result = _selector(lambda *_: client).select_executor(payload)

    assert (result.status, result.reason, result.suggested_value) == (
        "blocked",
        "api_failure",
        None,
    )


def test_explicit_executor_and_single_agent_skip_decisions() -> None:
    client = _FakeClient(_choice_response("executor", "root"))
    explicit = ExecutorSelectionInput.model_validate(
        _base(
            mode=CodingMode.MULTI_AGENT,
            explicit_user_executor="sub_agent",
            current_session_child_count=1,
            available_slots=0,
        )
    )
    single = ExecutorSelectionInput.model_validate(
        _base(
            mode=CodingMode.SINGLE_AGENT,
            current_session_child_count=0,
            available_slots=0,
        )
    )
    conflicting_single_sub = ExecutorSelectionInput.model_validate(
        _base(
            mode=CodingMode.SINGLE_AGENT,
            explicit_user_executor="sub_agent",
            current_session_child_count=0,
            available_slots=0,
        )
    )
    explicit_single_root = ExecutorSelectionInput.model_validate(
        _base(
            mode=CodingMode.SINGLE_AGENT,
            explicit_user_executor="root",
            current_session_child_count=0,
            available_slots=0,
        )
    )

    explicit_result = _selector(lambda *_: client).select_executor(explicit)
    single_result = _selector(lambda *_: client).select_executor(single)
    conflict_result = _selector(lambda *_: client).select_executor(conflicting_single_sub)
    root_result = _selector(lambda *_: client).select_executor(explicit_single_root)

    assert (explicit_result.status, explicit_result.suggested_value) == ("skipped", "sub_agent")
    assert (single_result.status, single_result.suggested_value) == ("skipped", "root")
    assert (
        conflict_result.status,
        conflict_result.reason,
        conflict_result.suggested_value,
    ) == (
        "blocked",
        "single_agent_mode_conflicts_with_explicit_child_executor",
        None,
    )
    assert (root_result.status, root_result.suggested_value) == ("skipped", "root")
    assert client.decisions.calls == []


def test_role_selection_uses_current_owner_and_user_instruction_skips_api() -> None:
    client = _FakeClient(
        _choice_response("child_role", AllocationRole.CONTEXT_BOOTSTRAP_REFRESH.value)
    )
    payload = ChildRoleSelectionInput.model_validate(
        _base(
            mode=CodingMode.MULTI_AGENT,
            created_roles=[],
            reserved_roles=[],
            available_slots=7,
            user_explicit_create_instruction=True,
            user_explicit_role=AllocationRole.CONTEXT_BOOTSTRAP_REFRESH,
        )
    )

    result = _selector(lambda *_: client).select_child_role(payload)

    assert (result.status, result.reason, result.suggested_value) == (
        "skipped",
        "explicit_user_creation_instruction",
        AllocationRole.CONTEXT_BOOTSTRAP_REFRESH.value,
    )
    assert client.decisions.calls == []


def test_role_selection_calls_decisions_with_owner_instructions_and_offered_roles(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.invalid/v1")
    selected_role = AllocationRole.CONTEXT_BOOTSTRAP_REFRESH
    client = _FakeClient(_choice_response("child_role", selected_role.value))

    result = _selector(lambda *_: client).select_child_role(_role_payload())

    assert (result.status, result.suggested_value, result.next_action) == (
        "available",
        selected_role.value,
        "root_review_then_reserve",
    )
    call = client.decisions.calls[0]
    assert call["model"] == "gpt-6-luna"
    request = json.loads(call["input"])
    assert [source["owner"] for source in request["current_skill_owner_sources"]] == [
        "child-role-selection",
        "session-role-ownership",
    ]
    offered_choices = call["questions"][0]["choices"]
    assert selected_role.value in {choice["value"] for choice in offered_choices}
    assert all(choice["description"].strip() for choice in offered_choices)


def test_role_selection_api_failure_falls_back_to_available_primary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.invalid/v1")
    client = _FakeClient(error=TimeoutError("sensitive transport detail"))

    result = _selector(lambda *_: client).select_child_role(_role_payload())

    assert (result.status, result.reason, result.fallback_value) == (
        "fallback",
        "api_failure",
        AllocationRole.PRIMARY_OUTPUT.value,
    )
    assert result.next_action == "root_review_then_use_primary_only_if_creation_is_established"
    assert "sensitive transport detail" not in result.model_dump_json()


def test_role_selection_excludes_occupied_roles_from_request_and_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.invalid/v1")
    occupied = _role_payload(
        created_roles=[AllocationRole.PRIMARY_OUTPUT],
        reserved_roles=[AllocationRole.CONTEXT_BOOTSTRAP_REFRESH],
    )
    selected_client = _FakeClient(
        _choice_response("child_role", AllocationRole.CHANGE_VERIFICATION.value)
    )

    selected = _selector(lambda *_: selected_client).select_child_role(occupied)
    offered_choices = selected_client.decisions.calls[0]["questions"][0]["choices"]

    assert selected.suggested_value == AllocationRole.CHANGE_VERIFICATION.value
    assert AllocationRole.PRIMARY_OUTPUT.value not in {
        choice["value"] for choice in offered_choices
    }
    assert AllocationRole.CONTEXT_BOOTSTRAP_REFRESH.value not in {
        choice["value"] for choice in offered_choices
    }

    failed_client = _FakeClient(error=TimeoutError("transport failed"))
    failed = _selector(lambda *_: failed_client).select_child_role(occupied)

    assert (failed.status, failed.reason, failed.fallback_value) == (
        "blocked",
        "api_failure",
        None,
    )


def test_output_token_yes_routes_or_holds_and_never_authorizes_root(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.invalid/v1")
    client = _FakeClient(_choice_response("output_tokens", "yes"))
    payload = OutputTokenRoutingInput.model_validate(
        _base(
            mode=CodingMode.MULTI_AGENT,
            requested_output_shape="Detailed release notes",
            expected_output_volume="Several long sections",
            idle_suitable_child_count=0,
            busy_suitable_child_count=1,
        )
    )

    result = _selector(lambda *_: client).assess_output_tokens(payload)

    assert (result.suggested_value, result.next_action) == (
        "yes",
        "wait_or_hold_until_a_suitable_child_is_idle",
    )


def test_missing_credentials_blocks_before_client_factory(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.invalid/v1")
    calls: list[bool] = []
    payload = ExecutorSelectionInput.model_validate(
        _base(
            mode=CodingMode.MULTI_AGENT,
            current_session_child_count=1,
            available_slots=1,
        )
    )

    result = _selector(lambda *_: calls.append(True)).select_executor(payload)

    assert (result.status, result.reason) == ("blocked", "missing_credentials")
    assert calls == []


@pytest.mark.parametrize(
    ("variable", "value"),
    [
        ("OPENAI_API_KEY", None),
        ("OPENAI_API_KEY", ""),
        ("OPENAI_API_KEY", "   "),
        ("OPENAI_BASE_URL", None),
        ("OPENAI_BASE_URL", ""),
        ("OPENAI_BASE_URL", "   "),
    ],
)
def test_each_missing_or_blank_decisions_credential_blocks_before_client(
    monkeypatch: pytest.MonkeyPatch,
    variable: str,
    value: str | None,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.invalid/v1")
    if value is None:
        monkeypatch.delenv(variable, raising=False)
    else:
        monkeypatch.setenv(variable, value)
    calls: list[bool] = []

    result = _selector(lambda *_: calls.append(True)).select_child_role(_role_payload())

    assert (result.status, result.reason) == ("blocked", "missing_credentials")
    assert calls == []


def test_real_openai_sdk_uses_decisions_wire_without_responses_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "canary-secret-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://canary.example.invalid/v1")
    requests: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        return httpx2.Response(
            200,
            json={
                "answers": [
                    {
                        "type": "choice",
                        "name": "executor",
                        "choice": "sub_agent",
                        "confidence": 0.8,
                        "probabilities": [{"value": "sub_agent", "probability": 0.8}],
                    }
                ],
                "model": "gpt-6-luna",
                "usage": {
                    "input_tokens": 20,
                    "output_tokens": 2,
                    "total_tokens": 22,
                },
            },
        )

    transport_client = httpx2.Client(transport=httpx2.MockTransport(handler))
    sdk_client = OpenAI(
        api_key="canary-secret-key",
        base_url="https://canary.example.invalid/v1",
        timeout=20.0,
        max_retries=0,
        http_client=transport_client,
    )
    payload = ExecutorSelectionInput.model_validate(
        _base(
            mode=CodingMode.MULTI_AGENT,
            current_session_child_count=1,
            available_slots=1,
        )
    )

    result = _selector(lambda *_: sdk_client).select_executor(payload)

    assert (result.status, result.suggested_value, result.total_tokens) == (
        "available",
        "sub_agent",
        22,
    )
    assert len(requests) == 1
    request = requests[0]
    assert request.method == "POST"
    assert request.url.path == "/v1/decisions"
    body = json.loads(request.content)
    assert body["model"] == "gpt-6-luna"
    assert body["questions"][0]["name"] == "executor"
    assert body["questions"][0]["instructions"].strip()
    assert [item["value"] for item in body["questions"][0]["choices"]] == [
        "root",
        "sub_agent",
        "insufficient_evidence",
    ]
    assert "canary-secret-key" not in request.content.decode()
    assert "canary.example.invalid" not in request.content.decode()
    assert transport_client.is_closed

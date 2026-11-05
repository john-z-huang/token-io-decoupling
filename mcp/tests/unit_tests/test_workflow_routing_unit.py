from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import ValidationError
from token_io_decoupling_core.rules import RuleLoader
from token_io_decoupling_workflow.decisions import (
    DecisionsRuntimeConfig,
)
from token_io_decoupling_workflow.workflow_routing import (
    MAX_CAPABILITY_FACTS,
    MAX_HARD_CONSTRAINTS,
    MAX_SOURCE_FACTS,
    DecouplingWorkflowRequest,
    WorkflowRouter,
    canonical_json,
    source_facts_hash,
)

_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def _source_facts() -> list[dict[str, str]]:
    return [{"fact_id": "scope", "source_ref": "caller:1", "statement": "Fix the parser."}]


def _request(**overrides: object) -> DecouplingWorkflowRequest:
    facts = _source_facts()
    data: dict[str, object] = {
        "task_id": "route-test",
        "task_summary": "Fix a parser edge case.",
        "stage": "execution",
        "language": "en",
        "mode_locked": True,
        "mode_count": {"mode": "Single-Agent Coding", "child_count": 0},
        "capabilities": [],
        "hard_constraints": [],
        "source_facts": facts,
        "source_facts_hash": source_facts_hash_from_dicts(facts),
        "outbound_data_permitted": False,
    }
    data.update(overrides)
    return DecouplingWorkflowRequest.model_validate_json(json.dumps(data, ensure_ascii=False))


def source_facts_hash_from_dicts(facts: list[dict[str, str]]) -> str:
    encoded = json.dumps(facts, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _router(client_factory: Any = None) -> WorkflowRouter:
    return WorkflowRouter(
        RuleLoader(repository_root=_REPOSITORY_ROOT),
        DecisionsRuntimeConfig(enabled=True, outbound_data_permitted=True),
        client_factory=client_factory,
    )


@pytest.mark.parametrize(
    ("mode", "child_count", "stage", "module_id", "route_id", "language", "route_path"),
    [
        (
            "Single-Agent Coding",
            0,
            "entry_readiness",
            "SM01",
            "coding-single-agent",
            "en",
            "coding-single-agent.md",
        ),
        (
            "Single-Agent Coding",
            0,
            "delivery_acceptance",
            "SM07",
            "coding-single-agent",
            "zh_cn",
            "coding-single-agent_zh_cn.md",
        ),
        (
            "Multi-Agent Coding",
            2,
            "execution",
            "MM04",
            "coding-multi-agent",
            "en",
            "coding-multi-agent.md",
        ),
        (
            "Multi-Agent Coding",
            1,
            "verification_repair",
            "MM05",
            "coding-multi-agent",
            "zh_cn",
            "coding-multi-agent_zh_cn.md",
        ),
    ],
)
def test_explicit_stage_maps_locked_mode_locally_without_api_or_credentials(
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
    child_count: int,
    stage: str,
    module_id: str,
    route_id: str,
    language: str,
    route_path: str,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    calls: list[tuple[str, str]] = []
    router = _router(lambda key, url: calls.append((key, url)))
    request = _request(
        mode_count={"mode": mode, "child_count": child_count}, stage=stage, language=language
    )

    result = router.decide(request)

    assert result.status == "available"
    assert result.advisory_only is True
    assert result.module_id == module_id
    assert result.selected_stage == stage
    assert result.route_reference is not None
    assert result.route_reference.route_id == route_id
    assert result.route_reference.route_path.endswith(route_path)
    assert result.route_reference.mode_count == request.mode_count
    assert result.rule_hash and result.index_sha256
    assert result.rule_evidence
    assert not result.model
    assert calls == []


def test_mode_must_be_locked_and_missing_capabilities_remain_unknown() -> None:
    result = _router().decide(_request(mode_locked=False))
    assert (result.status, result.reason) == ("blocked", "mode_not_locked")
    assert result.route_reference is None
    assert result.module_id is None
    assert all(item.status == "unknown" for item in result.capability_evidence)

    available = _router().decide(_request(stage="documentation"))
    evidence = {item.capability_id: item.status for item in available.capability_evidence}
    assert evidence["child_creation"] == "unknown"
    assert evidence["dispatch"] == "unknown"


def test_multi_agent_execution_advises_conditions_without_granting_authority() -> None:
    result = _router().decide(
        _request(mode_count={"mode": "Multi-Agent Coding", "child_count": 1}, stage="execution")
    )
    assert result.module_id == "MM04"
    ids = {item.check_id for item in result.conditional_checks}
    assert ids == {
        "multi_agent_child_role_and_authority_gates",
        "multi_agent_task_authorization_and_memo_conditions",
        "multi_agent_slice_before_child_creation",
    }
    assert result.capability_evidence[-2].status == "unknown"
    assert result.capability_evidence[-1].status == "unknown"


def test_hashes_use_ordered_canonical_unicode_json_and_exclude_fact_digest() -> None:
    facts = _source_facts()
    expected = hashlib.sha256(
        b'[{"fact_id":"scope","source_ref":"caller:1","statement":"Fix the parser."}]'
    ).hexdigest()
    assert canonical_json({"雪": [1, 2], "a": 1}) == '{"a":1,"雪":[1,2]}'
    assert source_facts_hash(_request().source_facts) == expected

    request = _request()
    mutated = request.model_copy(update={"source_facts_hash": "0" * 64})
    from token_io_decoupling_workflow.workflow_routing import _input_hash

    assert _input_hash(request) == _input_hash(mutated)
    reversed_facts = [
        dict(facts[0]),
        {"fact_id": "second", "source_ref": "caller:2", "statement": "Add tests."},
    ]
    ordered = _request(
        source_facts=reversed_facts, source_facts_hash=source_facts_hash_from_dicts(reversed_facts)
    )
    reversed_list = list(reversed(reversed_facts))
    reordered = _request(
        source_facts=reversed_list, source_facts_hash=source_facts_hash_from_dicts(reversed_list)
    )
    assert ordered.source_facts_hash != reordered.source_facts_hash


def test_hash_conflict_enum_duplicates_and_invalid_mode_count_are_rejected() -> None:
    facts = _source_facts()
    with pytest.raises(ValidationError, match="source_facts_hash"):
        _request(source_facts_hash="0" * 64)
    with pytest.raises(ValidationError):
        _request(stage="not-a-stage")
    duplicate = [facts[0], facts[0]]
    with pytest.raises(ValidationError, match="source fact IDs must be unique"):
        _request(source_facts=duplicate, source_facts_hash=source_facts_hash_from_dicts(duplicate))
    with pytest.raises(ValidationError):
        _request(mode_count={"mode": "Single-Agent Coding", "child_count": 1})
    with pytest.raises(ValidationError):
        _request(mode_count={"mode": "Multi-Agent Coding", "child_count": 0})


def test_bounded_collections_and_strict_extra_fields_are_rejected() -> None:
    too_many_facts = [
        {"fact_id": f"f{i}", "source_ref": "caller", "statement": "fact"}
        for i in range(MAX_SOURCE_FACTS + 1)
    ]
    with pytest.raises(ValidationError):
        _request(
            source_facts=too_many_facts,
            source_facts_hash=source_facts_hash_from_dicts(too_many_facts),
        )
    too_many_constraints = [
        {"constraint_id": f"c{i}", "source_ref": "caller", "statement": "constraint"}
        for i in range(MAX_HARD_CONSTRAINTS + 1)
    ]
    with pytest.raises(ValidationError):
        _request(hard_constraints=too_many_constraints)
    too_many_capabilities = [
        {"capability_id": capability, "status": "unknown", "source_ref": "caller"}
        for capability in [
            "rule_context",
            "implementation",
            "verification",
            "documentation",
            "git",
            "child_creation",
            "dispatch",
            "rule_context",
        ]
    ]
    assert len(too_many_capabilities) > MAX_CAPABILITY_FACTS
    with pytest.raises(ValidationError):
        _request(capabilities=too_many_capabilities)
    with pytest.raises(ValidationError):
        _request(unrecognized="extra")


def test_source_hash_is_caller_consistency_only_and_invalid_auto_conditions_make_no_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.invalid/v1")
    calls: list[tuple[str, str]] = []
    router = _router(lambda key, url: calls.append((key, url)))
    no_facts = _request(
        source_facts=[], source_facts_hash=source_facts_hash_from_dicts([]), stage="auto"
    )
    missing = router.decide(no_facts)
    assert (missing.status, missing.reason) == ("insufficient_evidence", "source_facts_missing")
    denied = router.decide(_request(stage="auto", outbound_data_permitted=False))
    assert (denied.status, denied.reason) == ("blocked", "outbound_data_not_permitted")
    assert calls == []


def test_rule_loader_failure_or_incomplete_bundle_never_returns_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    router = _router()
    monkeypatch.setattr(
        router._rules,
        "load_context_bundle",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError("secret")),
    )
    result = router.decide(_request(stage="execution"))
    assert (result.status, result.reason) == ("blocked", "rules_unavailable")
    assert "secret" not in json.dumps(result.model_dump(mode="json"))

    incomplete = _router()
    original = incomplete._rules.load_context_bundle
    monkeypatch.setattr(
        incomplete._rules,
        "load_context_bundle",
        lambda *args, **kwargs: original(*args, **kwargs).model_copy(
            update={"complete": False, "status": "incomplete_content"}
        ),
    )
    result = incomplete.decide(_request(stage="execution"))
    assert result.status != "available"
    assert result.reason == "rule_context_incomplete"


def test_result_is_stateless_and_input_hash_covers_request_but_not_fact_digest() -> None:
    router = _router()
    request = _request()
    before = request.model_dump(mode="json")
    first = router.decide(request)
    second = router.decide(request)
    assert request.model_dump(mode="json") == before
    assert first == second
    assert first.input_hash == second.input_hash
    assert first.source_facts_hash == request.source_facts_hash


class _FakeDecisions:
    def __init__(self, response: object | None = None, error: Exception | None = None) -> None:
        self.response = response
        self.error = error
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        assert self.response is not None
        return self.response


class _FakeApiClient:
    def __init__(self, response: object | None = None, error: Exception | None = None) -> None:
        self.decisions = _FakeDecisions(response=response, error=error)
        self.closed = False

    def close(self) -> None:
        self.closed = True


def _api_response(
    *,
    choice: str = "execution",
    model: str = "gpt-6-luna",
    status: str = "completed",
    answer_type: str = "choice",
    name: str = "workflow_stage",
    error: object | None = None,
    incomplete_details: object | None = None,
) -> object:
    return SimpleNamespace(
        answers=[SimpleNamespace(type=answer_type, name=name, choice=choice)],
        model=model,
        status=status,
        error=error,
        incomplete_details=incomplete_details,
        usage=SimpleNamespace(total_tokens=17),
    )


@pytest.mark.parametrize(
    ("response", "error", "expected_status", "expected_reason"),
    [
        (
            _api_response(choice="insufficient_evidence"),
            None,
            "insufficient_evidence",
            "insufficient_evidence",
        ),
        (_api_response(status="refused", answer_type="refusal"), None, "blocked", "refusal"),
        (_api_response(choice="unlisted_stage"), None, "blocked", "invalid_response"),
        (_api_response(model="another-model"), None, "blocked", "unsupported_model"),
        (
            _api_response(status="incomplete", incomplete_details={"reason": "budget"}),
            None,
            "blocked",
            "incomplete_response",
        ),
        (None, TimeoutError("synthetic timeout"), "blocked", "timeout"),
    ],
)
def test_auto_api_failure_and_insufficient_answers_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
    response: object | None,
    error: Exception | None,
    expected_status: str,
    expected_reason: str,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.invalid/v1")
    client = _FakeApiClient(response, error)
    factory_calls: list[tuple[str, str]] = []
    router = _router(lambda key, url: factory_calls.append((key, url)) or client)

    result = router.decide(_request(stage="auto", outbound_data_permitted=True))

    assert (result.status, result.reason) == (expected_status, expected_reason)
    assert result.module_id is None
    assert result.advisory_only is True
    assert factory_calls == [("test-key", "https://example.invalid/v1")]
    assert len(client.decisions.calls) == 1
    assert client.closed


@pytest.mark.parametrize(("key", "url"), [(None, "https://example.invalid/v1"), ("test-key", None)])
def test_auto_requires_both_environment_values_before_client_creation(
    monkeypatch: pytest.MonkeyPatch, key: str | None, url: str | None
) -> None:
    if key is None:
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    else:
        monkeypatch.setenv("OPENAI_API_KEY", key)
    if url is None:
        monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    else:
        monkeypatch.setenv("OPENAI_BASE_URL", url)
    calls: list[object] = []
    router = _router(lambda *_: calls.append("client"))

    result = router.decide(_request(stage="auto", outbound_data_permitted=True))

    assert (result.status, result.reason) == ("blocked", "missing_credentials")
    assert calls == []


def test_auto_configuration_and_permission_denials_do_not_create_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.invalid/v1")
    calls: list[object] = []
    loader = RuleLoader(repository_root=_REPOSITORY_ROOT)
    disabled = WorkflowRouter(
        loader,
        DecisionsRuntimeConfig(enabled=False, outbound_data_permitted=False),
        client_factory=lambda *_: calls.append("client"),
    )
    config_failure = disabled.decide(_request(stage="auto", outbound_data_permitted=True))
    permission_failure = _router(lambda *_: calls.append("client")).decide(
        _request(stage="auto", outbound_data_permitted=False)
    )

    assert (config_failure.status, config_failure.reason) == ("blocked", "decisions_disabled")
    assert (permission_failure.status, permission_failure.reason) == (
        "blocked",
        "outbound_data_not_permitted",
    )
    assert calls == []


def test_auto_detects_rule_context_change_during_api_call(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.invalid/v1")
    client = _FakeApiClient(_api_response(choice="execution"))
    router = _router(lambda *_: client)
    original = router._rules.load_context_bundle
    call_count: dict[str, int] = {}

    def changed_on_refresh(
        node_id: str,
        *,
        language: Any = None,
        fragment_ids: Any = None,
        max_chars: int = 12_000,
    ) -> Any:
        bundle = original(
            node_id,
            language=language,
            fragment_ids=fragment_ids,
            max_chars=max_chars,
        )
        call_count[node_id] = call_count.get(node_id, 0) + 1
        if call_count[node_id] > 1:
            return bundle.model_copy(update={"context_hash": "f" * 64})
        return bundle

    monkeypatch.setattr(router._rules, "load_context_bundle", changed_on_refresh)
    result = router.decide(_request(stage="auto", outbound_data_permitted=True))

    assert (result.status, result.reason) == ("stale", "stale_rule_context")
    assert result.module_id is None
    assert len(client.decisions.calls) == 1
    assert client.closed

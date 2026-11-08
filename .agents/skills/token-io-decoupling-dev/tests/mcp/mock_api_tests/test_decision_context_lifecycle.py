"""描述生成的校验优先级、政策新鲜度和客户端清理回归；不请求真实 API。"""

from types import SimpleNamespace

import pytest

from token_io_decoupling_workflow.decision_context import (
    GENERATION_MODEL,
    DecisionContextGenerator,
    DecisionContextInput,
    DecisionContextStructuredOutput,
    _input_hash,
)
from token_io_decoupling_workflow.rules import CompiledDelegationPolicy, RuleLoader, RuleLoadError

POLICY = CompiledDelegationPolicy("original policy", "a" * 64, {}, {})
CHANGED_POLICY = CompiledDelegationPolicy("changed policy", "b" * 64, {}, {})


class _SequenceRules(RuleLoader):
    def __init__(
        self, policies: list[CompiledDelegationPolicy | Exception], events: list[str]
    ) -> None:
        self.policies = iter(policies)
        self.events = events

    def load_delegation_policy(self, owner: str) -> CompiledDelegationPolicy:
        self.events.append("policy")
        policy = next(self.policies)
        if isinstance(policy, Exception):
            raise policy
        return policy


class _Client:
    def __init__(
        self, response: object, events: list[str], close_error: Exception | None = None
    ) -> None:
        self.responses = self
        self.response = response
        self.events = events
        self.close_error = close_error

    def parse(self, **kwargs: object) -> object:
        self.events.append("request")
        if isinstance(self.response, Exception):
            raise self.response
        return self.response

    def close(self) -> None:
        self.events.append("close")
        if self.close_error is not None:
            raise self.close_error


class _UnreadableUsage:
    @property
    def total_tokens(self) -> int:
        raise AssertionError("usage must not be read for a stale policy")


@pytest.fixture
def payload(monkeypatch: pytest.MonkeyPatch) -> DecisionContextInput:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.invalid/v1")
    return DecisionContextInput(
        raw_content="User requirement: preserve behavior.",
        decision_goal="Describe the current released task.",
        output_kind="decision_context",
        outbound_data_permitted=True,
    )


def _response(**overrides: object) -> SimpleNamespace:
    fields: dict[str, object] = {
        "status": "completed",
        "model": GENERATION_MODEL,
        "error": None,
        "incomplete_details": None,
        "output": [],
        "output_parsed": DecisionContextStructuredOutput(
            description="A valid description.", missing_information=[]
        ),
        "usage": SimpleNamespace(total_tokens=29),
    }
    fields.update(overrides)
    return SimpleNamespace(**fields)


@pytest.mark.parametrize(
    "current_policy",
    [CHANGED_POLICY, RuleLoadError("unavailable"), OSError("unavailable"), ValueError("invalid")],
    ids=["changed", "load-error", "os-error", "invalid-policy"],
)
def test_stale_policy_is_checked_after_close_and_before_usage(
    payload: DecisionContextInput, current_policy: CompiledDelegationPolicy | Exception
) -> None:
    events: list[str] = []
    rules = _SequenceRules([POLICY, current_policy], events)
    client = _Client(_response(usage=_UnreadableUsage()), events)
    generator = DecisionContextGenerator(rules=rules, client_factory=lambda *_: client)

    result = generator.generate(payload)

    assert (result.status, result.reason) == ("blocked", "stale_policy")
    assert result.source_policy_hash == POLICY.content_sha256
    assert result.input_hash == _input_hash(payload)
    assert result.description is None
    assert events == ["policy", "request", "close", "policy"]


@pytest.mark.parametrize(
    ("overrides", "reason", "missing"),
    [
        ({"status": "incomplete", "error": "failure", "model": "wrong"}, "incomplete", []),
        (
            {
                "error": "failure",
                "output": [SimpleNamespace(content=[SimpleNamespace(type="refusal")])],
            },
            "invalid_response",
            [],
        ),
        (
            {
                "model": "wrong",
                "output": [SimpleNamespace(content=[SimpleNamespace(type="refusal")])],
            },
            "invalid_response",
            [],
        ),
        (
            {
                "output": [SimpleNamespace(content=[SimpleNamespace(type="refusal")])],
                "output_parsed": None,
            },
            "refusal",
            [],
        ),
        (
            {
                "output_parsed": DecisionContextStructuredOutput(
                    description=None, missing_information=["specific gap"]
                )
            },
            "insufficient_evidence",
            ["specific gap"],
        ),
    ],
    ids=[
        "status-first",
        "error-before-refusal",
        "model-before-refusal",
        "refusal-before-body",
        "missing-evidence",
    ],
)
def test_response_failure_precedes_policy_refresh(
    payload: DecisionContextInput, overrides: dict[str, object], reason: str, missing: list[str]
) -> None:
    events: list[str] = []
    rules = _SequenceRules([POLICY], events)
    client = _Client(_response(**overrides), events)
    generator = DecisionContextGenerator(rules=rules, client_factory=lambda *_: client)

    result = generator.generate(payload)

    assert (result.status, result.reason) == ("blocked", reason)
    assert result.source_policy_hash == POLICY.content_sha256
    assert result.missing_information == missing
    assert events == ["policy", "request", "close"]


@pytest.mark.parametrize(
    ("tokens", "expected"),
    [(0, 0), (42, 42), (True, None), (-1, None), ("42", None), (None, None)],
    ids=["zero", "positive", "boolean", "negative", "string", "missing"],
)
def test_usage_requires_a_nonnegative_exact_integer(
    payload: DecisionContextInput, tokens: object, expected: int | None
) -> None:
    events: list[str] = []
    rules = _SequenceRules([POLICY, POLICY], events)
    client = _Client(_response(usage=SimpleNamespace(total_tokens=tokens)), events)
    generator = DecisionContextGenerator(rules=rules, client_factory=lambda *_: client)

    result = generator.generate(payload)

    assert (result.status, result.reason) == ("available", "description_generated")
    assert result.total_tokens == expected
    assert result.description == "A valid description."
    assert events == ["policy", "request", "close", "policy"]


@pytest.mark.parametrize("request_fails", [False, True], ids=["success", "timeout"])
def test_close_failure_preserves_the_original_result(
    payload: DecisionContextInput, request_fails: bool
) -> None:
    events: list[str] = []
    rules = _SequenceRules([POLICY, POLICY], events)
    response = TimeoutError("provider details") if request_fails else _response()
    client = _Client(response, events, close_error=RuntimeError("cleanup details"))
    generator = DecisionContextGenerator(rules=rules, client_factory=lambda *_: client)

    result = generator.generate(payload)

    assert result.reason == ("timeout" if request_fails else "description_generated")
    assert result.source_policy_hash == POLICY.content_sha256
    assert "details" not in result.model_dump_json()
    assert events == (
        ["policy", "request", "close"]
        if request_fails
        else ["policy", "request", "close", "policy"]
    )


def test_initial_policy_failure_stops_before_client_creation(payload: DecisionContextInput) -> None:
    events: list[str] = []
    rules = _SequenceRules([RuleLoadError("unavailable")], events)
    client = _Client(_response(), events)

    def make_client(_key: str, _url: str) -> object:
        events.append("create")
        return client

    generator = DecisionContextGenerator(rules=rules, client_factory=make_client)

    result = generator.generate(payload)

    assert (result.status, result.reason) == ("blocked", "policy_unavailable")
    assert result.source_policy_hash is None
    assert events == ["policy"]


def test_client_creation_failure_keeps_policy_provenance(payload: DecisionContextInput) -> None:
    events: list[str] = []
    rules = _SequenceRules([POLICY], events)

    def make_client(_key: str, _url: str) -> object:
        events.append("create")
        raise RuntimeError("private factory details")

    generator = DecisionContextGenerator(rules=rules, client_factory=make_client)

    result = generator.generate(payload)

    assert (result.status, result.reason) == ("blocked", "provider_error")
    assert result.source_policy_hash == POLICY.content_sha256
    assert "private factory details" not in result.model_dump_json()
    assert events == ["policy", "create"]

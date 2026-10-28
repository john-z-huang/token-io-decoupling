from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import httpx2
import pytest
from openai import OpenAI
from token_io_decoupling_core.rules import RuleLoader
from token_io_decoupling_workflow.decision_context import (
    GENERATION_MODEL,
    DecisionContextGenerator,
    DecisionContextInput,
    DecisionContextStructuredOutput,
    _input_hash,
)

_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def _rules() -> RuleLoader:
    return RuleLoader(repository_root=_REPOSITORY_ROOT)


def _generator(
    *, client_factory: Callable[[str, str], object] | None = None
) -> DecisionContextGenerator:
    return DecisionContextGenerator(rules=_rules(), client_factory=client_factory)


def _payload(**overrides: object) -> DecisionContextInput:
    request: dict[str, object] = {
        "raw_content": (
            "User requirement: preserve existing behavior.\n"
            "Current diff: adds strict decision question.\n"
            "LSP observation: caller-composed symbol fact."
        ),
        "decision_goal": "Ask which lowest sufficient effort fits the released task.",
        "output_kind": "decision_question",
        "outbound_data_permitted": True,
    }
    request.update(overrides)
    return DecisionContextInput.model_validate(request)


def _response(
    parsed: object,
    *,
    model: str = GENERATION_MODEL,
    status: str = "completed",
    output: object | None = None,
    error: object | None = None,
    incomplete_details: object | None = None,
) -> object:
    return SimpleNamespace(
        output_parsed=parsed,
        model=model,
        status=status,
        output=output,
        error=error,
        incomplete_details=incomplete_details,
        usage=SimpleNamespace(total_tokens=29),
    )


class _FakeResponses:
    def __init__(self, response: object | None = None, error: Exception | None = None) -> None:
        self.response = response
        self.error = error
        self.calls: list[dict[str, object]] = []

    def parse(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        assert self.response is not None
        return self.response


class _FakeClient:
    def __init__(self, response: object | None = None, error: Exception | None = None) -> None:
        self.responses = _FakeResponses(response, error)
        self.closed = False

    def close(self) -> None:
        self.closed = True


def test_success_preserves_all_caller_material_and_uses_fixed_responses_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.invalid/v1")
    payload = _payload(
        raw_content="需求：保留换行。\nDiff: add field.\nLSP: exact symbol observation. ☃",
        decision_goal="Ask the minimum-effort question within the released task constraints.",
    )
    parsed = DecisionContextStructuredOutput(
        description=(
            "Which lowest sufficient effort fits this released task?\nKeep its constraints."
        ),
        missing_information=[],
    )
    client = _FakeClient(_response(parsed))
    client_args: list[tuple[str, str]] = []
    result = _generator(
        client_factory=lambda key, url: client_args.append((key, url)) or client
    ).generate(payload)

    assert (result.status, result.reason) == ("available", "description_generated")
    assert result.description == parsed.description
    assert result.output_kind == "decision_question"
    assert result.model == GENERATION_MODEL
    assert result.total_tokens == 29
    assert result.input_hash == _input_hash(payload)
    assert client_args == [("test-key", "https://example.invalid/v1")]
    call = client.responses.calls[0]
    assert call["model"] == GENERATION_MODEL
    instructions = call["instructions"]
    assert isinstance(instructions, str)
    assert instructions == _rules().load_delegation_policy("decision-context-generation")[0]
    assert payload.raw_content not in instructions
    assert payload.decision_goal not in instructions
    assert call["text_format"] is DecisionContextStructuredOutput
    assert call["store"] is False
    assert call["reasoning"] == {"effort": "medium"}
    assert call["max_output_tokens"] == 4096
    assert call["truncation"] == "disabled"
    assert call["tools"] == []
    encoded_input = call["input"]
    assert isinstance(encoded_input, str)
    request = json.loads(encoded_input)["request"]
    assert request["raw_content"] == payload.raw_content
    assert request["decision_goal"] == payload.decision_goal
    assert request["output_kind"] == payload.output_kind
    assert "outbound_data_permitted" not in request
    assert client.closed


def test_real_openai_sdk_uses_responses_wire_contract_with_mock_transport(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "canary-secret-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://canary.example.invalid/v1")
    expected_description = "Which effort should be used for the released task?"
    source = "User requirement: preserve constraints.\nGit diff: add decision helper."
    requests: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        return httpx2.Response(
            200,
            json={
                "id": "resp_decision_context",
                "object": "response",
                "created_at": 1_730_000_000,
                "status": "completed",
                "error": None,
                "incomplete_details": None,
                "model": GENERATION_MODEL,
                "output": [
                    {
                        "id": "msg_decision_context",
                        "type": "message",
                        "status": "completed",
                        "role": "assistant",
                        "content": [
                            {
                                "type": "output_text",
                                "text": json.dumps(
                                    {
                                        "description": expected_description,
                                        "missing_information": [],
                                    }
                                ),
                                "annotations": [],
                            }
                        ],
                    }
                ],
                "usage": {
                    "input_tokens": 30,
                    "output_tokens": 12,
                    "total_tokens": 42,
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
    result = _generator(client_factory=lambda *_: sdk_client).generate(_payload(raw_content=source))

    assert (result.status, result.reason) == ("available", "description_generated")
    assert result.description == expected_description
    assert result.total_tokens == 42
    assert len(requests) == 1
    request = requests[0]
    assert request.method == "POST"
    assert request.url.path == "/v1/responses"
    body = json.loads(request.content)
    assert body["model"] == GENERATION_MODEL
    assert body["instructions"] == _rules().load_delegation_policy("decision-context-generation")[0]
    assert body["reasoning"] == {"effort": "medium"}
    assert body["store"] is False
    assert body["tools"] == []
    assert body["input"] == json.dumps(
        {
            "request": {
                "raw_content": source,
                "decision_goal": "Ask which lowest sufficient effort fits the released task.",
                "output_kind": "decision_question",
            }
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    assert body["text"]["format"]["type"] == "json_schema"
    assert body["text"]["format"]["strict"] is True
    assert "missing_information" in body["text"]["format"]["schema"]["properties"]
    assert "canary-secret-key" not in request.content.decode()
    assert "canary.example.invalid" not in request.content.decode()
    assert transport_client.is_closed


def test_context_kind_accepts_six_thousand_characters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.invalid/v1")
    description = "c" * 6000
    client = _FakeClient(
        _response(DecisionContextStructuredOutput(description=description, missing_information=[]))
    )
    result = _generator(client_factory=lambda *_: client).generate(
        _payload(output_kind="decision_context")
    )
    assert result.status == "available"
    assert result.description == description


def test_generated_question_is_compatible_with_child_effort_question_field(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.invalid/v1")
    description = "Which effort is sufficient for the released task?\nUse the stated constraints."
    client = _FakeClient(
        _response(DecisionContextStructuredOutput(description=description, missing_information=[]))
    )
    result = _generator(client_factory=lambda *_: client).generate(
        _payload(output_kind="decision_question")
    )
    assert result.description is not None
    child_data = {
        "slice_id": "released-1",
        "role": "Primary Output",
        "objective": "Implement the approved task.",
        "decision_question": result.description,
        "task_complexity": "ordinary_semantic",
        "uncertainty": "none",
        "scope": "One bounded slice.",
        "dependencies": "none",
        "risk": "Known and bounded.",
        "verification_demands": "Focused tests.",
        "previous_failure_evidence": "none",
        "slice_fingerprint": "a" * 64,
        "runtime": "codex",
        "child_model": "gpt-6-luna",
        "supported_efforts": ["low", "medium"],
        "outbound_data_permitted": True,
    }
    from token_io_decoupling_workflow.child_effort import ChildEffortInput

    assert ChildEffortInput.model_validate(child_data).decision_question == description


def test_false_permission_blocks_before_environment_or_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    environment_read = Mock(side_effect=AssertionError("unexpected environment read"))
    monkeypatch.setattr(
        "token_io_decoupling_workflow.decision_context.os.environ.get", environment_read
    )
    factory_calls: list[bool] = []
    result = _generator(client_factory=lambda *_: factory_calls.append(True)).generate(
        _payload(outbound_data_permitted=False)
    )
    assert (result.status, result.reason) == ("blocked", "outbound_data_not_permitted")
    environment_read.assert_not_called()
    assert factory_calls == []


@pytest.mark.parametrize(
    "key,url",
    [
        (None, "https://example.invalid/v1"),
        ("  ", "https://example.invalid/v1"),
        ("test-key", None),
        ("test-key", "\t "),
    ],
)
def test_each_missing_or_blank_credential_blocks_before_client(
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
    calls: list[bool] = []
    result = _generator(client_factory=lambda *_: calls.append(True)).generate(_payload())
    assert (result.status, result.reason) == ("blocked", "missing_credentials")
    assert calls == []


@pytest.mark.parametrize(
    "response,reason",
    [
        (_response(None, status="incomplete"), "incomplete"),
        (
            _response(None, incomplete_details=SimpleNamespace(reason="max_output_tokens")),
            "invalid_response",
        ),
        (_response(None, error=SimpleNamespace(code="provider_error")), "invalid_response"),
        (_response(None, model="different-model"), "invalid_response"),
        (
            _response(None, output=[SimpleNamespace(content=[SimpleNamespace(type="refusal")])]),
            "refusal",
        ),
        (_response({}), "invalid_response"),
        (
            _response(DecisionContextStructuredOutput(description="   ", missing_information=[])),
            "invalid_response",
        ),
        (
            _response(DecisionContextStructuredOutput(description=None, missing_information=[])),
            "invalid_response",
        ),
        (
            _response(
                DecisionContextStructuredOutput(description="context", missing_information=["gap"])
            ),
            "invalid_response",
        ),
        (
            _response(
                DecisionContextStructuredOutput(description=None, missing_information=["   "])
            ),
            "invalid_response",
        ),
        (
            _response(
                DecisionContextStructuredOutput(
                    description=None, missing_information=["specific missing fact"]
                )
            ),
            "insufficient_evidence",
        ),
    ],
)
def test_nonusable_or_inconsistent_model_outputs_fail_closed(
    monkeypatch: pytest.MonkeyPatch, response: object, reason: str
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.invalid/v1")
    client = _FakeClient(response)
    result = _generator(client_factory=lambda *_: client).generate(_payload())
    assert (result.status, result.reason) == ("blocked", reason)
    assert result.description is None
    if reason == "insufficient_evidence":
        assert result.missing_information == ["specific missing fact"]
    else:
        assert result.missing_information == []
    assert client.closed


def test_output_limits_are_enforced_per_kind(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.invalid/v1")
    too_long_question = _FakeClient(
        _response(DecisionContextStructuredOutput(description="q" * 1201, missing_information=[]))
    )
    question_result = _generator(client_factory=lambda *_: too_long_question).generate(
        _payload(output_kind="decision_question")
    )
    assert (question_result.status, question_result.reason) == ("blocked", "invalid_response")

    too_long_context = _FakeClient(
        _response(
            DecisionContextStructuredOutput.model_construct(
                description="c" * 6001, missing_information=[]
            ),
        )
    )
    context_result = _generator(client_factory=lambda *_: too_long_context).generate(
        _payload(output_kind="decision_context")
    )
    assert (context_result.status, context_result.reason) == ("blocked", "invalid_response")


@pytest.mark.parametrize(
    "error,reason",
    [(RuntimeError("private provider details"), "provider_error"), (TimeoutError(), "timeout")],
)
def test_provider_failures_are_redacted_and_close_client(
    monkeypatch: pytest.MonkeyPatch, error: Exception, reason: str
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.invalid/v1")
    client = _FakeClient(error=error)
    result = _generator(client_factory=lambda *_: client).generate(_payload())
    assert (result.status, result.reason) == ("blocked", reason)
    private_error = error.args[0] if error.args else type(error).__name__
    assert private_error not in result.model_dump_json()
    assert result.description is None
    assert client.closed


def test_parsing_error_is_reported_as_invalid_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.invalid/v1")

    class ResponseParsingError(RuntimeError):
        pass

    client = _FakeClient(error=ResponseParsingError("bad response body"))
    result = _generator(client_factory=lambda *_: client).generate(_payload())
    assert (result.status, result.reason) == ("blocked", "invalid_response")
    assert "bad response body" not in result.model_dump_json()

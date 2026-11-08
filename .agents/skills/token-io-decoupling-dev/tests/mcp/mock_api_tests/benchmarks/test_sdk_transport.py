"""真实 SDK 配合模拟 transport 的调用记录与次数上限。"""

from __future__ import annotations

import json
from typing import Any, cast

import benchmark_metrics as metrics
import httpx2
import pytest
from benchmark_support.fixtures import (
    _configured,
    _decisions_payload,
    _FakeClient,
    _ParsedOutput,
    _responses_payload,
)
from openai import APIConnectionError


def test_real_sdk_uses_default_httpx2_transport_and_records_safe_usage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configured(monkeypatch)
    requests: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        if request.url.path == "/v1/responses":
            return httpx2.Response(200, json=_responses_payload())
        if request.url.path == "/v1/decisions":
            return httpx2.Response(200, json=_decisions_payload())
        return httpx2.Response(404, json={"error": {"message": "unexpected route"}})

    recorder = metrics.Recorder(
        max_http_attempts=4,
        transport=httpx2.MockTransport(handler),
    )
    client = recorder.make_client(
        case_id="case-real-sdk",
        arm="baseline",
        component="reference_caller",
        timeout=20.0,
    )
    http_client = cast(Any, client._client)._client
    assert isinstance(http_client, httpx2.Client)
    assert http_client.timeout.read == 20.0
    assert http_client.follow_redirects is True
    parsed = client.responses.parse(
        model=metrics.FIXED_MODEL,
        input="frozen benchmark facts",
        reasoning={"effort": "medium"},
        text_format=_ParsedOutput,
    )
    decision = client.decisions.create(
        model=metrics.FIXED_MODEL,
        input="frozen route facts",
        questions=[
            {
                "type": "choice",
                "name": "stage",
                "instructions": "Choose a supported current stage.",
                "choices": [{"value": "work_definition", "description": "Work remains."}],
            }
        ],
    )

    assert parsed.output_parsed.answer == "ready"
    assert decision.answers[0].choice == "work_definition"
    assert recorder.http_attempts == 2
    assert [request.url.path for request in requests] == ["/v1/responses", "/v1/decisions"]
    assert all(
        request.headers["authorization"] == "Bearer canary-private-key" for request in requests
    )
    assert json.loads(requests[0].content)["reasoning"] == {"effort": "medium"}
    assert [call["http_attempts"] for call in recorder.calls] == [1, 1]
    assert [call["timeout_seconds"] for call in recorder.calls] == [20.0, 20.0]
    assert recorder.calls[0]["requested_model"] == metrics.FIXED_MODEL
    assert recorder.calls[0]["requested_effort"] == "medium"
    assert [call["usage"] for call in recorder.calls] == [
        {"input_tokens": 11, "output_tokens": 3, "total_tokens": 14},
        {"input_tokens": 80, "output_tokens": 7, "total_tokens": 87},
    ]
    safe_records = repr(recorder.calls)
    assert "canary-private-key" not in safe_records
    assert "benchmark.invalid" not in safe_records
    assert "frozen benchmark facts" not in safe_records

    client.close()
    assert cast(Any, client._client)._client.is_closed is True


def test_real_sdk_transport_failures_count_attempts_and_stop_at_cap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configured(monkeypatch)
    requests: list[str] = []

    def fail_transport(request: httpx2.Request) -> httpx2.Response:
        requests.append(request.url.path)
        raise httpx2.ConnectError("private transport diagnostic", request=request)

    recorder = metrics.Recorder(
        max_http_attempts=1,
        transport=httpx2.MockTransport(fail_transport),
    )
    client = recorder.make_client(
        case_id="case-failure",
        arm="assisted",
        component="materialization_renderer",
        timeout=30.0,
    )

    with pytest.raises(APIConnectionError):
        client.responses.parse(
            model=metrics.FIXED_MODEL,
            input="synthetic input",
            text_format=_ParsedOutput,
        )
    with pytest.raises(metrics.BenchmarkHTTPAttemptLimitExceeded):
        client.responses.parse(
            model=metrics.FIXED_MODEL,
            input="synthetic input",
            text_format=_ParsedOutput,
        )

    assert recorder.http_attempts == 1
    assert requests == ["/v1/responses"]
    assert [call["http_attempts"] for call in recorder.calls] == [1, 0]
    assert all(call["status"] == "error" for call in recorder.calls)
    assert "private transport diagnostic" not in repr(recorder.calls)
    client.close()


def test_proxy_forwards_responses_and_decisions_and_records_safe_usage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configured(monkeypatch)
    captured: dict[str, object] = {}
    fake_client: _FakeClient | None = None

    def build_client(**kwargs: object) -> _FakeClient:
        nonlocal fake_client
        captured.update(kwargs)
        hook = kwargs["request_hook"]
        assert callable(hook)
        fake_client = _FakeClient(hook)
        return fake_client

    monkeypatch.setattr(metrics, "_build_openai_client", build_client)
    recorder = metrics.Recorder()
    client = recorder.make_client(
        case_id="case-a",
        arm="baseline",
        component="reference_caller",
        timeout=20.0,
    )
    response_args = ("positional-response-argument",)
    response_kwargs = {
        "model": metrics.FIXED_MODEL,
        "input": "frozen benchmark facts",
        "reasoning": {"effort": "medium"},
    }
    decision_kwargs = {
        "model": metrics.FIXED_MODEL,
        "input": "frozen route facts",
        "questions": [{"type": "choice", "name": "stage"}],
    }

    assert client.responses.parse(*response_args, **response_kwargs)["model"] == metrics.FIXED_MODEL
    assert client.decisions.create(**decision_kwargs)["model"] == metrics.FIXED_MODEL

    assert captured["api_key"] == "canary-private-key"
    assert captured["base_url"] == "https://benchmark.invalid/v1"
    assert captured["timeout"] == 20.0
    assert captured["max_retries"] == 0
    assert fake_client is not None
    assert fake_client.responses.calls == [(response_args, response_kwargs)]
    assert fake_client.decisions.calls == [((), decision_kwargs)]
    assert recorder.http_attempts == 2
    assert [call["operation"] for call in recorder.calls] == ["parse", "create"]
    assert [call["api"] for call in recorder.calls] == ["responses", "decisions"]
    assert [call["timeout_seconds"] for call in recorder.calls] == [20.0, 20.0]
    assert recorder.calls[0]["requested_model"] == metrics.FIXED_MODEL
    assert recorder.calls[0]["requested_effort"] == "medium"
    assert recorder.calls[0]["usage"] == {
        "input_tokens": 11,
        "output_tokens": 3,
        "total_tokens": 14,
    }
    assert recorder.calls[1]["usage"] == {
        "input_tokens": 80,
        "output_tokens": 7,
        "total_tokens": 87,
    }
    safe_records = repr(recorder.calls)
    assert "canary-private-key" not in safe_records
    assert "benchmark.invalid" not in safe_records
    assert "frozen benchmark facts" not in safe_records

    client.close()
    assert fake_client.closed

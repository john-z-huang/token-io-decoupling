"""模拟客户端的代理转发、凭据前置校验及安全调用记录。"""

from __future__ import annotations

import benchmark_metrics as metrics
import pytest
from benchmark_support.fixtures import (
    _configured,
    _FakeClient,
)


@pytest.mark.parametrize(
    ("component", "timeout"),
    [("caller", 30.0), ("route", 20.0), ("renderer", 30.0)],
)
def test_successful_call_records_keep_timeout_for_each_component(
    monkeypatch: pytest.MonkeyPatch,
    component: str,
    timeout: float,
) -> None:
    _configured(monkeypatch)

    def build_client(**kwargs: object) -> _FakeClient:
        hook = kwargs["request_hook"]
        assert callable(hook)
        return _FakeClient(hook)

    monkeypatch.setattr(metrics, "_build_openai_client", build_client)
    recorder = metrics.Recorder()
    client = recorder.make_client(
        case_id="case-timeout",
        arm="baseline",
        component=component,
        timeout=timeout,
    )

    client.responses.parse(model=metrics.FIXED_MODEL, input="synthetic input")

    assert len(recorder.calls) == 1
    assert recorder.calls[0]["status"] == "success"
    assert recorder.calls[0]["timeout_seconds"] == timeout
    client.close()


def test_positional_payload_is_not_recorded_as_requested_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configured(monkeypatch)

    def build_client(**kwargs: object) -> _FakeClient:
        hook = kwargs["request_hook"]
        assert callable(hook)
        return _FakeClient(hook)

    monkeypatch.setattr(metrics, "_build_openai_client", build_client)
    recorder = metrics.Recorder()
    client = recorder.make_client(
        case_id="case-positional-input",
        arm="baseline",
        component="caller",
        timeout=30.0,
    )
    client.responses.parse("private positional payload")

    assert recorder.calls[0]["requested_model"] is None
    assert "private positional payload" not in repr(recorder.calls)
    client.close()


@pytest.mark.parametrize(
    ("component", "timeout"),
    [("caller", 30.0), ("route", 20.0), ("renderer", 30.0)],
)
def test_transport_failures_count_attempts_and_enforce_global_cap(
    monkeypatch: pytest.MonkeyPatch,
    component: str,
    timeout: float,
) -> None:
    _configured(monkeypatch)
    captured: dict[str, object] = {}

    class _FailingResponses:
        def parse(self, **_kwargs: object) -> None:
            hook = captured["request_hook"]
            assert callable(hook)
            hook(object())
            raise RuntimeError("private transport diagnostic")

    class _FailingClient:
        responses = _FailingResponses()

        def close(self) -> None:
            pass

    def build_client(**kwargs: object) -> _FailingClient:
        captured.update(kwargs)
        return _FailingClient()

    monkeypatch.setattr(metrics, "_build_openai_client", build_client)
    recorder = metrics.Recorder(max_http_attempts=1)
    client = recorder.make_client(
        case_id="case-b",
        arm="assisted",
        component=component,
        timeout=timeout,
    )

    with pytest.raises(RuntimeError, match="private transport diagnostic"):
        client.responses.parse(model=metrics.FIXED_MODEL, input="synthetic input")
    with pytest.raises(metrics.BenchmarkHTTPAttemptLimitExceeded):
        client.responses.parse(model=metrics.FIXED_MODEL, input="synthetic input")

    assert recorder.http_attempts == 1
    assert len(recorder.calls) == 2
    assert [call["http_attempts"] for call in recorder.calls] == [1, 0]
    assert [call["timeout_seconds"] for call in recorder.calls] == [timeout, timeout]
    assert all(call["status"] == "error" for call in recorder.calls)
    assert all(
        call["usage"] == {"input_tokens": None, "output_tokens": None, "total_tokens": None}
        for call in recorder.calls
    )
    assert "private transport diagnostic" not in repr(recorder.calls)


def test_make_client_requires_explicit_nonblank_process_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_BASE_URL", "https://benchmark.invalid/v1")

    def fail_builder(**_kwargs: object) -> object:
        raise AssertionError("OpenAI client was created without an API key")

    monkeypatch.setattr(metrics, "_build_openai_client", fail_builder)
    recorder = metrics.Recorder()

    with pytest.raises(metrics.BenchmarkCredentialError) as error:
        recorder.make_client(
            case_id="case-c",
            arm="baseline",
            component="reference_caller",
            timeout=20.0,
        )

    assert str(error.value) == "OPENAI_API_KEY_must_be_set_to_a_nonblank_value"
    assert recorder.http_attempts == 0
    assert recorder.calls == []

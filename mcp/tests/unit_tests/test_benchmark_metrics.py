from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import httpx2
import pytest
from openai import APIConnectionError
from pydantic import BaseModel

_SUPPORT = Path(__file__).resolve().parents[1] / "support"
sys.path.insert(0, str(_SUPPORT))

import benchmark_cases as cases  # noqa: E402  # ty: ignore[unresolved-import]
import benchmark_metrics as metrics  # noqa: E402  # ty: ignore[unresolved-import]
import optimization_benchmark as benchmark  # noqa: E402  # ty: ignore[unresolved-import]


class _ParsedOutput(BaseModel):
    answer: str


def _responses_payload() -> dict[str, object]:
    return {
        "id": "resp_metrics",
        "object": "response",
        "created_at": 1_730_000_000,
        "status": "completed",
        "error": None,
        "incomplete_details": None,
        "model": metrics.FIXED_MODEL,
        "output": [
            {
                "id": "msg_metrics",
                "type": "message",
                "status": "completed",
                "role": "assistant",
                "content": [
                    {
                        "type": "output_text",
                        "text": '{"answer":"ready"}',
                        "annotations": [],
                    }
                ],
            }
        ],
        "usage": {"input_tokens": 11, "output_tokens": 3, "total_tokens": 14},
    }


def _decisions_payload() -> dict[str, object]:
    return {
        "answers": [
            {
                "type": "choice",
                "name": "stage",
                "choice": "work_definition",
                "confidence": 1.0,
                "probabilities": [{"value": "work_definition", "probability": 1.0}],
            }
        ],
        "model": metrics.FIXED_MODEL,
        "usage": {"input_tokens": 80, "output_tokens": 7, "total_tokens": 87},
    }


class _FakeResponses:
    def __init__(self, hook, response: dict[str, object]) -> None:
        self._hook = hook
        self._response = response
        self.calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def parse(self, *args: object, **kwargs: object) -> dict[str, object]:
        self.calls.append((args, kwargs))
        self._hook(object())
        return self._response


class _FakeDecisions:
    def __init__(self, hook, response: dict[str, object]) -> None:
        self._hook = hook
        self._response = response
        self.calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def create(self, *args: object, **kwargs: object) -> dict[str, object]:
        self.calls.append((args, kwargs))
        self._hook(object())
        return self._response


class _FakeClient:
    def __init__(self, hook) -> None:
        self.responses = _FakeResponses(
            hook,
            {
                "model": metrics.FIXED_MODEL,
                "usage": {"input_tokens": 11, "output_tokens": 3, "total_tokens": 14},
            },
        )
        self.decisions = _FakeDecisions(
            hook,
            {
                "model": metrics.FIXED_MODEL,
                "usage": {"input_tokens": 80, "output_tokens": 7, "total_tokens": 87},
            },
        )
        self.closed = False

    def close(self) -> None:
        self.closed = True


def _configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "canary-private-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://benchmark.invalid/v1")


class _RunnerRecorder:
    def __init__(self, *, max_http_attempts: int) -> None:
        self.max_http_attempts = max_http_attempts
        self.http_attempts = 0
        self.calls: list[dict[str, object]] = []


def _runner_case_module(run_case) -> SimpleNamespace:
    cases_by_id = {case_id: {"service": case_id} for case_id in cases.CASE_IDS}

    return SimpleNamespace(
        CASE_IDS=cases.CASE_IDS,
        DATASET={**cases.DATASET, "protocol_version": 2},
        DATASET_PATH=cases.DATASET_PATH,
        _COMMON_SOURCES=cases._COMMON_SOURCES,
        _CASE_SOURCES=cases._CASE_SOURCES,
        _CASES=cases_by_id,
        _service_metadata=lambda service: ({"service": service}, []),
        run_case=run_case,
    )


def _runner_row(case_module: SimpleNamespace, case_id: str) -> dict[str, object]:
    metadata, _ = case_module._service_metadata(case_module._CASES[case_id]["service"])
    return {
        "semantic_success": True,
        "source_hashes": {"stable": True},
        "metadata_hash": benchmark._canonical_hash(metadata),
        "component_calls": [
            {
                "tool": "benchmark_tool",
                "arguments_utf8_bytes": 12,
                "result_utf8_bytes": 20,
                "seconds": 0.001,
            }
        ],
        "timings": {"service": 0.001},
    }


def _runner_api_call(component: str) -> dict[str, object]:
    return {
        "component": component,
        "operation": "parse" if component == "caller" else "create",
        "status": "success",
        "error_type": None,
        "requested_model": metrics.FIXED_MODEL,
        "requested_effort": "medium" if component == "caller" else None,
        "usage": {"input_tokens": 4, "output_tokens": 2, "total_tokens": 6},
        "duration_ms": 1.0,
        "http_attempts": 1,
    }


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


@pytest.mark.parametrize(
    ("calls", "expected_usage", "expected_known", "complete_calls", "total_calls"),
    [
        (
            [],
            {"input_tokens": None, "output_tokens": None, "total_tokens": None},
            {"input_tokens": None, "output_tokens": None, "total_tokens": None},
            0,
            0,
        ),
        (
            [
                {
                    "component": "caller",
                    "operation": "parse",
                    "duration_ms": 2.0,
                    "usage": {"input_tokens": 5, "output_tokens": 2, "total_tokens": 7},
                },
                {
                    "component": "inner",
                    "operation": "create",
                    "duration_ms": 3.0,
                    "usage": {"input_tokens": 8, "output_tokens": 1, "total_tokens": 9},
                },
            ],
            {"input_tokens": 13, "output_tokens": 3, "total_tokens": 16},
            {"input_tokens": 13, "output_tokens": 3, "total_tokens": 16},
            2,
            2,
        ),
        (
            [
                {
                    "component": "caller",
                    "operation": "parse",
                    "duration_ms": 2.0,
                    "usage": {"input_tokens": 5, "output_tokens": 2, "total_tokens": 7},
                },
                {
                    "component": "inner",
                    "operation": "create",
                    "duration_ms": 3.0,
                    "usage": {"input_tokens": 8, "output_tokens": None, "total_tokens": None},
                },
            ],
            {"input_tokens": None, "output_tokens": None, "total_tokens": None},
            {"input_tokens": 13, "output_tokens": 2, "total_tokens": 7},
            1,
            2,
        ),
    ],
)
def test_aggregate_calls_keeps_unknown_usage_null_and_reports_coverage(
    calls: list[dict[str, Any]],
    expected_usage: dict[str, int | None],
    expected_known: dict[str, int | None],
    complete_calls: int,
    total_calls: int,
) -> None:
    result = metrics.aggregate_calls(calls)

    assert result["api_calls"] == total_calls
    assert result["usage"] == expected_usage
    assert result["known_subtotal"] == expected_known
    coverage = result["usage_coverage"]
    assert isinstance(coverage, dict)
    assert coverage["complete_calls"] == complete_calls
    assert coverage["total_calls"] == total_calls
    if total_calls == 0:
        assert coverage["complete_fraction"] is None
    else:
        assert coverage["complete_fraction"] == complete_calls / total_calls


def test_usage_fields_accept_zero_but_reject_missing_or_invalid_values() -> None:
    calls = [
        {"usage": {"input_tokens": 0, "output_tokens": "3", "total_tokens": None}},
    ]

    result = metrics.aggregate_calls(calls)

    assert result["usage"] == {"input_tokens": None, "output_tokens": None, "total_tokens": None}
    assert result["known_subtotal"] == {
        "input_tokens": 0,
        "output_tokens": None,
        "total_tokens": None,
    }


def test_mock_runner_executes_fixed_case_arm_order_and_writes_complete_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configured(monkeypatch)
    order: list[tuple[str, str]] = []
    created_recorders: list[_RunnerRecorder] = []
    case_module: SimpleNamespace

    def run_case(
        case_id: str,
        arm: str,
        recorder: _RunnerRecorder,
        _repo_root: Path,
        _temporary_root: Path,
    ) -> dict[str, object]:
        order.append((case_id, arm))
        recorder.http_attempts += 1
        recorder.calls.append(_runner_api_call("caller"))
        if arm == "assisted":
            recorder.http_attempts += 1
            recorder.calls.append(_runner_api_call("inner"))
        return _runner_row(case_module, case_id)

    case_module = _runner_case_module(run_case)

    def recorder_factory(*, max_http_attempts: int) -> _RunnerRecorder:
        recorder = _RunnerRecorder(max_http_attempts=max_http_attempts)
        created_recorders.append(recorder)
        return recorder

    output = tmp_path / "benchmark.json"
    report = benchmark.run_benchmark(
        output,
        repo_root=Path(__file__).resolve().parents[3],
        case_module=case_module,
        recorder_factory=recorder_factory,
    )

    expected_order = [(case_id, arm) for case_id in cases.CASE_IDS for arm in benchmark.ARMS]
    assert order == expected_order
    assert len(created_recorders) == 1
    assert created_recorders[0].max_http_attempts == benchmark.MAX_HTTP_ATTEMPTS == 30
    assert report["status"] == "complete"
    assert report["protocol_version"] == 2
    assert report["case_ids"] == list(cases.CASE_IDS)
    assert len(report["rows"]) == 10
    assert all(row["execution_status"] == "executed" for row in report["rows"])
    assert report["http_attempts"] == 15
    assert sum(row["http_attempts"] for row in report["rows"]) == 15
    assert len(report["api_calls"]) == 15
    assert report["summary"]["caller"]["usage"]["input_tokens"] == 40
    assert report["summary"]["inner"]["usage"]["input_tokens"] == 20
    assert report["summary"]["caller"]["usage_coverage"]["complete_fraction"] == 1.0
    assert report["validation"]["measurement_valid"] is True
    assert report["validation"]["usage_complete"] is True
    fingerprints = report["fingerprints"]
    assert fingerprints["sources"]["stable"] is True
    assert fingerprints["dataset"]["stable"] is True
    assert fingerprints["metadata"]["stable"] is True
    assert report["started_at_utc"]
    assert report["finished_at_utc"]
    assert json.loads(output.read_text(encoding="utf-8")) == report


def test_timing_summary_reads_nested_runner_rows_and_keeps_layers_separate() -> None:
    case_module = _runner_case_module(lambda *_args: {})
    case_id = cases.CASE_IDS[0]
    baseline = _runner_row(case_module, case_id)
    baseline["timings"] = {"service": 0.002, "caller": 0.004, "elapsed": 0.006}
    assisted = _runner_row(case_module, case_id)
    assisted["timings"] = {"service": 0.003, "caller": 0.005, "elapsed": 0.008}
    rows = [
        {"case_id": case_id, "arm": "baseline", "raw_case_row": baseline},
        {"case_id": case_id, "arm": "assisted", "raw_case_row": assisted},
    ]

    summary = benchmark._timing_summary(rows)

    assert all("timings" not in row for row in rows)
    assert set(summary) == {"caller", "elapsed", "service"}
    assert summary["caller"]["samples"] == 2
    assert summary["caller"]["sum_seconds"] == 0.009
    assert summary["caller"]["seconds_by_row"] == {
        f"{case_id}:baseline": 0.004,
        f"{case_id}:assisted": 0.005,
    }
    assert summary["service"]["sum_seconds"] == 0.005
    assert summary["elapsed"]["sum_seconds"] == 0.014
    assert "end_to_end_speedup" not in summary


def test_mock_runner_preserves_rows_calls_and_attempts_at_the_global_cap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configured(monkeypatch)
    case_module: SimpleNamespace

    def run_case(
        case_id: str,
        _arm: str,
        recorder: _RunnerRecorder,
        _repo_root: Path,
        _temporary_root: Path,
    ) -> dict[str, object]:
        for _ in range(6):
            recorder.http_attempts += 1
            recorder.calls.append(_runner_api_call("caller"))
        return _runner_row(case_module, case_id)

    case_module = _runner_case_module(run_case)
    output = tmp_path / "capped.json"
    report = benchmark.run_benchmark(
        output,
        repo_root=Path(__file__).resolve().parents[3],
        case_module=case_module,
        recorder_factory=_RunnerRecorder,
    )

    rows = report["rows"]
    assert report["status"] == "partial"
    assert report["blocking_reason"] == "http_attempt_cap_reached"
    assert report["http_attempts"] == benchmark.MAX_HTTP_ATTEMPTS
    assert len(report["api_calls"]) == benchmark.MAX_HTTP_ATTEMPTS
    assert [row["execution_status"] for row in rows] == ["executed"] * 5 + ["unrun"] * 5
    assert [row["http_attempts"] for row in rows[:5]] == [6] * 5
    assert all(row["unrun_reason"] == "http_attempt_cap_reached" for row in rows[5:])
    assert sum(row["http_attempts"] for row in rows) == benchmark.MAX_HTTP_ATTEMPTS
    assert report["summary"]["caller"]["usage_coverage"]["complete_fraction"] == 1.0
    assert json.loads(output.read_text(encoding="utf-8")) == report


def test_complete_telemetry_does_not_make_semantic_failure_comparable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configured(monkeypatch)
    case_module: SimpleNamespace

    def run_case(
        case_id: str,
        arm: str,
        recorder: _RunnerRecorder,
        _repo_root: Path,
        _temporary_root: Path,
    ) -> dict[str, object]:
        recorder.http_attempts += 1
        recorder.calls.append(_runner_api_call("caller"))
        if arm == "assisted":
            recorder.http_attempts += 1
            recorder.calls.append(_runner_api_call("inner"))
        row = _runner_row(case_module, case_id)
        if case_id == cases.CASE_IDS[0] and arm == "baseline":
            row["semantic_success"] = False
        return row

    case_module = _runner_case_module(run_case)
    report = benchmark.run_benchmark(
        tmp_path / "semantic-failure.json",
        repo_root=Path(__file__).resolve().parents[3],
        case_module=case_module,
        recorder_factory=_RunnerRecorder,
    )

    assert report["status"] == "complete"
    assert report["protocol_version"] == 2
    assert report["validation"]["measurement_valid"] is True
    assert report["validation"]["usage_complete"] is True
    assert report["validation"]["semantic_valid"] is False
    assert report["validation"]["token_comparison_valid"] is False


def test_mock_runner_keeps_failure_type_without_persisting_or_printing_raw_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _configured(monkeypatch)
    case_module: SimpleNamespace

    def run_case(
        case_id: str,
        arm: str,
        recorder: _RunnerRecorder,
        _repo_root: Path,
        _temporary_root: Path,
    ) -> dict[str, object]:
        recorder.http_attempts += 1
        if case_id == cases.CASE_IDS[0] and arm == "baseline":
            failed_call = _runner_api_call("caller")
            failed_call["status"] = "error"
            failed_call["error_type"] = "RuntimeError"
            failed_call["usage"] = {
                "input_tokens": None,
                "output_tokens": None,
                "total_tokens": None,
            }
            recorder.calls.append(failed_call)
            raise RuntimeError("private raw provider error")
        recorder.calls.append(_runner_api_call("caller"))
        if arm == "assisted":
            recorder.http_attempts += 1
            recorder.calls.append(_runner_api_call("inner"))
        return _runner_row(case_module, case_id)

    case_module = _runner_case_module(run_case)
    output = tmp_path / "failed-row.json"
    report = benchmark.run_benchmark(
        output,
        repo_root=Path(__file__).resolve().parents[3],
        case_module=case_module,
        recorder_factory=_RunnerRecorder,
    )
    captured = capsys.readouterr()

    first_row = report["rows"][0]
    assert report["status"] == "partial"
    assert len(report["rows"]) == 10
    assert first_row["execution_status"] == "error"
    assert first_row["error_type"] == "RuntimeError"
    assert first_row["raw_case_row"] is None
    assert report["http_attempts"] == 15
    assert len(report["api_calls"]) == 15
    assert "private raw provider error" not in captured.out
    assert "private raw provider error" not in captured.err
    assert "private raw provider error" not in output.read_text(encoding="utf-8")
    assert report["summary"]["caller"]["usage"]["input_tokens"] is None
    assert report["summary"]["caller"]["usage_coverage"]["complete_fraction"] == 0.9


def test_live_cli_rejects_existing_output_before_loading_cases_or_creating_client(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output = tmp_path / "existing.json"
    output.write_text("preserve this report", encoding="utf-8")
    monkeypatch.setattr(benchmark, "_suppress_sdk_logs", lambda: None)

    def fail_load() -> Any:
        raise AssertionError("cases loaded before the output collision was rejected")

    def fail_recorder(**_kwargs: object) -> Any:
        raise AssertionError("a recorder was created before output validation")

    monkeypatch.setattr(
        benchmark,
        "_load_case_module",
        fail_load,
    )
    monkeypatch.setattr(
        benchmark,
        "Recorder",
        fail_recorder,
    )

    status = benchmark.main(["--live", "--output", str(output)])
    captured = capsys.readouterr()

    assert status == 2
    assert output.read_text(encoding="utf-8") == "preserve this report"
    assert "benchmark_output_rejected" in captured.err
    assert "preserve this report" not in captured.err

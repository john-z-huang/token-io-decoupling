"""基准遥测测试专用的响应数据、客户端及合成案例。"""

from __future__ import annotations

from types import SimpleNamespace

import benchmark_cases as cases
import benchmark_metrics as metrics
import optimization_benchmark as benchmark
import pytest
from pydantic import BaseModel


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
        PROTOCOL_STATUS="synthetic_test_fixture",
        DATASET={"protocol_version": "synthetic-instrumentation-v1"},
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

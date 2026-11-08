"""合成基准的执行顺序、全局上限和失败报告。"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import benchmark_cases as cases
import optimization_benchmark as benchmark
import pytest
from benchmark_support.fixtures import (
    _configured,
    _runner_api_call,
    _runner_case_module,
    _runner_row,
    _RunnerRecorder,
)


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
        repo_root=Path(__file__).resolve().parents[7],
        case_module=case_module,
        recorder_factory=recorder_factory,
    )

    expected_order = [(case_id, arm) for case_id in cases.CASE_IDS for arm in benchmark.ARMS]
    assert order == expected_order
    assert len(created_recorders) == 1
    assert created_recorders[0].max_http_attempts == benchmark.MAX_HTTP_ATTEMPTS == 30
    assert report["status"] == "synthetic_complete"
    assert report["protocol_version"] == "synthetic-instrumentation-v1"
    assert report["case_ids"] == list(cases.CASE_IDS)
    assert len(report["rows"]) == 10
    assert all(row["execution_status"] == "executed" for row in report["rows"])
    assert report["http_attempts"] == 15
    assert sum(row["http_attempts"] for row in report["rows"]) == 15
    assert len(report["api_calls"]) == 15
    assert report["summary"]["caller"]["usage"]["input_tokens"] == 40
    assert report["summary"]["inner"]["usage"]["input_tokens"] == 20
    assert report["summary"]["caller"]["usage_coverage"]["complete_fraction"] == 1.0
    assert report["validation"]["synthetic_telemetry_valid"] is True
    assert report["validation"]["measurement_valid"] is False
    assert report["validation"]["token_comparison_valid"] is False
    assert report["validation"]["usage_complete"] is True
    fingerprints = report["fingerprints"]
    assert fingerprints["sources"]["stable"] is True
    assert fingerprints["dataset"]["stable"] is True
    assert fingerprints["metadata"]["stable"] is True
    assert report["started_at_utc"]
    assert report["finished_at_utc"]
    assert json.loads(output.read_text(encoding="utf-8")) == report


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
        repo_root=Path(__file__).resolve().parents[7],
        case_module=case_module,
        recorder_factory=_RunnerRecorder,
    )

    rows = report["rows"]
    assert report["status"] == "synthetic_partial"
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
        repo_root=Path(__file__).resolve().parents[7],
        case_module=case_module,
        recorder_factory=_RunnerRecorder,
    )

    assert report["status"] == "synthetic_complete"
    assert report["protocol_version"] == "synthetic-instrumentation-v1"
    assert report["validation"]["synthetic_telemetry_valid"] is True
    assert report["validation"]["measurement_valid"] is False
    assert report["validation"]["token_comparison_valid"] is False
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
        repo_root=Path(__file__).resolve().parents[7],
        case_module=case_module,
        recorder_factory=_RunnerRecorder,
    )
    captured = capsys.readouterr()

    first_row = report["rows"][0]
    assert report["status"] == "synthetic_partial"
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

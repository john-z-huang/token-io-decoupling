"""合成基准在执行前阻塞，以及案例类型错误的安全报告。"""

import json
from pathlib import Path

import optimization_benchmark as benchmark
import pytest
from benchmark_support.fixtures import _configured, _runner_case_module, _RunnerRecorder

REPO_ROOT = Path(__file__).resolve().parents[7]


def _forbidden_recorder(**kwargs):
    raise AssertionError("recorder must not be created before preconditions pass")


@pytest.mark.parametrize(
    ("precondition", "status", "reason"),
    [
        pytest.param(
            "missing-credentials",
            "blocked",
            "required_process_environment_missing",
            id="credentials",
        ),
        pytest.param(
            "missing-source", "blocked", "source_or_metadata_snapshot_failed", id="source"
        ),
        pytest.param(
            "reordered-cases",
            "blocked",
            "dataset_does_not_match_fixed_case_order",
            id="dataset-order",
        ),
        pytest.param("duplicate-cases", "error", "benchmark_runner_error", id="duplicate-cases"),
    ],
)
def test_runner_checks_preconditions_before_creating_recorder(
    tmp_path, monkeypatch, precondition, status, reason
):
    _configured(monkeypatch)
    cases = _runner_case_module(lambda *_: pytest.fail("case executed before preconditions passed"))
    if precondition == "missing-credentials":
        monkeypatch.delenv("OPENAI_API_KEY")
    elif precondition == "missing-source":
        cases._COMMON_SOURCES = ["missing-benchmark-source.py"]
    elif precondition == "reordered-cases":
        cases.CASE_IDS = tuple(reversed(cases.CASE_IDS))
    elif precondition == "duplicate-cases":
        cases.CASE_IDS = (cases.CASE_IDS[0],) * 5

    output = tmp_path / "report.json"
    report = benchmark.run_benchmark(
        output, repo_root=REPO_ROOT, case_module=cases, recorder_factory=_forbidden_recorder
    )

    assert report["status"] == status
    assert report["blocking_reason"] == reason
    assert report["api_calls"] == []
    assert report["http_attempts"] == 0
    assert all(row["execution_status"] == "unrun" for row in report["rows"])
    assert json.loads(output.read_text()) == report


def test_non_mapping_case_result_records_failure_type_without_aborting_remaining_rows(
    tmp_path, monkeypatch
):
    _configured(monkeypatch)
    cases = _runner_case_module(lambda *_: None)

    report = benchmark.run_benchmark(
        tmp_path / "report.json",
        repo_root=REPO_ROOT,
        case_module=cases,
        recorder_factory=_RunnerRecorder,
    )

    assert report["status"] == "synthetic_partial"
    assert len(report["rows"]) == 10
    assert all(row["execution_status"] == "error" for row in report["rows"])
    assert {row["error_type"] for row in report["rows"]} == {"TypeError"}
    assert report["validation"]["synthetic_telemetry_valid"] is False
    assert report["validation"]["measurement_valid"] is False
    assert report["validation"]["token_comparison_valid"] is False


class _InitiallyCappedRecorder(_RunnerRecorder):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.http_attempts = self.max_http_attempts


def test_initial_attempt_cap_preserves_legacy_case_group_dispositions(tmp_path, monkeypatch):
    _configured(monkeypatch)
    cases = _runner_case_module(lambda *_: pytest.fail("case executed after the cap"))

    report = benchmark.run_benchmark(
        tmp_path / "capped.json",
        repo_root=REPO_ROOT,
        case_module=cases,
        recorder_factory=_InitiallyCappedRecorder,
    )

    assert report["status"] == "synthetic_partial"
    assert report["blocking_reason"] == "http_attempt_cap_reached"
    assert report["http_attempts"] == 30
    assert report["api_calls"] == []
    assert [row["unrun_reason"] for row in report["rows"]] == (
        ["http_attempt_cap_reached"] * 2 + ["benchmark_not_started"] * 8
    )

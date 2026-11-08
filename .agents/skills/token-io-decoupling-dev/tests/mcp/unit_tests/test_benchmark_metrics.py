"""调用用量聚合、缺失值与分层时延的确定性校验。"""

from __future__ import annotations

from typing import Any

import benchmark_cases as cases
import benchmark_metrics as metrics
import optimization_benchmark as benchmark
import pytest


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


def test_timing_summary_reads_nested_runner_rows_and_keeps_layers_separate() -> None:
    case_id = cases.CASE_IDS[0]
    baseline = {"timings": {"service": 0.002, "caller": 0.004, "elapsed": 0.006}}
    assisted = {"timings": {"service": 0.003, "caller": 0.005, "elapsed": 0.008}}
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

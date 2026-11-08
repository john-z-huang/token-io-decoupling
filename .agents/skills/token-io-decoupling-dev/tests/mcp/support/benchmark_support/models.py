"""合成基准的报告契约与固定执行参数。"""

from __future__ import annotations

from typing import Any, TypedDict


class TimingLayer(TypedDict):
    samples: int
    sum_seconds: float
    seconds_by_row: dict[str, float]


class BenchmarkReport(TypedDict, total=False):
    schema_version: int
    status: str
    started_at_utc: str
    finished_at_utc: str | None
    fixed_model: str
    caller_reasoning_effort: str
    max_http_attempts: int
    protocol_version: object
    protocol_status: str
    comparison_scope: str
    case_ids: list[str]
    arms: list[str]
    rows: list[dict[str, Any]]
    api_calls: list[dict[str, Any]]
    http_attempts: int
    summary: dict[str, Any]
    fingerprints: dict[str, Any]
    validation: dict[str, Any]
    blocking_reason: str | None
    runner_error_type: str
    missing_environment_keys: list[str]


ARMS = ("baseline", "assisted")


EXPECTED_CASE_COUNT = 5


MAX_HTTP_ATTEMPTS = 30


CALLER_REASONING_EFFORT = "medium"

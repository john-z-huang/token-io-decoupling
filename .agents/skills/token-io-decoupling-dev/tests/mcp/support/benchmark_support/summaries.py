"""按调用组件、工具和时延层汇总合成遥测。"""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence

from benchmark_metrics import aggregate_calls

from .models import TimingLayer


def _row_id(case_id: str, arm: str) -> str:
    return f"{case_id}:{arm}"


def _call_summary(calls: Sequence[Mapping[str, object]]) -> dict[str, object]:
    caller_calls = [call for call in calls if call.get("component") == "caller"]
    inner_calls = [call for call in calls if call.get("component") == "inner"]
    other_calls = [call for call in calls if call.get("component") not in {"caller", "inner"}]
    return {
        "api_calls": len(calls),
        "caller": aggregate_calls(caller_calls),
        "inner": aggregate_calls(inner_calls),
        "other_components": aggregate_calls(other_calls),
    }


def _component_summary(rows: Sequence[Mapping[str, object]]) -> dict[str, object]:
    components: list[Mapping[str, object]] = []
    for row in rows:
        case_result = row.get("raw_case_row")
        if not isinstance(case_result, Mapping):
            continue
        values = case_result.get("component_calls")
        if isinstance(values, list):
            components.extend(item for item in values if isinstance(item, Mapping))
    by_tool = Counter(
        tool
        for item in components
        if (tool := item.get("tool")) is not None and isinstance(tool, str)
    )
    argument_bytes = sum(
        value
        for item in components
        if (value := item.get("arguments_utf8_bytes")) is not None
        and type(value) is int
        and value >= 0
    )
    result_bytes = sum(
        value
        for item in components
        if (value := item.get("result_utf8_bytes")) is not None
        and type(value) is int
        and value >= 0
    )
    return {
        "invocations": len(components),
        "invocations_by_tool": dict(sorted(by_tool.items())),
        "argument_utf8_bytes": argument_bytes,
        "result_utf8_bytes": result_bytes,
        "duration_seconds": round(
            sum(
                value
                for item in components
                if (value := item.get("seconds")) is not None
                and isinstance(value, (int, float))
                and not isinstance(value, bool)
                and value >= 0
            ),
            6,
        ),
    }


def _timing_summary(rows: Sequence[Mapping[str, object]]) -> dict[str, TimingLayer]:
    samples: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for row in rows:
        case_result = row.get("raw_case_row")
        timings = case_result.get("timings") if isinstance(case_result, Mapping) else None
        if not isinstance(timings, Mapping):
            continue
        for name, value in timings.items():
            if (
                isinstance(name, str)
                and isinstance(value, (int, float))
                and not isinstance(value, bool)
                and math.isfinite(value)
                and value >= 0
            ):
                samples[name].append((_row_id(str(row["case_id"]), str(row["arm"])), float(value)))
    return {
        name: {
            "samples": len(values),
            "sum_seconds": round(sum(value for _, value in values), 6),
            "seconds_by_row": {row: round(value, 6) for row, value in values},
        }
        for name, values in sorted(samples.items())
    }


def _report_summary(
    rows: Sequence[Mapping[str, object]], calls: Sequence[Mapping[str, object]]
) -> dict[str, object]:
    return {
        **_call_summary(calls),
        "component_invocations": _component_summary(rows),
        "timing_layers": _timing_summary(rows),
    }

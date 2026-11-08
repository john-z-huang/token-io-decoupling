"""合成遥测的完整性、来源稳定性与可比较性检查。"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from benchmark_metrics import FIXED_MODEL

from .models import ARMS, CALLER_REASONING_EFFORT, EXPECTED_CASE_COUNT, MAX_HTTP_ATTEMPTS
from .summaries import _call_summary


def _usage_is_complete(summary: Mapping[str, object]) -> bool:
    for component in ("caller", "inner"):
        aggregate = summary.get(component)
        if not isinstance(aggregate, Mapping):
            return False
        coverage = aggregate.get("usage_coverage")
        if not isinstance(coverage, Mapping):
            return False
        count = coverage.get("total_calls")
        complete = coverage.get("complete_calls")
        if type(count) is not int or count == 0 or complete != count:
            return False
    return True


def _settings_valid(calls: Sequence[Mapping[str, object]]) -> bool:
    caller = [call for call in calls if call.get("component") == "caller"]
    inner = [call for call in calls if call.get("component") == "inner"]
    return (
        len(caller) >= 10
        and len(inner) >= 2
        and all(
            call.get("requested_model") == FIXED_MODEL
            and call.get("requested_effort") == CALLER_REASONING_EFFORT
            for call in caller
        )
        and all(call.get("requested_model") == FIXED_MODEL for call in inner)
    )


def _validation(
    rows: Sequence[Mapping[str, object]],
    calls: Sequence[Mapping[str, object]],
    *,
    fingerprints: Mapping[str, object],
    http_attempts: int,
) -> dict[str, object]:
    executed = [row for row in rows if row.get("execution_status") == "executed"]
    errors = [row for row in rows if row.get("execution_status") == "error"]
    unrun = [row for row in rows if row.get("execution_status") == "unrun"]
    source_hashes = fingerprints.get("sources")
    dataset_hashes = fingerprints.get("dataset")
    metadata_hashes = fingerprints.get("metadata")
    source_stable = isinstance(source_hashes, Mapping) and source_hashes.get("stable") is True
    dataset_stable = isinstance(dataset_hashes, Mapping) and dataset_hashes.get("stable") is True
    metadata_stable = isinstance(metadata_hashes, Mapping) and metadata_hashes.get("stable") is True
    row_source_stable = all(
        isinstance((result := row.get("raw_case_row")), Mapping)
        and isinstance(result.get("source_hashes"), Mapping)
        and result["source_hashes"].get("stable") is True
        for row in executed
    ) and bool(executed)
    metadata_matches = (
        all(
            isinstance((result := row.get("raw_case_row")), Mapping)
            and result.get("metadata_hash") == metadata_hashes.get("before", {}).get(row["case_id"])
            for row in executed
        )
        if isinstance(metadata_hashes, Mapping)
        and isinstance(metadata_hashes.get("before"), Mapping)
        else False
    )
    summary = _call_summary(calls)
    usage_complete = _usage_is_complete(summary)
    settings_valid = _settings_valid(calls)
    attempts_within_cap = 0 <= http_attempts <= MAX_HTTP_ATTEMPTS
    execution_complete = (
        len(executed) == EXPECTED_CASE_COUNT * len(ARMS) and not errors and not unrun
    )
    attempt_cap_blocked = any(
        call.get("error_type") == "BenchmarkHTTPAttemptLimitExceeded" for call in calls
    )
    measurement_valid = (
        execution_complete
        and source_stable
        and dataset_stable
        and metadata_stable
        and row_source_stable
        and metadata_matches
        and attempts_within_cap
        and not attempt_cap_blocked
        and settings_valid
    )
    semantic_valid = all(row.get("semantic_success") is True for row in executed) and bool(executed)
    return {
        "executed_rows": len(executed),
        "error_rows": len(errors),
        "unrun_rows": len(unrun),
        "source_stable": source_stable and row_source_stable,
        "metadata_stable": metadata_stable and metadata_matches,
        "dataset_stable": dataset_stable,
        "api_settings_valid": settings_valid,
        "attempts_within_cap": attempts_within_cap,
        "attempt_cap_blocked": attempt_cap_blocked,
        "usage_complete": usage_complete,
        "measurement_valid": measurement_valid,
        "semantic_valid": semantic_valid,
        "token_comparison_valid": measurement_valid and usage_complete and semantic_valid,
    }

"""Run the finite, opt-in optimization benchmark and save safe evidence."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import logging
import math
import os
import sys
import tempfile
from collections import Counter, defaultdict
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from benchmark_metrics import FIXED_MODEL, Recorder, aggregate_calls

ARMS = ("baseline", "assisted")
EXPECTED_CASE_COUNT = 5
MAX_HTTP_ATTEMPTS = 30
CALLER_REASONING_EFFORT = "medium"
_REDACTED_KEYS = {
    "api_key",
    "authorization",
    "base_url",
    "headers",
    "raw_error",
    "raw_exception",
    "error_message",
    "exception_message",
}


def _suppress_sdk_logs() -> None:
    """Silence SDK/transport logs before any live call or case import."""

    os.environ.pop("OPENAI_LOG", None)
    logging.disable(logging.CRITICAL)
    for name in ("openai", "httpx2", "httpx2._client"):
        logger = logging.getLogger(name)
        logger.disabled = True
        logger.propagate = False
        logger.setLevel(logging.CRITICAL + 1)


def _load_case_module() -> Any:
    return importlib.import_module("benchmark_cases")


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _canonical_hash(value: object) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return _sha256(payload)


def _json_safe(value: object) -> object:
    if value is None or type(value) in {bool, int, str}:
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, BaseException):
        return {"error_type": type(value).__name__}
    if isinstance(value, Mapping):
        result: dict[str, object] = {}
        for key, item in value.items():
            key_text = str(key)
            if key_text.lower() in _REDACTED_KEYS:
                continue
            result[key_text] = _json_safe(item)
        return result
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        try:
            return _json_safe(model_dump(mode="json"))
        except Exception:
            return {"value_type": type(value).__name__}
    return {"value_type": type(value).__name__}


def _write_json(fd: int, report: Mapping[str, object]) -> None:
    payload = (
        json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"
    ).encode("utf-8")
    os.lseek(fd, 0, os.SEEK_SET)
    os.ftruncate(fd, 0)
    offset = 0
    while offset < len(payload):
        offset += os.write(fd, payload[offset:])
    os.fsync(fd)


def _reserve_output(path_value: str | Path) -> tuple[Path, int]:
    requested = Path(path_value).expanduser()
    if not requested.name:
        raise ValueError("output_must_name_a_new_file")
    parent = requested.parent.resolve(strict=True)
    if not parent.is_dir():
        raise ValueError("output_parent_must_be_a_directory")
    output_path = parent / requested.name
    fd = os.open(output_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    return output_path, fd


def _row_id(case_id: str, arm: str) -> str:
    return f"{case_id}:{arm}"


def _empty_rows(case_ids: Sequence[str]) -> list[dict[str, object]]:
    return [
        {
            "case_id": case_id,
            "arm": arm,
            "execution_status": "unrun",
            "semantic_success": None,
            "error_type": None,
            "http_attempts": 0,
            "api_calls": [],
            "api_usage": aggregate_calls([]),
            "raw_case_row": None,
            "unrun_reason": "benchmark_not_started",
        }
        for case_id in case_ids
        for arm in ARMS
    ]


def _source_manifest(case_module: Any, case_ids: Sequence[str], repo_root: Path) -> list[str]:
    paths = list(case_module._COMMON_SOURCES)
    case_sources = case_module._CASE_SOURCES
    for case_id in case_ids:
        paths.extend(case_sources[case_id])
    paths.extend(
        [
            "mcp/tests/support/benchmark_cases.py",
            "mcp/tests/support/benchmark_metrics.py",
            "mcp/tests/support/optimization_benchmark.py",
        ]
    )
    dataset_path = Path(case_module.DATASET_PATH).resolve(strict=True)
    paths.append(dataset_path.relative_to(repo_root.resolve()).as_posix())
    return sorted(set(str(path) for path in paths))


def _snapshot_sources(
    repo_root: Path, paths: Sequence[str]
) -> tuple[dict[str, str | None], dict[str, str]]:
    hashes: dict[str, str | None] = {}
    errors: dict[str, str] = {}
    for relative in paths:
        try:
            hashes[relative] = _sha256((repo_root / relative).read_bytes())
        except OSError as exc:
            hashes[relative] = None
            errors[relative] = type(exc).__name__
    return hashes, errors


def _dataset_snapshot(case_module: Any, case_ids: Sequence[str]) -> dict[str, object]:
    path = Path(case_module.DATASET_PATH)
    try:
        raw = path.read_bytes()
        dataset = json.loads(raw)
        discovered = tuple(item["case_id"] for item in dataset["cases"])
        return {
            "sha256": _sha256(raw),
            "case_ids": list(discovered),
            "matches_fixed_case_order": discovered == tuple(case_ids),
            "error_type": None,
        }
    except Exception as exc:
        return {
            "sha256": None,
            "case_ids": None,
            "matches_fixed_case_order": False,
            "error_type": type(exc).__name__,
        }


def _metadata_snapshot(
    case_module: Any, case_ids: Sequence[str]
) -> tuple[dict[str, str | None], dict[str, str]]:
    hashes: dict[str, str | None] = {}
    errors: dict[str, str] = {}
    for case_id in case_ids:
        try:
            service = case_module._CASES[case_id]["service"]
            metadata, _source_paths = case_module._service_metadata(service)
            hashes[case_id] = _canonical_hash(metadata)
        except Exception as exc:
            hashes[case_id] = None
            errors[case_id] = type(exc).__name__
    return hashes, errors


def _missing_credentials() -> list[str]:
    return [
        name
        for name in ("OPENAI_API_KEY", "OPENAI_BASE_URL")
        if not (os.environ.get(name) or "").strip()
    ]


def _dataset_protocol_version(case_module: Any) -> object:
    dataset = getattr(case_module, "DATASET", None)
    if isinstance(dataset, Mapping):
        return _json_safe(dataset.get("protocol_version"))
    return _json_safe(getattr(dataset, "protocol_version", None))


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


def _timing_summary(rows: Sequence[Mapping[str, object]]) -> dict[str, object]:
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


def _report_summary(
    rows: Sequence[Mapping[str, object]], calls: Sequence[Mapping[str, object]]
) -> dict[str, object]:
    return {
        **_call_summary(calls),
        "component_invocations": _component_summary(rows),
        "timing_layers": _timing_summary(rows),
    }


def _fingerprints(
    case_module: Any,
    case_ids: Sequence[str],
    repo_root: Path,
    source_paths: Sequence[str],
    source_errors_before: Mapping[str, str],
    source_before: Mapping[str, str | None],
    dataset_before: Mapping[str, object],
    metadata_before: Mapping[str, str | None],
    metadata_errors_before: Mapping[str, str],
) -> dict[str, object]:
    source_after, source_errors_after = _snapshot_sources(repo_root, source_paths)
    dataset_after = _dataset_snapshot(case_module, case_ids)
    metadata_after, metadata_errors_after = _metadata_snapshot(case_module, case_ids)
    return {
        "sources": {
            "before": dict(source_before),
            "after": source_after,
            "errors_before": dict(source_errors_before),
            "errors_after": source_errors_after,
            "stable": not source_errors_before
            and not source_errors_after
            and dict(source_before) == source_after,
        },
        "dataset": {
            "before": dict(dataset_before),
            "after": dataset_after,
            "stable": (
                dataset_before.get("error_type") is None
                and dataset_after.get("error_type") is None
                and dataset_before.get("sha256") == dataset_after.get("sha256")
                and dataset_before.get("matches_fixed_case_order") is True
                and dataset_after.get("matches_fixed_case_order") is True
            ),
        },
        "metadata": {
            "before": dict(metadata_before),
            "after": metadata_after,
            "errors_before": dict(metadata_errors_before),
            "errors_after": metadata_errors_after,
            "stable": not metadata_errors_before
            and not metadata_errors_after
            and dict(metadata_before) == metadata_after,
        },
    }


def run_benchmark(
    output: str | Path,
    *,
    repo_root: Path,
    case_module: Any | None = None,
    recorder_factory: Callable[..., Any] = Recorder,
) -> dict[str, object]:
    """Run each fixed case once per arm and persist partial-safe JSON evidence."""

    output_path, output_fd = _reserve_output(output)
    started_at = _now()
    case_ids: tuple[str, ...] = ()
    rows: list[dict[str, object]] = []
    report: dict[str, object] = {
        "schema_version": 1,
        "status": "starting",
        "started_at_utc": started_at,
        "finished_at_utc": None,
        "fixed_model": FIXED_MODEL,
        "caller_reasoning_effort": CALLER_REASONING_EFFORT,
        "max_http_attempts": MAX_HTTP_ATTEMPTS,
        "protocol_version": None,
        "case_ids": [],
        "arms": list(ARMS),
        "rows": rows,
        "api_calls": [],
        "http_attempts": 0,
        "summary": _report_summary(rows, []),
        "fingerprints": {},
        "validation": {},
        "blocking_reason": None,
    }
    recorder: Any | None = None
    try:
        _write_json(output_fd, report)
        root = repo_root.resolve(strict=True)
        if case_module is None:
            case_module = _load_case_module()
        case_ids = tuple(case_module.CASE_IDS)
        if len(case_ids) != EXPECTED_CASE_COUNT or len(set(case_ids)) != EXPECTED_CASE_COUNT:
            raise ValueError("benchmark_requires_exactly_five_unique_cases")
        rows = _empty_rows(case_ids)
        report["case_ids"] = list(case_ids)
        report["protocol_version"] = _dataset_protocol_version(case_module)
        report["rows"] = rows
        _write_json(output_fd, report)
        source_paths = _source_manifest(case_module, case_ids, root)
        source_before, source_errors_before = _snapshot_sources(root, source_paths)
        dataset_before = _dataset_snapshot(case_module, case_ids)
        metadata_before, metadata_errors_before = _metadata_snapshot(case_module, case_ids)
        report["fingerprints"] = {
            "sources": {
                "before": source_before,
                "after": None,
                "stable": None,
                "errors_before": source_errors_before,
            },
            "dataset": {"before": dataset_before, "after": None, "stable": None},
            "metadata": {
                "before": metadata_before,
                "after": None,
                "stable": None,
                "errors_before": metadata_errors_before,
            },
        }
        if source_errors_before or metadata_errors_before:
            report["status"] = "blocked"
            report["blocking_reason"] = "source_or_metadata_snapshot_failed"
        elif (
            dataset_before.get("error_type") is not None
            or dataset_before.get("matches_fixed_case_order") is not True
        ):
            report["status"] = "blocked"
            report["blocking_reason"] = "dataset_does_not_match_fixed_case_order"
        else:
            missing = _missing_credentials()
            if missing:
                report["status"] = "blocked"
                report["blocking_reason"] = "required_process_environment_missing"
                report["missing_environment_keys"] = missing
            else:
                recorder = recorder_factory(max_http_attempts=MAX_HTTP_ATTEMPTS)
                report["status"] = "running"
                row_index = 0
                stopped_reason: str | None = None
                with tempfile.TemporaryDirectory(prefix="token-io-optimization-") as temporary:
                    temporary_root = Path(temporary).resolve(strict=True)
                    for case_id in case_ids:
                        for arm in ARMS:
                            row = rows[row_index]
                            row_index += 1
                            if int(getattr(recorder, "http_attempts", 0)) >= MAX_HTTP_ATTEMPTS:
                                row["unrun_reason"] = "http_attempt_cap_reached"
                                stopped_reason = "http_attempt_cap_reached"
                                continue
                            calls_start = len(recorder.calls)
                            attempts_start = int(recorder.http_attempts)
                            try:
                                raw_row = case_module.run_case(
                                    case_id,
                                    arm,
                                    recorder,
                                    root,
                                    temporary_root,
                                )
                                if not isinstance(raw_row, Mapping):
                                    raise TypeError("benchmark_case_result_must_be_a_mapping")
                                row["execution_status"] = "executed"
                                row["semantic_success"] = (
                                    raw_row.get("semantic_success")
                                    if type(raw_row.get("semantic_success")) is bool
                                    else None
                                )
                                row["raw_case_row"] = _json_safe(raw_row)
                                row["error_type"] = None
                            except Exception as exc:
                                row["execution_status"] = "error"
                                row["error_type"] = type(exc).__name__
                                row["raw_case_row"] = None
                                row["unrun_reason"] = None
                                stopped_reason = stopped_reason or None
                            calls_end = list(recorder.calls[calls_start:])
                            row["api_calls"] = _json_safe(calls_end)
                            row["http_attempts"] = int(recorder.http_attempts) - attempts_start
                            row["api_usage"] = aggregate_calls(calls_end)
                            if int(getattr(recorder, "http_attempts", 0)) >= MAX_HTTP_ATTEMPTS:
                                stopped_reason = "http_attempt_cap_reached"
                            row["unrun_reason"] = None
                            report["api_calls"] = _json_safe(list(recorder.calls))
                            report["http_attempts"] = int(recorder.http_attempts)
                            report["summary"] = _report_summary(rows, list(recorder.calls))
                            _write_json(output_fd, report)
                            print(
                                f"case={case_id} arm={arm} status={row['execution_status']} "
                                f"api_calls={len(calls_end)} http_attempts={row['http_attempts']}",
                                file=sys.stderr,
                            )
                            if stopped_reason == "http_attempt_cap_reached":
                                for remaining in rows[row_index:]:
                                    remaining["unrun_reason"] = "http_attempt_cap_reached"
                                break
                        if stopped_reason == "http_attempt_cap_reached":
                            break
                if stopped_reason is not None:
                    report["blocking_reason"] = stopped_reason

        fingerprints = _fingerprints(
            case_module,
            case_ids,
            root,
            source_paths,
            source_errors_before,
            source_before,
            dataset_before,
            metadata_before,
            metadata_errors_before,
        )
        report["fingerprints"] = fingerprints
        all_calls = list(getattr(recorder, "calls", [])) if recorder is not None else []
        report["api_calls"] = _json_safe(all_calls)
        report["http_attempts"] = (
            int(getattr(recorder, "http_attempts", 0)) if recorder is not None else 0
        )
        report["summary"] = _report_summary(rows, all_calls)
        report["validation"] = _validation(
            rows,
            all_calls,
            fingerprints=fingerprints,
            http_attempts=int(getattr(recorder, "http_attempts", 0)) if recorder is not None else 0,
        )
        if report["status"] == "running":
            report["status"] = (
                "complete" if report["validation"].get("measurement_valid") is True else "partial"
            )
        report["finished_at_utc"] = _now()
        _write_json(output_fd, report)
        return report
    except Exception as exc:
        report["status"] = "error"
        report["blocking_reason"] = "benchmark_runner_error"
        report["runner_error_type"] = type(exc).__name__
        report["api_calls"] = _json_safe(list(getattr(recorder, "calls", [])))
        report["http_attempts"] = (
            int(getattr(recorder, "http_attempts", 0)) if recorder is not None else 0
        )
        report["summary"] = _report_summary(
            rows, list(getattr(recorder, "calls", [])) if recorder is not None else []
        )
        report["finished_at_utc"] = _now()
        try:
            _write_json(output_fd, report)
        except OSError:
            pass
        return report
    finally:
        os.close(output_fd)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="run the authorized live API benchmark")
    parser.add_argument(
        "--output", type=Path, help="path to a new JSON output file; never overwritten"
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.live:
        if args.output is not None:
            print("--output requires --live; no output file was created", file=sys.stderr)
            return 2
        _suppress_sdk_logs()
        case_module = _load_case_module()
        print(
            json.dumps(
                {
                    "status": "dry_run",
                    "case_ids": list(case_module.CASE_IDS),
                    "arms": list(ARMS),
                    "live_api_calls": 0,
                    "http_attempt_cap": MAX_HTTP_ATTEMPTS,
                    "use_live_flag_and_new_output_path_to_run": True,
                },
                sort_keys=True,
            )
        )
        return 0
    if args.output is None:
        print("--live requires --output pointing to a new file", file=sys.stderr)
        return 2
    _suppress_sdk_logs()
    repo_root = Path(__file__).resolve().parents[3]
    try:
        report = run_benchmark(args.output, repo_root=repo_root)
    except (OSError, ValueError) as exc:
        print(f"benchmark_output_rejected: {type(exc).__name__}", file=sys.stderr)
        return 2
    return 0 if report.get("status") == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())

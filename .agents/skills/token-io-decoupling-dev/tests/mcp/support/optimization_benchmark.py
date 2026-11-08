"""Retire incompatible live protocols and exercise synthetic telemetry fixtures only."""

from __future__ import annotations

import argparse
import importlib
import json
import logging
import os
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from benchmark_metrics import FIXED_MODEL as FIXED_MODEL
from benchmark_metrics import Recorder
from benchmark_metrics import aggregate_calls as aggregate_calls
from benchmark_support.models import (
    ARMS as ARMS,
)
from benchmark_support.models import (
    CALLER_REASONING_EFFORT as CALLER_REASONING_EFFORT,
)
from benchmark_support.models import (
    EXPECTED_CASE_COUNT as EXPECTED_CASE_COUNT,
)
from benchmark_support.models import (
    MAX_HTTP_ATTEMPTS as MAX_HTTP_ATTEMPTS,
)
from benchmark_support.models import (
    BenchmarkReport as BenchmarkReport,
)
from benchmark_support.models import (
    TimingLayer as TimingLayer,
)
from benchmark_support.runner import BenchmarkRun
from benchmark_support.runner import (
    _empty_rows as _empty_rows,
)
from benchmark_support.runner import (
    _missing_credentials as _missing_credentials,
)
from benchmark_support.serialization import (
    _REDACTED_KEYS as _REDACTED_KEYS,
)
from benchmark_support.serialization import (
    _canonical_hash as _canonical_hash,
)
from benchmark_support.serialization import (
    _json_safe as _json_safe,
)
from benchmark_support.serialization import (
    _now as _now,
)
from benchmark_support.serialization import (
    _reserve_output as _reserve_output,
)
from benchmark_support.serialization import (
    _sha256 as _sha256,
)
from benchmark_support.serialization import (
    _write_json as _write_json,
)
from benchmark_support.snapshots import (
    _dataset_protocol_version as _dataset_protocol_version,
)
from benchmark_support.snapshots import (
    _dataset_snapshot as _dataset_snapshot,
)
from benchmark_support.snapshots import (
    _fingerprints as _fingerprints,
)
from benchmark_support.snapshots import (
    _metadata_snapshot as _metadata_snapshot,
)
from benchmark_support.snapshots import (
    _snapshot_sources as _snapshot_sources,
)
from benchmark_support.snapshots import (
    _source_manifest as _source_manifest,
)
from benchmark_support.summaries import (
    _call_summary as _call_summary,
)
from benchmark_support.summaries import (
    _component_summary as _component_summary,
)
from benchmark_support.summaries import (
    _report_summary as _report_summary,
)
from benchmark_support.summaries import (
    _row_id as _row_id,
)
from benchmark_support.summaries import (
    _timing_summary as _timing_summary,
)
from benchmark_support.validation import (
    _settings_valid as _settings_valid,
)
from benchmark_support.validation import (
    _usage_is_complete as _usage_is_complete,
)
from benchmark_support.validation import (
    _validation as _validation,
)


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


def run_benchmark(
    output: str | Path,
    *,
    repo_root: Path,
    case_module: Any | None = None,
    recorder_factory: Callable[..., Any] = Recorder,
) -> BenchmarkReport:
    """拒绝退役的真实测量协议，只允许注入 recorder 的合成遥测测试。"""
    _output_path, output_fd = _reserve_output(output)
    try:
        run = BenchmarkRun(output_fd, repo_root, recorder_factory)
        return run.run(case_module, _load_case_module, Recorder)
    finally:
        os.close(output_fd)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--live",
        action="store_true",
        help="legacy request flag; the current protocol is retired and makes no API calls",
    )
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
                    "status": "retired",
                    "blocking_reason": "retired_benchmark_protocol",
                    "case_ids": list(case_module.CASE_IDS),
                    "arms": list(ARMS),
                    "live_api_calls": 0,
                    "http_attempt_cap": MAX_HTTP_ATTEMPTS,
                    "use_live_flag_and_new_output_path_to_run": False,
                    "token_comparison_valid": False,
                },
                sort_keys=True,
            )
        )
        return 1
    if args.output is None:
        print("--live requires --output pointing to a new file", file=sys.stderr)
        return 2
    _suppress_sdk_logs()
    repo_root = Path(__file__).resolve().parents[6]
    try:
        report = run_benchmark(args.output, repo_root=repo_root)
    except (OSError, ValueError) as exc:
        print(f"benchmark_output_rejected: {type(exc).__name__}", file=sys.stderr)
        return 2
    return 0 if report.get("status") == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())

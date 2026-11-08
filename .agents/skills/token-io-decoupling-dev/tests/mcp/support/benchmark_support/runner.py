"""按协议、准备、执行和收尾阶段管理一次合成基准运行。"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from benchmark_metrics import FIXED_MODEL, aggregate_calls

from .execution import CaseExecutor, report_progress
from .models import (
    ARMS,
    CALLER_REASONING_EFFORT,
    EXPECTED_CASE_COUNT,
    MAX_HTTP_ATTEMPTS,
    BenchmarkReport,
)
from .serialization import _now, _safe_mapping, _write_json
from .snapshots import EvidenceSnapshot, _dataset_protocol_version
from .summaries import _report_summary
from .validation import _validation


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


def _missing_credentials() -> list[str]:
    return [
        name
        for name in ("OPENAI_API_KEY", "OPENAI_BASE_URL")
        if not (os.environ.get(name) or "").strip()
    ]


def _new_report(rows: list[dict[str, Any]]) -> BenchmarkReport:
    return {
        "schema_version": 1,
        "status": "starting",
        "started_at_utc": _now(),
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


class BenchmarkRun:
    """持有单次运行的可变报告和 recorder，不在不同运行间共享状态。"""

    def __init__(self, output_fd: int, root: Path, recorder_factory: Callable[..., Any]) -> None:
        self.output_fd = output_fd
        self.root = root
        self.recorder_factory = recorder_factory
        self.recorder: Any | None = None
        self.case_module: Any = None
        self.case_ids: tuple[str, ...] = ()
        self.rows: list[dict[str, Any]] = []
        self.report = _new_report(self.rows)

    def run(
        self, case_module: Any, loader: Callable[[], Any], live_recorder: type
    ) -> BenchmarkReport:
        try:
            self.write()
            self.root = self.root.resolve(strict=True)
            self.case_module = case_module if case_module is not None else loader()
            self.case_ids = tuple(self.case_module.CASE_IDS)
            if self._allow_synthetic(live_recorder):
                self._run_synthetic()
            self.finish()
        except Exception as exc:
            self._runner_error(exc)
        return self.report

    def _allow_synthetic(self, live_recorder: type) -> bool:
        protocol_status = getattr(self.case_module, "PROTOCOL_STATUS", "unsupported")
        self.report["protocol_status"] = protocol_status
        self.report["protocol_version"] = _dataset_protocol_version(self.case_module)
        self.report["case_ids"] = list(self.case_ids)
        if (
            protocol_status == "synthetic_test_fixture"
            and self.recorder_factory is not live_recorder
        ):
            return True
        retired = protocol_status == "retired"
        self.report["status"] = "retired" if retired else "blocked"
        self.report["blocking_reason"] = (
            "retired_benchmark_protocol" if retired else "no_supported_live_benchmark_protocol"
        )
        self.report["validation"] = {"measurement_valid": False, "token_comparison_valid": False}
        return False

    def _run_synthetic(self) -> None:
        self.report["comparison_scope"] = "synthetic_test_only"
        if (
            len(self.case_ids) != EXPECTED_CASE_COUNT
            or len(set(self.case_ids)) != EXPECTED_CASE_COUNT
        ):
            raise ValueError("benchmark_requires_exactly_five_unique_cases")
        self.rows = _empty_rows(self.case_ids)
        self.report["case_ids"] = list(self.case_ids)
        self.report["protocol_version"] = _dataset_protocol_version(self.case_module)
        self.report["rows"] = self.rows
        self.write()
        before = EvidenceSnapshot.capture(self.case_module, self.case_ids, self.root)
        self.report["fingerprints"] = before.initial()
        reason = before.blocking_reason()
        if reason is not None:
            self.report["status"] = "blocked"
            self.report["blocking_reason"] = reason
        else:
            self._start_cases()
        self._complete_synthetic(before)

    def _start_cases(self) -> None:
        missing = _missing_credentials()
        if missing:
            self.report["status"] = "blocked"
            self.report["blocking_reason"] = "required_process_environment_missing"
            self.report["missing_environment_keys"] = missing
            return
        self.recorder = self.recorder_factory(max_http_attempts=MAX_HTTP_ATTEMPTS)
        self.report["status"] = "running"
        reason = self._run_cases()
        if reason is not None:
            self.report["blocking_reason"] = reason

    def _run_cases(self) -> str | None:
        executor = CaseExecutor(self.case_module, self.recorder, self.root)
        with tempfile.TemporaryDirectory(prefix="token-io-optimization-") as temporary:
            temporary_root = Path(temporary).resolve(strict=True)
            for index, row in enumerate(self.rows):
                if int(getattr(self.recorder, "http_attempts", 0)) >= MAX_HTTP_ATTEMPTS:
                    return self._skip_capped_case(index)
                executor.execute(row, temporary_root)
                self._refresh_calls()
                self.write()
                report_progress(row)
                if int(getattr(self.recorder, "http_attempts", 0)) >= MAX_HTTP_ATTEMPTS:
                    return self._skip_remaining(index + 1)
        return None

    def _skip_capped_case(self, first_unrun: int) -> str:
        # 保留旧的分组循环语义：进入时已满额，只标记当前案例的两个 arm。
        case_end = (first_unrun // len(ARMS) + 1) * len(ARMS)
        for row in self.rows[first_unrun:case_end]:
            row["unrun_reason"] = "http_attempt_cap_reached"
        return "http_attempt_cap_reached"

    def _skip_remaining(self, first_unrun: int) -> str:
        for row in self.rows[first_unrun:]:
            row["unrun_reason"] = "http_attempt_cap_reached"
        return "http_attempt_cap_reached"

    def _refresh_calls(self) -> None:
        calls = list(getattr(self.recorder, "calls", [])) if self.recorder is not None else []
        self.report["api_calls"] = [_safe_mapping(call) for call in calls]
        self.report["http_attempts"] = (
            int(getattr(self.recorder, "http_attempts", 0)) if self.recorder is not None else 0
        )
        self.report["summary"] = _report_summary(self.rows, calls)

    def _complete_synthetic(self, before: EvidenceSnapshot) -> None:
        fingerprints = before.compare(self.case_module, self.case_ids, self.root)
        self.report["fingerprints"] = fingerprints
        self._refresh_calls()
        calls = list(getattr(self.recorder, "calls", [])) if self.recorder is not None else []
        self.report["validation"] = _validation(
            self.rows, calls, fingerprints=fingerprints, http_attempts=self.report["http_attempts"]
        )
        telemetry_valid = self.report["validation"].get("measurement_valid") is True
        self.report["validation"]["synthetic_telemetry_valid"] = telemetry_valid
        self.report["validation"]["measurement_valid"] = False
        self.report["validation"]["token_comparison_valid"] = False
        if self.report["status"] == "running":
            self.report["status"] = "synthetic_complete" if telemetry_valid else "synthetic_partial"

    def _runner_error(self, exc: Exception) -> None:
        self.report["status"] = "error"
        self.report["blocking_reason"] = "benchmark_runner_error"
        self.report["runner_error_type"] = type(exc).__name__
        self._refresh_calls()
        try:
            self.finish()
        except OSError:
            # 仍返回内存中的安全报告；无法再写输出时不覆盖原始错误类别。
            pass

    def write(self) -> None:
        _write_json(self.output_fd, self.report)

    def finish(self) -> None:
        self.report["finished_at_utc"] = _now()
        self.write()

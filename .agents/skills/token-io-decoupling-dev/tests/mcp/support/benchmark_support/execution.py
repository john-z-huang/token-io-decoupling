"""隔离单个合成案例的异常，并记录该案例的调用与尝试次数。"""

from __future__ import annotations

import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from benchmark_metrics import aggregate_calls

from .serialization import _json_safe


class CaseExecutor:
    def __init__(self, case_module: Any, recorder: Any, root: Path) -> None:
        self.case_module = case_module
        self.recorder = recorder
        self.root = root

    def execute(self, row: dict[str, object], temporary_root: Path) -> None:
        calls_start = len(self.recorder.calls)
        attempts_start = int(self.recorder.http_attempts)
        try:
            result = self.case_module.run_case(
                row["case_id"], row["arm"], self.recorder, self.root, temporary_root
            )
            if not isinstance(result, Mapping):
                raise TypeError("benchmark_case_result_must_be_a_mapping")
            row["execution_status"] = "executed"
            row["semantic_success"] = (
                result.get("semantic_success")
                if type(result.get("semantic_success")) is bool
                else None
            )
            row["raw_case_row"] = _json_safe(result)
            row["error_type"] = None
        except Exception as exc:
            # 案例是可注入的测试边界；报告保留失败类别，不泄漏异常文本。
            row["execution_status"] = "error"
            row["error_type"] = type(exc).__name__
            row["raw_case_row"] = None
            row["unrun_reason"] = None
        calls = list(self.recorder.calls[calls_start:])
        row["api_calls"] = _json_safe(calls)
        row["http_attempts"] = int(self.recorder.http_attempts) - attempts_start
        row["api_usage"] = aggregate_calls(calls)
        row["unrun_reason"] = None


def report_progress(row: Mapping[str, Any]) -> None:
    print(
        f"case={row['case_id']} arm={row['arm']} status={row['execution_status']} "
        f"api_calls={len(row['api_calls'])} http_attempts={row['http_attempts']}",
        file=sys.stderr,
    )

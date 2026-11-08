"""构建有界校验发现与批次结果。"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .constants import (
    MAX_BATCH_UTF8_BYTES,
    MAX_CANDIDATES,
    MAX_CHECK_MESSAGE_CHARS,
    MAX_DIRECT_TARGETS,
    MAX_FILE_CHARS,
    MAX_OUTPUT_CHECKS,
    MAX_PATH_CHARS,
    POLICY_VERSION,
)


def build_result(
    policy_scope: str,
    checks: Sequence[Mapping[str, Any]],
    *,
    direct_targets_read: int = 0,
    target_limit_exceeded: bool = False,
) -> dict[str, Any]:
    all_statuses = [item.get("status") for item in checks if item.get("status") != "not_applicable"]
    bounded = [dict(item) for item in checks[:MAX_OUTPUT_CHECKS]]
    if len(checks) > MAX_OUTPUT_CHECKS:
        bounded[-1] = _finding(
            "output_check_budget",
            "unknown",
            None,
            None,
            "check output budget was exceeded; additional checks were omitted",
            reason_code="output_check_budget_exceeded",
            evidence_missing=["checks omitted after the configured output-check budget"],
        )
    status = (
        "fail"
        if "fail" in all_statuses
        else "unknown"
        if "unknown" in all_statuses
        else "pass"
        if "pass" in all_statuses
        else "not_applicable"
    )
    return {
        "status": status,
        "policy_scope": policy_scope,
        "policy_version": POLICY_VERSION,
        "checks": bounded,
        "not_evaluated": [
            "reverse inbound-link scans across unchanged documents",
            "semantic equivalence between English and Simplified Chinese mirrors",
            "full repository CI and final integration acceptance",
        ],
        "limits": {
            "max_candidates": MAX_CANDIDATES,
            "max_path_chars": MAX_PATH_CHARS,
            "max_file_chars": MAX_FILE_CHARS,
            "max_batch_utf8_bytes": MAX_BATCH_UTF8_BYTES,
            "max_direct_targets": MAX_DIRECT_TARGETS,
            "direct_targets_read": direct_targets_read,
            "direct_target_limit_exceeded": target_limit_exceeded,
            "max_checks": MAX_OUTPUT_CHECKS,
            "checks_returned": len(bounded),
            "checks_truncated": len(checks) > MAX_OUTPUT_CHECKS,
        },
    }


def _finding(
    rule: str,
    status: str,
    path: str | None,
    line: int | None,
    message: str,
    *,
    target_path: str | None = None,
    reason_code: str | None = None,
    evidence_missing: Sequence[str] | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "rule_id": rule,
        "status": status,
        "path": path,
        "line": line,
        "message": message[:MAX_CHECK_MESSAGE_CHARS],
        "evidence_missing": [
            item[:MAX_CHECK_MESSAGE_CHARS] for item in (evidence_missing or [])[:8]
        ],
    }
    if target_path is not None:
        result["target_path"] = target_path[:MAX_PATH_CHARS]
    if reason_code is not None:
        result["reason_code"] = reason_code
    return result

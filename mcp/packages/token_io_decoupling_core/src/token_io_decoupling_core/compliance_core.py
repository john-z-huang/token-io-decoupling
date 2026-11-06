"""Generic bounded candidate validation; repository authoring checks are private."""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence
from pathlib import PurePosixPath
from typing import Any

MAX_CANDIDATES = 64
MAX_PATH_CHARS = 512
MAX_FILE_CHARS = 131_072
MAX_BATCH_UTF8_BYTES = 524_288
MAX_DIRECT_TARGETS = 256
MAX_OUTPUT_CHECKS = 512
MAX_CHECK_MESSAGE_CHARS = 512
POLICY_VERSION = 2
POLICY_SCOPES = frozenset({"generic_project"})
OPERATIONS = frozenset({"create", "replace", "delete"})
STATUS_VALUES = frozenset({"pass", "fail", "unknown", "not_applicable"})


class ComplianceInputError(ValueError):
    """Raised when a caller-supplied candidate envelope exceeds its contract."""


def validate_relative_posix_path(value: Any) -> str:
    """Return a canonical repo-relative POSIX path or reject it without OS resolution."""
    if not isinstance(value, str) or not value or len(value) > MAX_PATH_CHARS:
        raise ComplianceInputError("candidate_path_invalid_length")
    if "\\" in value or "\x00" in value or value.startswith("/"):
        raise ComplianceInputError("candidate_path_not_relative_posix")
    parts = value.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise ComplianceInputError("candidate_path_not_canonical")
    path = PurePosixPath(value)
    if path.is_absolute() or path.as_posix() != value:
        raise ComplianceInputError("candidate_path_not_canonical")
    return value


def validate_candidate_list(candidates: Any) -> list[dict[str, Any]]:
    """Validate the bounded, provider-neutral candidate payload used by both callers."""
    if not isinstance(candidates, Sequence) or isinstance(candidates, (str, bytes)):
        raise ComplianceInputError("candidates_must_be_a_list")
    if not 1 <= len(candidates) <= MAX_CANDIDATES:
        raise ComplianceInputError("candidate_count_out_of_range")

    normalized: list[dict[str, Any]] = []
    paths: set[str] = set()
    batch_bytes = 0
    for candidate in candidates:
        if not isinstance(candidate, Mapping):
            raise ComplianceInputError("candidate_shape_invalid")
        path = validate_relative_posix_path(candidate.get("path"))
        if path in paths:
            raise ComplianceInputError("candidate_paths_must_be_unique")
        paths.add(path)
        operation = candidate.get("operation")
        baseline = candidate.get("baseline")
        content = candidate.get("content")
        if operation not in OPERATIONS or not isinstance(baseline, Mapping):
            raise ComplianceInputError("candidate_operation_or_baseline_invalid")
        state = baseline.get("state")
        digest = baseline.get("value")
        if operation == "create":
            if state != "absent" or digest is not None:
                raise ComplianceInputError("create_requires_absent_baseline")
        elif (
            state != "sha256"
            or not isinstance(digest, str)
            or not re.fullmatch(r"[0-9a-f]{64}", digest)
        ):
            raise ComplianceInputError("replace_delete_require_sha256_baseline")
        if operation == "delete":
            if content is not None:
                raise ComplianceInputError("delete_must_not_include_content")
        else:
            if not isinstance(content, str):
                raise ComplianceInputError("create_replace_require_content")
            if len(content) > MAX_FILE_CHARS:
                raise ComplianceInputError("candidate_content_char_limit_exceeded")
            try:
                encoded = content.encode("utf-8", errors="strict")
            except UnicodeEncodeError as exc:
                raise ComplianceInputError("candidate_content_not_valid_utf8") from exc
            batch_bytes += len(encoded)
            if batch_bytes > MAX_BATCH_UTF8_BYTES:
                raise ComplianceInputError("candidate_batch_byte_limit_exceeded")
        normalized.append(
            {
                "path": path,
                "operation": operation,
                "baseline": {"state": state, **({"value": digest} if digest is not None else {})},
                "content": content,
            }
        )
    return normalized


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
    if len(checks) > MAX_OUTPUT_CHECKS and status == "pass":
        status = "unknown"
    return {
        "status": status,
        "policy_scope": policy_scope,
        "policy_version": POLICY_VERSION,
        "checks": bounded,
        "not_evaluated": [
            "semantic correctness of proposed changes",
            "project-specific checks supplied by the target repository",
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


def evaluate_candidate_checks(
    policy_scope: str,
    candidates: Sequence[Mapping[str, Any]],
    baseline_checks: Sequence[Mapping[str, Any]],
    path_present: Callable[[str], bool | None],
    *,
    allowed_scope: bool,
    direct_targets_read: int = 0,
    target_limit_exceeded: bool = False,
) -> dict[str, Any]:
    """Check generic candidate evidence, without project-specific documentation rules."""
    normalized = validate_candidate_list(candidates)
    if policy_scope not in POLICY_SCOPES:
        raise ComplianceInputError("policy_scope_invalid")
    checks = [dict(item) for item in baseline_checks]
    if not allowed_scope:
        checks.extend(
            _finding(
                "policy_scope",
                "unknown",
                item["path"],
                None,
                "requested scope is not enabled by the operator-configured service",
                reason_code="policy_scope_not_allowed",
                evidence_missing=["operator allowlist entry for the requested policy scope"],
            )
            for item in normalized
        )
    if target_limit_exceeded:
        checks.append(
            _finding(
                "direct_target_budget",
                "unknown",
                None,
                None,
                "target read budget exceeded",
                reason_code="direct_target_budget_exceeded",
            )
        )
    return build_result(
        policy_scope,
        checks,
        direct_targets_read=direct_targets_read,
        target_limit_exceeded=target_limit_exceeded,
    )

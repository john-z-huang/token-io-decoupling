"""受限候选操作基线及 UTF-8 内容的规范化校验。"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from pathlib import PurePosixPath
from typing import Any

from .constants import (
    MAX_BATCH_UTF8_BYTES,
    MAX_CANDIDATES,
    MAX_FILE_CHARS,
    MAX_PATH_CHARS,
    OPERATIONS,
)


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


def _validate_candidate_baseline(operation: Any, baseline: Any) -> dict[str, Any]:
    """按操作类型校验并规范化基线，保留稳定的错误码。"""
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

    normalized = {"state": state}
    if digest is not None:
        normalized["value"] = digest
    return normalized


def _candidate_content_bytes(operation: Any, content: Any) -> int:
    """校验单文件内容并返回 UTF-8 字节数；删除操作不携带正文。"""
    if operation == "delete":
        if content is not None:
            raise ComplianceInputError("delete_must_not_include_content")
        return 0
    if not isinstance(content, str):
        raise ComplianceInputError("create_replace_require_content")
    if len(content) > MAX_FILE_CHARS:
        raise ComplianceInputError("candidate_content_char_limit_exceeded")
    try:
        return len(content.encode("utf-8", errors="strict"))
    except UnicodeEncodeError as exc:
        raise ComplianceInputError("candidate_content_not_valid_utf8") from exc


def validate_candidate_list(candidates: Any) -> list[dict[str, Any]]:
    """校验候选批次的唯一路径、操作基线及内容大小，返回规范化副本。"""
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
        content = candidate.get("content")
        baseline = _validate_candidate_baseline(operation, candidate.get("baseline"))
        batch_bytes += _candidate_content_bytes(operation, content)
        if batch_bytes > MAX_BATCH_UTF8_BYTES:
            raise ComplianceInputError("candidate_batch_byte_limit_exceeded")
        normalized.append(
            {
                "path": path,
                "operation": operation,
                "baseline": baseline,
                "content": content,
            }
        )
    return normalized

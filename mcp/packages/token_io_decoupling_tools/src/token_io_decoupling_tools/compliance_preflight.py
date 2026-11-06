"""Trusted-root, read-only compliance preflight for bounded candidate overlays."""

from __future__ import annotations

import hashlib
import os
import stat
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from token_io_decoupling_core.compliance_core import (
    MAX_BATCH_UTF8_BYTES,
    MAX_DIRECT_TARGETS,
    POLICY_SCOPES,
    build_result,
    evaluate_candidate_checks,
    validate_candidate_list,
)


@dataclass(frozen=True)
class _ReadResult:
    state: str
    data: bytes | None = None


class CompliancePreflightService:
    """Read only from a root fixed by trusted operator startup configuration."""

    def __init__(self, root: str | os.PathLike[str], allowed_scopes: Collection[str]) -> None:
        scopes = frozenset(allowed_scopes)
        if any(scope not in POLICY_SCOPES for scope in scopes):
            raise ValueError("allowed_scopes_invalid")
        required_flags = ("O_DIRECTORY", "O_NOFOLLOW")
        if any(not hasattr(os, flag) for flag in required_flags) or not hasattr(
            os, "supports_dir_fd"
        ):
            raise RuntimeError("secure_dirfd_reader_unavailable")
        if os.open not in os.supports_dir_fd:
            raise RuntimeError("secure_dirfd_reader_unavailable")
        resolved_root = Path(root).resolve(strict=True)
        root_fd = os.open(
            str(resolved_root),
            os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_CLOEXEC", 0),
        )
        if not stat.S_ISDIR(os.fstat(root_fd).st_mode):
            os.close(root_fd)
            raise ValueError("configured_root_not_directory")
        self._root_fd = root_fd
        self._closed = False
        self._allowed_scopes = scopes

    def close(self) -> None:
        if not self._closed:
            os.close(self._root_fd)
            self._closed = True

    def root_identity(self) -> tuple[int, int]:
        """Return device/inode for this service's already-pinned root descriptor."""
        if self._closed:
            raise RuntimeError("compliance_root_unavailable")
        metadata = os.fstat(self._root_fd)
        if not stat.S_ISDIR(metadata.st_mode):
            raise RuntimeError("compliance_root_unavailable")
        return int(metadata.st_dev), int(metadata.st_ino)

    def __enter__(self) -> CompliancePreflightService:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass

    def capability(self) -> dict[str, Any]:
        """Describe only the already configured reader and allowlist; do not probe paths."""
        return {
            "status": "available" if not self._closed else "unavailable",
            "reason_code": "configured_secure_read_only_backend"
            if not self._closed
            else "compliance_backend_closed",
            "policy_scopes": sorted(self._allowed_scopes),
        }

    def validate(self, request: Any) -> dict[str, Any]:
        if hasattr(request, "model_dump"):
            request = request.model_dump(mode="python")
        if not isinstance(request, Mapping):
            raise ValueError("compliance_request_invalid")
        policy_scope = request.get("policy_scope")
        candidates = validate_candidate_list(request.get("candidates"))
        if policy_scope not in self._allowed_scopes:
            baseline_checks = [
                _check(
                    "candidate_baseline",
                    "unknown",
                    item["path"],
                    "requested policy scope is not enabled by the operator-configured service",
                    reason_code="policy_scope_not_allowed",
                    evidence_missing=["operator allowlist entry for the requested policy scope"],
                )
                for item in candidates
            ]
            return evaluate_candidate_checks(
                policy_scope,
                candidates,
                baseline_checks,
                lambda _path: None,
                allowed_scope=False,
            )
        if self._closed:
            return _unavailable_result(policy_scope, candidates)

        baseline_checks = [self._baseline_check(item) for item in candidates]
        overlay_present = {item["path"] for item in candidates if item["operation"] != "delete"}
        overlay_deleted = {item["path"] for item in candidates if item["operation"] == "delete"}
        target_cache: dict[str, bool | None] = {}
        target_limit_exceeded = False

        def target_present(path: str) -> bool | None:
            nonlocal target_limit_exceeded
            if path in overlay_deleted:
                return False
            if path in overlay_present:
                return True
            if path in target_cache:
                return target_cache[path]
            if len(target_cache) >= MAX_DIRECT_TARGETS:
                target_limit_exceeded = True
                return None
            read = self._read_relative(path)
            if read.state == "missing":
                result: bool | None = False
            elif read.state == "present" and read.data is not None:
                try:
                    read.data.decode("utf-8", errors="strict")
                except UnicodeDecodeError:
                    result = None
                else:
                    result = True
            else:
                result = None
            target_cache[path] = result
            return result

        result = evaluate_candidate_checks(
            policy_scope,
            candidates,
            baseline_checks,
            target_present,
            allowed_scope=True,
        )
        result["limits"]["direct_targets_read"] = len(target_cache)
        result["limits"]["direct_target_limit_exceeded"] = target_limit_exceeded
        if target_limit_exceeded:
            return build_result(
                policy_scope,
                [
                    *result["checks"],
                    _check(
                        "direct_target_budget",
                        "unknown",
                        None,
                        "direct link and mirror target read budget was exceeded; remaining "
                        "targets were not probed",
                        reason_code="direct_target_budget_exceeded",
                    ),
                ],
                direct_targets_read=len(target_cache),
                target_limit_exceeded=True,
            )
        return result

    def _baseline_check(self, candidate: Mapping[str, Any]) -> dict[str, Any]:
        path = candidate["path"]
        baseline = candidate["baseline"]
        read = self._read_relative(path)
        operation = candidate["operation"]
        if operation == "create":
            if read.state == "missing":
                return _check("candidate_baseline", "pass", path, "create target is absent")
            if read.state == "present":
                return _check(
                    "candidate_baseline",
                    "fail",
                    path,
                    "create target already exists in the trusted root",
                    reason_code="create_target_exists",
                )
            return _check(
                "candidate_baseline",
                "unknown",
                path,
                "create target could not be safely inspected",
                reason_code="baseline_unavailable",
                evidence_missing=[
                    "safe inspection of the candidate path under the configured root"
                ],
            )
        if read.state == "missing":
            return _check(
                "candidate_baseline",
                "fail",
                path,
                "replace/delete baseline target is missing from the trusted root",
                reason_code="baseline_target_missing",
            )
        if read.state != "present" or read.data is None:
            return _check(
                "candidate_baseline",
                "unknown",
                path,
                "replace/delete baseline could not be safely read within the byte limit",
                reason_code="baseline_unavailable",
                evidence_missing=["complete current file bytes within the configured read limit"],
            )
        actual = hashlib.sha256(read.data).hexdigest()
        if actual != baseline["value"]:
            return _check(
                "candidate_baseline",
                "fail",
                path,
                "trusted-root file does not match the supplied SHA-256 baseline",
                reason_code="baseline_mismatch",
            )
        return _check("candidate_baseline", "pass", path, "trusted-root SHA-256 baseline matches")

    def _read_relative(self, path: str) -> _ReadResult:
        """Read a UTF-8-agnostic bounded file through pinned directory descriptors."""
        if self._closed:
            return _ReadResult("unavailable")
        current_fd = -1
        file_fd = -1
        try:
            parts = path.split("/")
            current_fd = os.dup(self._root_fd)
            directory_flags = (
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
            )
            for part in parts[:-1]:
                next_fd = os.open(part, directory_flags, dir_fd=current_fd)
                os.close(current_fd)
                current_fd = next_fd
            file_flags = os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
            file_flags |= getattr(os, "O_NONBLOCK", 0)
            file_fd = os.open(parts[-1], file_flags, dir_fd=current_fd)
            metadata = os.fstat(file_fd)
            if not stat.S_ISREG(metadata.st_mode):
                return _ReadResult("unavailable")
            if metadata.st_size > MAX_BATCH_UTF8_BYTES:
                if not self._relative_path_matches(parts, metadata):
                    return _ReadResult("unavailable")
                return _ReadResult("present")
            chunks: list[bytes] = []
            remaining = MAX_BATCH_UTF8_BYTES + 1
            while remaining > 0:
                chunk = os.read(file_fd, min(65_536, remaining))
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            data = b"".join(chunks)
            if len(data) > MAX_BATCH_UTF8_BYTES:
                if not self._relative_path_matches(parts, metadata):
                    return _ReadResult("unavailable")
                return _ReadResult("present")
            after_read = os.fstat(file_fd)
            if not _same_file_state(metadata, after_read):
                return _ReadResult("unavailable")
            if not self._relative_path_matches(parts, after_read):
                return _ReadResult("unavailable")
            return _ReadResult("present", data)
        except FileNotFoundError:
            return _ReadResult("missing")
        except (OSError, NotImplementedError, ValueError):
            return _ReadResult("unavailable")
        finally:
            if file_fd >= 0:
                os.close(file_fd)
            if current_fd >= 0:
                os.close(current_fd)

    def _relative_path_matches(self, parts: list[str], expected: os.stat_result) -> bool:
        """Re-open the complete path from the pinned root and compare its final inode."""
        current_fd = -1
        probe_fd = -1
        try:
            current_fd = os.dup(self._root_fd)
            directory_flags = (
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
            )
            for part in parts[:-1]:
                next_fd = os.open(part, directory_flags, dir_fd=current_fd)
                os.close(current_fd)
                current_fd = next_fd
            file_flags = os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
            file_flags |= getattr(os, "O_NONBLOCK", 0)
            probe_fd = os.open(parts[-1], file_flags, dir_fd=current_fd)
            current = os.fstat(probe_fd)
            return stat.S_ISREG(current.st_mode) and _same_file_state(expected, current)
        except (OSError, NotImplementedError, ValueError):
            return False
        finally:
            if probe_fd >= 0:
                os.close(probe_fd)
            if current_fd >= 0:
                os.close(current_fd)


def validate_decoupling_compliance(
    service: CompliancePreflightService | None, request: Any
) -> dict[str, Any]:
    """Tool callback. Missing service never probes a candidate or current directory."""
    if hasattr(request, "model_dump"):
        request = request.model_dump(mode="python")
    if not isinstance(request, Mapping):
        raise ValueError("compliance_request_invalid")
    policy_scope = request.get("policy_scope")
    candidates = validate_candidate_list(request.get("candidates"))
    if service is not None:
        return service.validate({"policy_scope": policy_scope, "candidates": candidates})
    return _unavailable_result(policy_scope, candidates)


def _unavailable_result(policy_scope: str, candidates: list[dict[str, Any]]) -> dict[str, Any]:
    baseline_checks = [
        _check(
            "candidate_baseline",
            "unknown",
            item["path"],
            "trusted compliance reader is unavailable; no candidate path was probed",
            reason_code="compliance_backend_unavailable",
            evidence_missing=["trusted operator-configured root reader and current disk baseline"],
        )
        for item in candidates
    ]
    return evaluate_candidate_checks(
        policy_scope,
        candidates,
        baseline_checks,
        lambda _path: None,
        allowed_scope=True,
    )


def _check(
    rule: str,
    status: str,
    path: str | None,
    message: str,
    *,
    reason_code: str | None = None,
    evidence_missing: Sequence[str] | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "rule_id": rule,
        "status": status,
        "path": path,
        "line": None,
        "message": message[:512],
        "evidence_missing": [item[:512] for item in (evidence_missing or [])[:8]],
    }
    if reason_code is not None:
        result["reason_code"] = reason_code
    return result


def _same_file_state(left: os.stat_result, right: os.stat_result) -> bool:
    return (
        left.st_dev == right.st_dev
        and left.st_ino == right.st_ino
        and left.st_mode == right.st_mode
        and left.st_size == right.st_size
        and left.st_mtime_ns == right.st_mtime_ns
        and left.st_ctime_ns == right.st_ctime_ns
    )

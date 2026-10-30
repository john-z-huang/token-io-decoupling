from __future__ import annotations

import contextlib
import hashlib
import importlib
import json
import os
import re
import stat
import subprocess
import tempfile
from collections.abc import Generator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Protocol

try:
    import fcntl
except ImportError:  # pragma: no cover - exercised on non-POSIX hosts
    fcntl = None  # type: ignore[assignment]


MAX_PLAN_BYTES = 1_000_000
MAX_RECORDS_PER_OPERATION = 100
MAX_EVENTS = 10_000
_PLAN_ID = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$")
_RECORD_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,95}$")
_REQUEST_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_REVISION = re.compile(r"^[a-f0-9]{64}$")
_REPOSITORY_ID = re.compile(r"^git-v1-[a-f0-9]{64}$")
_HEADER_PREFIX = b"~~~json task-plan-header-v1\n"
_HEADER_V2_PREFIX = b"~~~json task-plan-header-v2\n"
_HEADER_SUFFIX = b"\n~~~\n"
_EVENT_PREFIX = b"~~~json task-plan-event-v1\n"
_EVENT_V2_PREFIX = b"~~~json task-plan-event-v2\n"
_EVENT_SUFFIX = b"\n~~~\n"
_KINDS = {
    "goal",
    "criterion",
    "verification",
    "blocker",
    "resolution",
    "result",
    "limitation",
    "constraint",
    "requirement",
    "fact",
    "decision",
    "progress",
}
_OUTCOMES = {"passed", "failed", "assumed", "unavailable"}
_GLOBAL_MEMORY_PREFIX = "global/token-io-decoupling/repos"
_GIT_IDENTITY_DOMAIN = b"token-io-decoupling:git-common-dir:v1\0"
_GIT_IDENTITY_TIMEOUT_SECONDS = 3
_GIT_IDENTITY_MAX_OUTPUT_BYTES = 8192
_GIT_REDIRECT_ENVIRONMENT = ("GIT_DIR", "GIT_COMMON_DIR", "GIT_WORK_TREE")


class TaskPlanFailure(Exception):
    def __init__(self, reason: str, status: str = "blocked") -> None:
        super().__init__(reason)
        self.reason = reason
        self.status = status


class PlanStore(Protocol):
    project_root: str

    @contextlib.contextmanager
    def locked(self, plan_id: str) -> Generator[None, None, None]: ...

    def read(self, plan_id: str, *, archived: bool = False) -> bytes | None: ...

    def write(
        self, plan_id: str, expected: bytes | None, content: bytes
    ) -> tuple[str, bytes | None]: ...

    def archive(self, plan_id: str, expected: bytes) -> tuple[str, bytes | None]: ...


@dataclass(frozen=True)
class _Snapshot:
    raw: bytes
    legacy: bytes
    events: tuple[dict[str, Any], ...]
    records: dict[str, dict[str, Any]]
    active_ids: frozenset[str]
    resolved_blockers: frozenset[str]
    completed: bool

    @property
    def revision(self) -> str:
        return _sha(self.raw)

    @property
    def unresolved_blockers(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                record_id
                for record_id, record in self.records.items()
                if record["kind"] == "blocker" and record_id not in self.resolved_blockers
            )
        )


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _repository_id_for_checkout(project_root: str | Path) -> str:
    """Derive a local repository identity from a verified Git common directory."""
    checkout_path = Path(project_root)
    if not checkout_path.is_absolute():
        raise TaskPlanFailure("project_root_must_be_absolute", "unavailable")
    try:
        checkout_root = checkout_path.resolve(strict=True)
    except OSError as exc:
        raise TaskPlanFailure("project_root_unavailable", "unavailable") from exc
    if not checkout_root.is_dir():
        raise TaskPlanFailure("project_root_unavailable", "unavailable")

    if any(os.environ.get(name) for name in _GIT_REDIRECT_ENVIRONMENT):
        raise TaskPlanFailure("git_environment_redirected", "unavailable")

    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(checkout_root),
                "rev-parse",
                "--path-format=absolute",
                "--show-toplevel",
                "--git-common-dir",
            ],
            check=False,
            capture_output=True,
            timeout=_GIT_IDENTITY_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise TaskPlanFailure("git_identity_timeout", "unavailable") from exc
    except OSError as exc:
        raise TaskPlanFailure("git_identity_unavailable", "unavailable") from exc
    if (
        result.returncode != 0
        or len(result.stdout) > _GIT_IDENTITY_MAX_OUTPUT_BYTES
        or len(result.stderr) > _GIT_IDENTITY_MAX_OUTPUT_BYTES
    ):
        raise TaskPlanFailure("git_identity_unavailable", "unavailable")

    try:
        output_lines = result.stdout.decode(errors="surrogateescape").splitlines()
        if len(output_lines) != 2:
            raise TaskPlanFailure("git_identity_output_invalid", "unavailable")
        reported_root = Path(output_lines[0])
        common_dir = Path(output_lines[1])
        if not reported_root.is_absolute() or not common_dir.is_absolute():
            raise TaskPlanFailure("git_identity_output_invalid", "unavailable")
        canonical_reported_root = reported_root.resolve(strict=True)
        canonical_common_dir = common_dir.resolve(strict=True)
        if canonical_reported_root != checkout_root or not canonical_common_dir.is_dir():
            raise TaskPlanFailure("git_identity_output_invalid", "unavailable")
    except TaskPlanFailure:
        raise
    except (OSError, ValueError) as exc:
        raise TaskPlanFailure("git_identity_output_invalid", "unavailable") from exc

    digest = hashlib.sha256(
        _GIT_IDENTITY_DOMAIN + os.fsencode(str(canonical_common_dir))
    ).hexdigest()
    return f"git-v1-{digest}"


def _history_identity(project_root: str, repository_id: str | None) -> tuple[int, str, str]:
    if repository_id is None:
        return 1, "project_root", project_root
    if not _REPOSITORY_ID.fullmatch(repository_id):
        raise TaskPlanFailure("repository_identity_invalid", "unavailable")
    return 2, "repository_id", repository_id


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_json_key")
        result[key] = value
    return result


def _json_object(encoded: bytes) -> dict[str, Any]:
    try:
        value = json.loads(encoded, object_pairs_hook=_unique_object)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise TaskPlanFailure("history_invalid", "blocked") from exc
    if not isinstance(value, dict):
        raise TaskPlanFailure("history_invalid", "blocked")
    if _canonical_json(value) != encoded:
        raise TaskPlanFailure("history_noncanonical", "blocked")
    return value


def _validate_plan_id(value: Any) -> str:
    if not isinstance(value, str) or not _PLAN_ID.fullmatch(value):
        raise TaskPlanFailure("invalid_plan_id")
    return value


def _validate_id(value: Any, pattern: re.Pattern[str], reason: str) -> str:
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise TaskPlanFailure(reason)
    return value


def _validate_revision(value: Any, *, allow_absent: bool = False) -> str | None:
    if allow_absent and value is None:
        return None
    if not isinstance(value, str) or not _REVISION.fullmatch(value):
        raise TaskPlanFailure("invalid_expected_revision")
    return value


def _validate_text(value: Any, maximum: int, reason: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise TaskPlanFailure(reason)
    return value


def _validate_record(record: Any) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise TaskPlanFailure("invalid_record")
    allowed = {
        "record_id",
        "kind",
        "text",
        "sources",
        "outcome",
        "resolves_blocker_id",
        "supersedes_id",
        "supersedes_reason",
    }
    if set(record) != allowed:
        raise TaskPlanFailure("invalid_record_fields")
    record_id = _validate_id(record["record_id"], _RECORD_ID, "invalid_record_id")
    kind = record["kind"]
    if not isinstance(kind, str) or kind not in _KINDS:
        raise TaskPlanFailure("invalid_record_kind")
    text = _validate_text(record["text"], 4000, "invalid_record_text")
    sources = record["sources"]
    if (
        not isinstance(sources, list)
        or not 1 <= len(sources) <= 8
        or any(
            not isinstance(source, str) or not source.strip() or len(source) > 512
            for source in sources
        )
    ):
        raise TaskPlanFailure("invalid_record_sources")
    outcome = record["outcome"]
    if kind == "verification":
        if not isinstance(outcome, str) or outcome not in _OUTCOMES:
            raise TaskPlanFailure("verification_outcome_required")
    elif outcome is not None:
        raise TaskPlanFailure("outcome_only_for_verification")
    resolves = record["resolves_blocker_id"]
    if kind == "resolution":
        _validate_id(resolves, _RECORD_ID, "resolution_blocker_required")
    elif resolves is not None:
        raise TaskPlanFailure("blocker_reference_only_for_resolution")
    supersedes = record["supersedes_id"]
    reason = record["supersedes_reason"]
    if supersedes is None:
        if reason is not None:
            raise TaskPlanFailure("supersedes_reason_without_target")
    else:
        _validate_id(supersedes, _RECORD_ID, "invalid_supersedes_id")
        _validate_text(reason, 1000, "supersedes_reason_required")
    return {
        "record_id": record_id,
        "kind": kind,
        "text": text,
        "sources": list(sources),
        "outcome": outcome,
        "resolves_blocker_id": resolves,
        "supersedes_id": supersedes,
        "supersedes_reason": reason,
    }


def _apply_records(
    records: dict[str, dict[str, Any]],
    active_ids: set[str],
    resolved_blockers: set[str],
    additions: list[dict[str, Any]],
    *,
    completion: bool,
) -> None:
    if not isinstance(additions, list) or not 1 <= len(additions) <= MAX_RECORDS_PER_OPERATION:
        raise TaskPlanFailure("invalid_record_count")
    seen: set[str] = set()
    for raw_record in additions:
        record = _validate_record(raw_record)
        record_id = record["record_id"]
        if record_id in seen or record_id in records:
            raise TaskPlanFailure("record_id_conflict")
        seen.add(record_id)
        if completion and record["kind"] not in {"result", "limitation"}:
            raise TaskPlanFailure("completion_record_kind_invalid")
        if not completion and record["kind"] in {"result", "limitation"}:
            raise TaskPlanFailure("result_requires_completion")
        supersedes = record["supersedes_id"]
        if supersedes is not None:
            old = records.get(supersedes)
            if old is None or supersedes not in active_ids:
                raise TaskPlanFailure("superseded_record_not_active")
            if old["kind"] != record["kind"]:
                raise TaskPlanFailure("superseded_record_kind_mismatch")
            active_ids.remove(supersedes)
        blocker_id = record["resolves_blocker_id"]
        if blocker_id is not None:
            blocker = records.get(blocker_id)
            if blocker is None or blocker["kind"] != "blocker":
                raise TaskPlanFailure("resolution_blocker_not_found")
            if blocker_id in resolved_blockers:
                raise TaskPlanFailure("blocker_already_resolved")
            resolved_blockers.add(blocker_id)
        records[record_id] = record
        active_ids.add(record_id)


def _validate_evidence(
    records: dict[str, dict[str, Any]],
    active_ids: set[str],
    unresolved: tuple[str, ...],
    evidence: Any,
) -> list[dict[str, str]]:
    if unresolved:
        raise TaskPlanFailure("unresolved_blockers")
    criteria = {record_id for record_id in active_ids if records[record_id]["kind"] == "criterion"}
    if not criteria:
        raise TaskPlanFailure("active_criterion_required")
    verifications = {
        record_id: record
        for record_id, record in records.items()
        if record_id in active_ids and record["kind"] == "verification"
    }
    if not isinstance(evidence, list) or not 1 <= len(evidence) <= MAX_RECORDS_PER_OPERATION:
        raise TaskPlanFailure("criterion_evidence_required")
    normalized: list[dict[str, str]] = []
    mapped: set[str] = set()
    for entry in evidence:
        if not isinstance(entry, dict) or set(entry) != {"criterion_id", "verification_id"}:
            raise TaskPlanFailure("invalid_criterion_evidence")
        criterion_id = _validate_id(entry["criterion_id"], _RECORD_ID, "invalid_criterion_id")
        verification_id = _validate_id(
            entry["verification_id"], _RECORD_ID, "invalid_verification_id"
        )
        if criterion_id in mapped:
            raise TaskPlanFailure("duplicate_criterion_mapping")
        if criterion_id not in criteria:
            raise TaskPlanFailure("criterion_not_active")
        verification = verifications.get(verification_id)
        if verification is None:
            raise TaskPlanFailure("verification_not_active")
        if verification["outcome"] != "passed":
            raise TaskPlanFailure("verification_not_passed")
        mapped.add(criterion_id)
        normalized.append({"criterion_id": criterion_id, "verification_id": verification_id})
    if mapped != criteria:
        raise TaskPlanFailure("criterion_evidence_incomplete")
    return normalized


def _parse_snapshot(
    raw: bytes,
    plan_id: str,
    project_root: str | None = None,
    *,
    repository_id: str | None = None,
) -> _Snapshot:
    if len(raw) > MAX_PLAN_BYTES:
        raise TaskPlanFailure("plan_too_large")
    v1_marker_count = raw.count(_HEADER_PREFIX)
    v2_marker_count = raw.count(_HEADER_V2_PREFIX)
    marker_count = v1_marker_count + v2_marker_count
    if marker_count == 0:
        return _Snapshot(raw, raw, (), {}, frozenset(), frozenset(), False)
    if marker_count != 1:
        raise TaskPlanFailure("history_invalid")
    if v1_marker_count:
        version = 1
        header_prefix = _HEADER_PREFIX
        event_prefix = _EVENT_PREFIX
    else:
        version = 2
        header_prefix = _HEADER_V2_PREFIX
        event_prefix = _EVENT_V2_PREFIX
    marker = raw.index(header_prefix)
    if marker and raw[marker - 1] not in b"\r\n":
        raise TaskPlanFailure("history_invalid")
    line_end = raw.find(_HEADER_SUFFIX, marker + len(header_prefix))
    if line_end < 0:
        raise TaskPlanFailure("history_invalid")
    header_end = line_end + len(_HEADER_SUFFIX)
    header = _json_object(raw[marker + len(header_prefix) : line_end])
    if version == 1:
        expected_header_keys = {
            "version",
            "plan_id",
            "project_root",
            "legacy_length",
            "legacy_revision",
        }
        identity_key = "project_root"
        expected_identity = project_root
    elif version == 2:
        expected_header_keys = {
            "version",
            "plan_id",
            "repository_id",
            "legacy_length",
            "legacy_revision",
        }
        identity_key = "repository_id"
        expected_identity = repository_id
    else:
        raise TaskPlanFailure("history_invalid")
    if set(header) != expected_header_keys or header["version"] != version:
        raise TaskPlanFailure("history_invalid")
    if (
        header["plan_id"] != plan_id
        or not isinstance(header[identity_key], str)
        or (expected_identity is not None and header[identity_key] != expected_identity)
        or (version == 1 and repository_id is not None)
        or (version == 2 and project_root is not None)
    ):
        raise TaskPlanFailure("history_identity_mismatch")
    if version == 2 and not _REPOSITORY_ID.fullmatch(header["repository_id"]):
        raise TaskPlanFailure("history_identity_mismatch")
    legacy_length = header["legacy_length"]
    if not isinstance(legacy_length, int) or legacy_length < 0 or legacy_length > marker:
        raise TaskPlanFailure("history_invalid")
    legacy = raw[:legacy_length]
    separator = raw[legacy_length:marker]
    expected_separator = b"" if not legacy or legacy.endswith((b"\n", b"\r")) else b"\n"
    if separator != expected_separator or header["legacy_revision"] != _sha(legacy):
        raise TaskPlanFailure("history_legacy_prefix_mismatch")
    if marker != legacy_length + len(separator):
        raise TaskPlanFailure("history_invalid")
    if header_end > len(raw):
        raise TaskPlanFailure("history_invalid")
    events: list[dict[str, Any]] = []
    records: dict[str, dict[str, Any]] = {}
    active_ids: set[str] = set()
    resolved_blockers: set[str] = set()
    operation_ids: dict[str, str] = {}
    completed = False
    position = header_end
    while position < len(raw):
        if not raw.startswith(event_prefix, position):
            raise TaskPlanFailure("history_invalid")
        if position and raw[position - 1] not in b"\r\n":
            raise TaskPlanFailure("history_invalid")
        event_start = position + len(event_prefix)
        event_end = raw.find(_EVENT_SUFFIX, event_start)
        if event_end < 0:
            raise TaskPlanFailure("history_invalid")
        event = _json_object(raw[event_start:event_end])
        expected_event_keys = {
            "version",
            "plan_id",
            identity_key,
            "operation_id",
            "operation",
            "request_hash",
            "previous_revision",
            "data",
        }
        if set(event) != expected_event_keys or event["version"] != version:
            raise TaskPlanFailure("history_invalid")
        if (
            event["plan_id"] != plan_id
            or event[identity_key] != header[identity_key]
            or (expected_identity is not None and event[identity_key] != expected_identity)
            or event["operation"] not in {"update", "complete"}
        ):
            raise TaskPlanFailure("history_identity_mismatch")
        if version == 2 and not _REPOSITORY_ID.fullmatch(event["repository_id"]):
            raise TaskPlanFailure("history_identity_mismatch")
        op_id = _validate_id(event["operation_id"], _REQUEST_ID, "history_invalid")
        if not isinstance(event["data"], dict):
            raise TaskPlanFailure("history_invalid")
        request_hash = _request_hash(
            plan_id,
            event["project_root"] if version == 1 else "",
            event["operation"],
            event["data"],
            repository_id=event["repository_id"] if version == 2 else None,
        )
        if event["request_hash"] != request_hash:
            raise TaskPlanFailure("history_request_hash_mismatch")
        previous = _sha(legacy) if not events else _sha(raw[:position])
        if event["previous_revision"] != previous:
            raise TaskPlanFailure("history_chain_mismatch")
        if op_id in operation_ids:
            raise TaskPlanFailure("history_duplicate_operation_id")
        operation_ids[op_id] = request_hash
        data = event["data"]
        if set(data) != (
            {"records"} if event["operation"] == "update" else {"records", "criterion_evidence"}
        ):
            raise TaskPlanFailure("history_invalid")
        additions = data["records"]
        if completed:
            raise TaskPlanFailure("history_after_completion")
        normalized = (
            [_validate_record(record) for record in additions]
            if isinstance(additions, list)
            else []
        )
        if normalized != additions:
            raise TaskPlanFailure("history_record_invalid")
        _apply_records(
            records,
            active_ids,
            resolved_blockers,
            normalized,
            completion=event["operation"] == "complete",
        )
        if event["operation"] == "complete":
            if not any(record["kind"] == "result" for record in normalized):
                raise TaskPlanFailure("completion_result_required")
            unresolved = tuple(
                sorted(
                    record_id
                    for record_id, record in records.items()
                    if record["kind"] == "blocker" and record_id not in resolved_blockers
                )
            )
            evidence = _validate_evidence(
                records, active_ids, unresolved, data["criterion_evidence"]
            )
            if evidence != data["criterion_evidence"]:
                raise TaskPlanFailure("history_invalid")
            completed = True
        events.append(event)
        if len(events) > MAX_EVENTS:
            raise TaskPlanFailure("history_too_large")
        position = event_end + len(_EVENT_SUFFIX)
    return _Snapshot(
        raw,
        legacy,
        tuple(events),
        records,
        frozenset(active_ids),
        frozenset(resolved_blockers),
        completed,
    )


def _request_hash(
    plan_id: str,
    project_root: str,
    operation: str,
    data: dict[str, Any],
    *,
    repository_id: str | None = None,
) -> str:
    _, identity_key, identity_value = _history_identity(project_root, repository_id)
    return _sha(
        _canonical_json(
            {
                "plan_id": plan_id,
                identity_key: identity_value,
                "operation": operation,
                "data": data,
            }
        )
    )


def _event_line(event: dict[str, Any]) -> bytes:
    version = event.get("version")
    if version == 1:
        event_prefix = _EVENT_PREFIX
    elif version == 2:
        event_prefix = _EVENT_V2_PREFIX
    else:
        raise TaskPlanFailure("history_invalid")
    return event_prefix + _canonical_json(event) + _EVENT_SUFFIX


def _append_event(
    raw: bytes | None,
    plan_id: str,
    project_root: str,
    operation_id: str,
    operation: str,
    request_hash: str,
    data: dict[str, Any],
    *,
    repository_id: str | None = None,
) -> bytes:
    version, identity_key, identity_value = _history_identity(project_root, repository_id)
    header_prefix = _HEADER_PREFIX if version == 1 else _HEADER_V2_PREFIX
    if raw is None:
        legacy = b""
        separator = b""
        header = {
            "version": version,
            "plan_id": plan_id,
            identity_key: identity_value,
            "legacy_length": 0,
            "legacy_revision": _sha(legacy),
        }
        prefix = separator + header_prefix + _canonical_json(header) + _HEADER_SUFFIX
        previous = _sha(legacy)
    else:
        snapshot = _parse_snapshot(
            raw,
            plan_id,
            project_root if repository_id is None else None,
            repository_id=repository_id,
        )
        if snapshot.events:
            prefix = b""
        else:
            separator = b"" if not raw or raw.endswith((b"\n", b"\r")) else b"\n"
            header = {
                "version": version,
                "plan_id": plan_id,
                identity_key: identity_value,
                "legacy_length": len(raw),
                "legacy_revision": _sha(raw),
            }
            prefix = separator + header_prefix + _canonical_json(header) + _HEADER_SUFFIX
        previous = _sha(raw)
    event = {
        "version": version,
        "plan_id": plan_id,
        identity_key: identity_value,
        "operation_id": operation_id,
        "operation": operation,
        "request_hash": request_hash,
        "previous_revision": previous,
        "data": data,
    }
    result = (raw or b"") + prefix + _event_line(event)
    if len(result) > MAX_PLAN_BYTES:
        raise TaskPlanFailure("plan_too_large")
    return result


def _current_state(snapshot: _Snapshot | None) -> str:
    if snapshot is None:
        return "absent"
    if snapshot.completed:
        return "completed"
    return "in_progress" if snapshot.events else "legacy"


def _observed_state(
    raw: bytes | None,
    plan_id: str | None,
    project_root: str | None,
    *,
    repository_id: str | None = None,
) -> str:
    if plan_id is None or (project_root is None and repository_id is None):
        return "unknown"
    if raw is None:
        return "absent"
    try:
        return _current_state(
            _parse_snapshot(
                raw,
                plan_id,
                project_root if repository_id is None else None,
                repository_id=repository_id,
            )
        )
    except TaskPlanFailure:
        return "unknown"


def _receipt(
    *,
    status: str,
    reason: str,
    plan_id: str | None,
    state: str,
    before_revision: str | None,
    current_revision: str | None,
    changed_ids: list[str] | None = None,
    preservation: bool | None = None,
    readback: str = "not_applicable",
    replayed: bool = False,
    reconciliation: str = "not_required",
    project_root: str | None = None,
    memory_name: str | None = None,
    storage_scope: str | None = None,
    repository_id: str | None = None,
) -> dict[str, Any]:
    return {
        "status": status,
        "reason": reason,
        "plan_id": plan_id,
        "project_root": project_root,
        "memory_name": memory_name,
        "storage_scope": storage_scope,
        "repository_id": repository_id,
        "plan_state": state,
        "before_revision": before_revision,
        "current_revision": current_revision,
        "changed_record_ids": changed_ids or [],
        "changed_count": len(changed_ids or []),
        "legacy_prefix_preserved": preservation,
        "readback": readback,
        "replayed": replayed,
        "reconciliation_status": reconciliation,
    }


class SerenaMemoryStore:
    """Byte-preserving adapter over an actual Serena MemoryManager instance."""

    def __init__(
        self,
        memory_manager: object,
        project_root: str | Path,
        *,
        storage_scope: Literal["project", "global"] = "project",
    ) -> None:
        if storage_scope not in {"project", "global"}:
            raise TaskPlanFailure("storage_scope_invalid", "unavailable")
        try:
            memory_manager_module = importlib.import_module("serena.memories.memory_manager")
        except ImportError as exc:
            raise TaskPlanFailure("serena_unavailable", "unavailable") from exc
        manager_type = getattr(memory_manager_module, "MemoryManager", None)
        if not isinstance(manager_type, type):
            raise TaskPlanFailure("serena_manager_interface_unsupported", "unavailable")
        if not isinstance(memory_manager, manager_type):
            raise TaskPlanFailure("serena_manager_required", "unavailable")
        for name in (
            "get_memory_file_path",
            "_check_not_ignored",
            "_check_write_access",
        ):
            if not callable(getattr(memory_manager, name, None)):
                raise TaskPlanFailure("serena_manager_interface_unsupported", "unavailable")

        project_path = Path(project_root)
        if not project_path.is_absolute():
            raise TaskPlanFailure("project_root_must_be_absolute", "unavailable")
        try:
            self.project_root = str(project_path.resolve(strict=True))
            if not Path(self.project_root).is_dir():
                raise TaskPlanFailure("project_root_unavailable", "unavailable")
        except TaskPlanFailure:
            raise
        except OSError as exc:
            raise TaskPlanFailure("project_root_unavailable", "unavailable") from exc

        root_attribute = (
            "_project_memory_dir" if storage_scope == "project" else "_global_memory_dir"
        )
        unavailable_reason = (
            "serena_project_memory_unavailable"
            if storage_scope == "project"
            else "serena_global_memory_unavailable"
        )
        invalid_reason = (
            "serena_project_memory_invalid"
            if storage_scope == "project"
            else "serena_global_memory_invalid"
        )
        root_value = getattr(memory_manager, root_attribute, None)
        if not isinstance(root_value, (str, Path)):
            raise TaskPlanFailure(unavailable_reason, "unavailable")
        root_path = Path(root_value)
        try:
            root_stat = root_path.lstat()
            if (
                not root_path.is_absolute()
                or stat.S_ISLNK(root_stat.st_mode)
                or not stat.S_ISDIR(root_stat.st_mode)
            ):
                raise TaskPlanFailure(invalid_reason, "unavailable")
            self.memory_root = root_path.resolve(strict=True)
        except TaskPlanFailure:
            raise
        except OSError as exc:
            raise TaskPlanFailure(unavailable_reason, "unavailable") from exc

        self.storage_scope = storage_scope
        self.repository_id = (
            _repository_id_for_checkout(self.project_root) if storage_scope == "global" else None
        )
        self._manager = memory_manager

    def capability(self) -> dict[str, Any]:
        metadata = {
            "status": "configured",
            "reason_code": "explicit_serena_manager_injected",
            "project_root": self.project_root,
            "storage_scope": getattr(self, "storage_scope", "project"),
            "repository_id": getattr(self, "repository_id", None),
            "namespace": self._namespace_pattern(False),
            "archive_namespace": self._namespace_pattern(True),
        }
        try:
            self._assert_current_binding()
        except TaskPlanFailure as exc:
            metadata["status"] = "unavailable"
            metadata["reason_code"] = exc.reason
        return metadata

    def _memory_name(self, plan_id: str, archived: bool) -> str:
        namespace = "archive-plans" if archived else "plans"
        plan_name = f"{namespace}/PLAN-{plan_id}"
        if getattr(self, "storage_scope", "project") == "global":
            repository_id = getattr(self, "repository_id", None)
            if not isinstance(repository_id, str) or not _REPOSITORY_ID.fullmatch(repository_id):
                raise TaskPlanFailure("repository_identity_invalid", "unavailable")
            return f"{_GLOBAL_MEMORY_PREFIX}/{repository_id}/{plan_name}"
        return plan_name

    def _fixed_path(self, plan_id: str, archived: bool) -> Path:
        namespace = "archive-plans" if archived else "plans"
        if getattr(self, "storage_scope", "project") == "global":
            repository_id = getattr(self, "repository_id", None)
            if not isinstance(repository_id, str) or not _REPOSITORY_ID.fullmatch(repository_id):
                raise TaskPlanFailure("repository_identity_invalid", "unavailable")
            return (
                self.memory_root
                / "token-io-decoupling"
                / "repos"
                / repository_id
                / namespace
                / f"PLAN-{plan_id}.md"
            )
        return self.memory_root / namespace / f"PLAN-{plan_id}.md"

    def _namespace_pattern(self, archived: bool) -> str:
        namespace = "archive-plans" if archived else "plans"
        if getattr(self, "storage_scope", "project") == "global":
            repository_id = getattr(self, "repository_id", None)
            if not isinstance(repository_id, str) or not _REPOSITORY_ID.fullmatch(repository_id):
                return f"{_GLOBAL_MEMORY_PREFIX}/<unavailable>/{namespace}/PLAN-<plan_id>"
            return f"{_GLOBAL_MEMORY_PREFIX}/{repository_id}/{namespace}/PLAN-<plan_id>"
        return f"{namespace}/PLAN-<plan_id>"

    def _assert_current_binding(self) -> None:
        if getattr(self, "storage_scope", "project") != "global":
            return
        manager_root = getattr(self._manager, "_global_memory_dir", None)
        if not isinstance(manager_root, (str, Path)):
            raise TaskPlanFailure("serena_global_memory_unavailable", "unavailable")
        root_path = Path(manager_root)
        try:
            root_stat = root_path.lstat()
            if (
                not root_path.is_absolute()
                or stat.S_ISLNK(root_stat.st_mode)
                or not stat.S_ISDIR(root_stat.st_mode)
            ):
                raise TaskPlanFailure("serena_global_memory_invalid", "unavailable")
            current_root = root_path.resolve(strict=True)
        except TaskPlanFailure:
            raise
        except OSError as exc:
            raise TaskPlanFailure("serena_global_memory_unavailable", "unavailable") from exc
        if current_root != self.memory_root:
            raise TaskPlanFailure("serena_global_memory_mismatch", "unavailable")
        current_repository_id = _repository_id_for_checkout(self.project_root)
        if current_repository_id != self.repository_id:
            raise TaskPlanFailure("repository_identity_changed", "unavailable")

    def _policy(self, memory_name: str, *, write: bool) -> None:
        try:
            self._manager._check_not_ignored(memory_name)
            if write:
                self._manager._check_write_access(memory_name, True)
        except PermissionError as exc:
            raise TaskPlanFailure("serena_memory_read_only") from exc
        except ValueError as exc:
            raise TaskPlanFailure("serena_memory_ignored_or_invalid") from exc

    def _check_namespace(self, path: Path) -> None:
        if self.memory_root.is_symlink():
            raise TaskPlanFailure("memory_root_symlink_rejected", "unavailable")
        try:
            if not path.is_absolute():
                raise TaskPlanFailure("serena_memory_path_mismatch", "unavailable")
            if path.is_relative_to(self.memory_root):
                checked_root = self.memory_root
            else:
                root_attribute = (
                    "_project_memory_dir"
                    if getattr(self, "storage_scope", "project") == "project"
                    else "_global_memory_dir"
                )
                manager_root = getattr(self._manager, root_attribute, None)
                if not isinstance(manager_root, (str, Path)):
                    raise TaskPlanFailure("serena_memory_path_mismatch", "unavailable")
                checked_root = Path(manager_root)
                if not checked_root.is_absolute() or not path.is_relative_to(checked_root):
                    raise TaskPlanFailure("serena_memory_path_mismatch", "unavailable")
                try:
                    if checked_root.resolve(strict=True) != self.memory_root:
                        raise TaskPlanFailure("serena_memory_path_mismatch", "unavailable")
                except OSError as exc:
                    raise TaskPlanFailure("serena_memory_path_unavailable", "unavailable") from exc
            relative_parts = path.relative_to(checked_root).parts
            current = checked_root
            for index, part in enumerate(relative_parts):
                current = current / part
                try:
                    mode = current.lstat().st_mode
                except FileNotFoundError:
                    break
                if stat.S_ISLNK(mode):
                    if index == len(relative_parts) - 1:
                        raise TaskPlanFailure("memory_file_symlink_rejected", "unavailable")
                    raise TaskPlanFailure("memory_namespace_symlink_rejected", "unavailable")
                if index < len(relative_parts) - 1 and not stat.S_ISDIR(mode):
                    raise TaskPlanFailure("memory_namespace_invalid", "unavailable")
                if index == len(relative_parts) - 1 and not stat.S_ISREG(mode):
                    raise TaskPlanFailure("memory_file_invalid", "unavailable")
            if not path.resolve(strict=False).is_relative_to(self.memory_root):
                raise TaskPlanFailure("serena_memory_path_mismatch", "unavailable")
        except TaskPlanFailure:
            raise
        except OSError as exc:
            raise TaskPlanFailure("memory_path_unavailable", "unavailable") from exc

    def _canonical_path(
        self,
        plan_id: str,
        archived: bool,
        *,
        create_parent: bool,
        write: bool = True,
    ) -> Path:
        self._assert_current_binding()
        memory_name = self._memory_name(plan_id, archived)
        self._policy(memory_name, write=write)
        expected = self._fixed_path(plan_id, archived)
        self._check_namespace(expected)
        namespace = expected.parent
        if not namespace.exists() and not create_parent:
            return expected
        try:
            actual = Path(self._manager.get_memory_file_path(memory_name))
        except (OSError, ValueError, PermissionError) as exc:
            raise TaskPlanFailure("serena_memory_path_unavailable", "unavailable") from exc
        self._check_namespace(actual)
        if not actual.is_absolute():
            raise TaskPlanFailure("serena_memory_path_mismatch", "unavailable")
        try:
            actual_parent = actual.parent.resolve(strict=True)
            resolved_actual = actual.resolve(strict=False)
        except OSError as exc:
            raise TaskPlanFailure("serena_memory_path_unavailable", "unavailable") from exc
        if (
            actual_parent != expected.parent
            or resolved_actual != expected
            or not resolved_actual.is_relative_to(self.memory_root)
        ):
            raise TaskPlanFailure("serena_memory_path_mismatch", "unavailable")
        self._check_namespace(expected)
        return expected

    @contextlib.contextmanager
    def locked(self, plan_id: str) -> Generator[None, None, None]:
        _validate_plan_id(plan_id)
        self._assert_current_binding()
        if fcntl is None:
            raise TaskPlanFailure("posix_file_lock_unavailable", "unavailable")
        self._check_namespace(self._fixed_path(plan_id, False))
        self._check_namespace(self._fixed_path(plan_id, True))
        lock_path = self.memory_root / ".token-io-task-plan.lock"
        self._check_namespace(lock_path)
        try:
            flags = os.O_CREAT | os.O_RDWR
            flags |= getattr(os, "O_NOFOLLOW", 0)
            descriptor = os.open(lock_path, flags, 0o600)
        except TaskPlanFailure:
            raise
        except OSError as exc:
            raise TaskPlanFailure("plan_lock_unavailable", "unavailable") from exc
        locked = False
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            locked = True
            self._assert_current_binding()
            yield
        except TaskPlanFailure:
            raise
        except OSError as exc:
            raise TaskPlanFailure("plan_lock_unavailable", "unavailable") from exc
        finally:
            try:
                if locked:
                    fcntl.flock(descriptor, fcntl.LOCK_UN)
            finally:
                os.close(descriptor)

    def _read_path(self, path: Path) -> bytes | None:
        try:
            mode = path.lstat().st_mode
        except FileNotFoundError:
            return None
        except OSError as exc:
            raise TaskPlanFailure("memory_read_failed", "unavailable") from exc
        if stat.S_ISLNK(mode):
            raise TaskPlanFailure("memory_file_symlink_rejected", "unavailable")
        if not stat.S_ISREG(mode):
            raise TaskPlanFailure("memory_file_invalid", "unavailable")
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        try:
            descriptor = os.open(path, flags)
            with os.fdopen(descriptor, "rb") as stream:
                raw = stream.read(MAX_PLAN_BYTES + 1)
        except OSError as exc:
            raise TaskPlanFailure("memory_read_failed", "unavailable") from exc
        if len(raw) > MAX_PLAN_BYTES:
            raise TaskPlanFailure("plan_too_large")
        return raw

    def read(self, plan_id: str, *, archived: bool = False) -> bytes | None:
        _validate_plan_id(plan_id)
        self._assert_current_binding()
        memory_name = self._memory_name(plan_id, archived)
        self._policy(memory_name, write=False)
        path = self._fixed_path(plan_id, archived)
        self._check_namespace(path)
        if not path.parent.exists():
            return None
        canonical = self._canonical_path(plan_id, archived, create_parent=False, write=False)
        return self._read_path(canonical)

    def write(
        self, plan_id: str, expected: bytes | None, content: bytes
    ) -> tuple[str, bytes | None]:
        if len(content) > MAX_PLAN_BYTES:
            return "plan_too_large", None
        path = self._canonical_path(plan_id, False, create_parent=True)
        effect_started = False
        try:
            current = self._read_path(path)
            if current != expected:
                return "conflict", current
            descriptor, temporary = tempfile.mkstemp(prefix=".task-plan-", dir=path.parent)
            temp_path = Path(temporary)
            try:
                with os.fdopen(descriptor, "wb") as stream:
                    stream.write(content)
                    stream.flush()
                    os.fsync(stream.fileno())
                self._check_namespace(path)
                latest = self._read_path(path)
                if latest != expected:
                    return "conflict", latest
                if expected is None:
                    try:
                        effect_started = True
                        os.link(temp_path, path, follow_symlinks=False)
                    except FileExistsError:
                        effect_started = False
                        return "conflict", self._read_path(path)
                    temp_path.unlink()
                else:
                    effect_started = True
                    os.replace(temp_path, path)
                dir_fd = os.open(path.parent, os.O_RDONLY)
                try:
                    os.fsync(dir_fd)
                finally:
                    os.close(dir_fd)
            finally:
                try:
                    temp_path.unlink()
                except FileNotFoundError:
                    pass
            actual = self._read_path(path)
            if actual == content:
                return "written", actual
            return "uncertain", actual
        except TaskPlanFailure:
            if not effect_started:
                raise
            try:
                actual = self._read_path(path)
            except TaskPlanFailure:
                actual = None
            return "uncertain", actual
        except OSError:
            try:
                actual = self._read_path(path)
            except TaskPlanFailure:
                actual = None
            if actual == content:
                return "uncertain", actual
            if actual == expected:
                return "unavailable", actual
            return "uncertain", actual

    def archive(self, plan_id: str, expected: bytes) -> tuple[str, bytes | None]:
        self._assert_current_binding()
        source_name = self._memory_name(plan_id, False)
        target_name = self._memory_name(plan_id, True)
        self._policy(source_name, write=True)
        self._policy(target_name, write=True)
        source = self._canonical_path(plan_id, False, create_parent=False)
        target = self._canonical_path(plan_id, True, create_parent=True)
        effect_started = False
        try:
            source_before = self._read_path(source)
            if source_before != expected:
                return "conflict", source_before
            if self._read_path(target) is not None:
                return "collision", source_before
            source_stat = source.lstat()
            if not stat.S_ISREG(source_stat.st_mode):
                return "unavailable", source_before
            self._check_namespace(source)
            self._check_namespace(target)
            effect_started = True
            os.link(source, target, follow_symlinks=False)
            linked_source = source.lstat()
            linked_target = target.lstat()
            if (linked_source.st_dev, linked_source.st_ino) != (
                source_stat.st_dev,
                source_stat.st_ino,
            ) or (linked_target.st_dev, linked_target.st_ino) != (
                source_stat.st_dev,
                source_stat.st_ino,
            ):
                return "uncertain", self._read_path(target)
            if self._read_path(target) != expected or self._read_path(source) != expected:
                return "uncertain", self._read_path(target)
            os.unlink(source)
            for directory in {source.parent, target.parent}:
                dir_fd = os.open(directory, os.O_RDONLY)
                try:
                    os.fsync(dir_fd)
                finally:
                    os.close(dir_fd)
            actual = self._read_path(target)
            if actual == expected and self._read_path(source) is None:
                return "archived", actual
            return "uncertain", actual
        except FileExistsError:
            effect_started = False
            return "collision", self._read_path(source)
        except TaskPlanFailure:
            if not effect_started:
                raise
            try:
                target_bytes = self._read_path(target)
            except TaskPlanFailure:
                target_bytes = None
            return "uncertain", target_bytes
        except (OSError, TypeError, NotImplementedError):
            try:
                target_bytes = self._read_path(target)
                source_bytes = self._read_path(source)
            except TaskPlanFailure:
                target_bytes = None
                source_bytes = None
            if source_bytes != expected and target_bytes is None:
                return "conflict", source_bytes
            if source_bytes == expected and target_bytes is None:
                return "unavailable", source_bytes
            return "uncertain", target_bytes


def _request_data(
    request: dict[str, Any], operation: str
) -> tuple[str, str, str, str | None, dict[str, Any]]:
    if not isinstance(request, dict):
        raise TaskPlanFailure("invalid_request")
    project_root = request.get("project_root")
    if (
        not isinstance(project_root, str)
        or not Path(project_root).is_absolute()
        or len(project_root) > 4096
    ):
        raise TaskPlanFailure("invalid_project_root")
    plan_id = _validate_plan_id(request.get("plan_id"))
    operation_id = _validate_id(request.get("request_id"), _REQUEST_ID, "invalid_request_id")
    expected = _validate_revision(
        request.get("expected_revision"), allow_absent=operation == "update"
    )
    if operation == "update":
        if set(request) != {
            "project_root",
            "plan_id",
            "request_id",
            "expected_revision",
            "records",
        }:
            raise TaskPlanFailure("invalid_request_fields")
        raw_records = request["records"]
        if not isinstance(raw_records, list):
            raise TaskPlanFailure("invalid_record_count")
        records = [_validate_record(record) for record in raw_records]
        data = {"records": records}
    else:
        if set(request) != {
            "project_root",
            "plan_id",
            "request_id",
            "expected_revision",
            "criterion_evidence",
            "records",
        }:
            raise TaskPlanFailure("invalid_request_fields")
        raw_records = request["records"]
        if not isinstance(raw_records, list):
            raise TaskPlanFailure("invalid_record_count")
        records = [_validate_record(record) for record in raw_records]
        evidence = request["criterion_evidence"]
        if not isinstance(evidence, list):
            raise TaskPlanFailure("criterion_evidence_required")
        data = {"records": records, "criterion_evidence": evidence}
    return plan_id, operation_id, project_root, expected, data


def _check_expected(expected: str | None, raw: bytes | None) -> None:
    if raw is None:
        if expected is None:
            return
        raise TaskPlanFailure("plan_not_found", "conflict")
    if expected is None:
        raise TaskPlanFailure("plan_already_exists", "conflict")
    if expected != _sha(raw):
        raise TaskPlanFailure("stale_revision", "conflict")


def _locate_replay(snapshot: _Snapshot, operation_id: str, request_hash: str) -> bool:
    for event in snapshot.events:
        if event["operation_id"] != operation_id:
            continue
        if event["request_hash"] != request_hash:
            raise TaskPlanFailure("operation_id_conflict", "conflict")
        return True
    return False


class TaskPlanService:
    """Deterministic plan operations over an injected store; None means unavailable."""

    def __init__(self, store: PlanStore | None = None) -> None:
        if store is not None and not isinstance(store, SerenaMemoryStore):
            raise TypeError("TaskPlanService requires SerenaMemoryStore")
        self._store = store

    def capability(self) -> dict[str, Any]:
        if self._store is None:
            return {
                "status": "unavailable",
                "reason_code": "task_plan_backend_not_configured",
                "project_root": None,
                "storage_scope": None,
                "repository_id": None,
                "namespace": None,
                "archive_namespace": None,
            }
        describe = getattr(self._store, "capability", None)
        if not callable(describe):
            return {
                "status": "unavailable",
                "reason_code": "task_plan_backend_interface_unsupported",
                "project_root": None,
                "storage_scope": None,
                "repository_id": None,
                "namespace": None,
                "archive_namespace": None,
            }
        try:
            return describe()
        except Exception:
            return {
                "status": "unavailable",
                "reason_code": "task_plan_backend_unavailable",
                "project_root": None,
                "storage_scope": getattr(self._store, "storage_scope", None),
                "repository_id": getattr(self._store, "repository_id", None),
                "namespace": None,
                "archive_namespace": None,
            }

    def _unavailable(self, plan_id: str | None, reason: str) -> dict[str, Any]:
        return self._make_receipt(
            status="unavailable",
            reason=reason,
            plan_id=plan_id,
            state="unknown",
            before_revision=None,
            current_revision=None,
        )

    def _make_receipt(self, **fields: Any) -> dict[str, Any]:
        store = self._store
        fields.setdefault(
            "storage_scope",
            getattr(store, "storage_scope", "project") if store is not None else None,
        )
        fields.setdefault("repository_id", getattr(store, "repository_id", None))
        return _receipt(**fields)

    def _history_binding(self, project_root: str) -> tuple[str | None, str | None]:
        if self._store is not None and getattr(self._store, "storage_scope", "project") == "global":
            repository_id = getattr(self._store, "repository_id", None)
            if not isinstance(repository_id, str) or not _REPOSITORY_ID.fullmatch(repository_id):
                raise TaskPlanFailure("repository_identity_invalid", "unavailable")
            return None, repository_id
        return project_root, None

    def _parse_plan(self, raw: bytes, plan_id: str, project_root: str) -> _Snapshot:
        history_root, repository_id = self._history_binding(project_root)
        return _parse_snapshot(raw, plan_id, history_root, repository_id=repository_id)

    def _request_hash_for(
        self, plan_id: str, project_root: str, operation: str, data: dict[str, Any]
    ) -> str:
        _, repository_id = self._history_binding(project_root)
        return _request_hash(plan_id, project_root, operation, data, repository_id=repository_id)

    def _append_event_for(
        self,
        raw: bytes | None,
        plan_id: str,
        project_root: str,
        operation_id: str,
        operation: str,
        request_hash: str,
        data: dict[str, Any],
    ) -> bytes:
        _, repository_id = self._history_binding(project_root)
        return _append_event(
            raw,
            plan_id,
            project_root,
            operation_id,
            operation,
            request_hash,
            data,
            repository_id=repository_id,
        )

    def _observed_state_for(
        self, raw: bytes | None, plan_id: str | None, project_root: str | None
    ) -> str:
        if plan_id is None or project_root is None:
            return "unknown"
        history_root, repository_id = self._history_binding(project_root)
        return _observed_state(raw, plan_id, history_root, repository_id=repository_id)

    def _scope(self, plan_id: str, archived: bool = False) -> tuple[str | None, str | None]:
        if self._store is None:
            return None, None
        project = getattr(self._store, "project_root", None)
        name_factory = getattr(self._store, "_memory_name", None)
        if callable(name_factory):
            name = name_factory(plan_id, archived)
        else:
            namespace = "archive-plans" if archived else "plans"
            name = f"{namespace}/PLAN-{plan_id}"
        return project if isinstance(project, str) else None, name

    def update(self, request: dict[str, Any]) -> dict[str, Any]:
        plan_id: str | None = None
        project: str | None = None
        memory_name: str | None = None
        before_revision: str | None = None
        current_revision: str | None = None
        state = "unknown"
        try:
            plan_id, operation_id, requested_project, expected, data = _request_data(
                request, "update"
            )
            if self._store is None:
                return self._unavailable(plan_id, "task_plan_backend_not_configured")
            project, memory_name = self._scope(plan_id)
            if not project or requested_project != project:
                raise TaskPlanFailure("project_scope_mismatch", "conflict")
            request_hash = self._request_hash_for(plan_id, project, "update", data)
            with self._store.locked(plan_id):
                raw = self._store.read(plan_id)
                current_revision = _sha(raw) if raw is not None else None
                before_revision = current_revision
                snapshot = self._parse_plan(raw, plan_id, project) if raw is not None else None
                state = _current_state(snapshot)
                if snapshot is not None and snapshot.completed:
                    raise TaskPlanFailure("plan_completed", "conflict")
                archived = self._store.read(plan_id, archived=True)
                if archived is not None:
                    self._parse_plan(archived, plan_id, project)
                    _, memory_name = self._scope(plan_id, archived=True)
                    raise TaskPlanFailure("plan_already_archived", "conflict")
                if snapshot is not None and _locate_replay(snapshot, operation_id, request_hash):
                    return self._make_receipt(
                        status="replayed",
                        reason="identical_operation_replay",
                        plan_id=plan_id,
                        state=state,
                        before_revision=expected,
                        current_revision=snapshot.revision,
                        replayed=True,
                        preservation=True,
                        readback="verified",
                        project_root=project,
                        memory_name=memory_name,
                    )
                _check_expected(expected, raw)
                records = {} if snapshot is None else dict(snapshot.records)
                active_ids = set() if snapshot is None else set(snapshot.active_ids)
                resolved = set() if snapshot is None else set(snapshot.resolved_blockers)
                _apply_records(records, active_ids, resolved, data["records"], completion=False)
                updated = self._append_event_for(
                    raw, plan_id, project, operation_id, "update", request_hash, data
                )
                parsed = self._parse_plan(updated, plan_id, project)
                status, actual = self._store.write(plan_id, raw, updated)
                current_revision = _sha(actual) if actual is not None else None
                state = _current_state(parsed)
                if status == "conflict":
                    return self._make_receipt(
                        status="conflict",
                        reason="state_changed_during_write",
                        plan_id=plan_id,
                        state=self._observed_state_for(actual, plan_id, project),
                        before_revision=before_revision,
                        current_revision=current_revision,
                        project_root=project,
                        memory_name=memory_name,
                    )
                if status == "unavailable":
                    return self._make_receipt(
                        status="unavailable",
                        reason="atomic_write_unavailable",
                        plan_id=plan_id,
                        state=_current_state(snapshot),
                        before_revision=before_revision,
                        current_revision=current_revision,
                        readback="not_applicable",
                        project_root=project,
                        memory_name=memory_name,
                    )
                if status != "written" or actual != updated:
                    return self._make_receipt(
                        status="uncertain",
                        reason="write_readback_uncertain",
                        plan_id=plan_id,
                        state=self._observed_state_for(actual, plan_id, project),
                        before_revision=before_revision,
                        current_revision=current_revision,
                        changed_ids=[record["record_id"] for record in data["records"]],
                        preservation=bool(actual and actual.startswith(parsed.legacy)),
                        readback="mismatch_or_unavailable",
                        reconciliation="required",
                        project_root=project,
                        memory_name=memory_name,
                    )
                return self._make_receipt(
                    status="updated",
                    reason="append_verified",
                    plan_id=plan_id,
                    state=state,
                    before_revision=before_revision,
                    current_revision=current_revision,
                    changed_ids=[record["record_id"] for record in data["records"]],
                    preservation=actual.startswith(parsed.legacy),
                    readback="verified",
                    project_root=project,
                    memory_name=memory_name,
                )
        except TaskPlanFailure as exc:
            return self._make_receipt(
                status=exc.status,
                reason=exc.reason,
                plan_id=plan_id,
                state=state,
                before_revision=before_revision,
                current_revision=current_revision,
                project_root=project,
                memory_name=memory_name,
            )
        except Exception:
            return self._make_receipt(
                status="unavailable",
                reason="task_plan_backend_unavailable",
                plan_id=plan_id,
                state=state,
                before_revision=before_revision,
                current_revision=current_revision,
                project_root=project,
                memory_name=memory_name,
            )

    def complete(self, request: dict[str, Any]) -> dict[str, Any]:
        plan_id: str | None = None
        project: str | None = None
        memory_name: str | None = None
        before_revision: str | None = None
        current_revision: str | None = None
        state = "unknown"
        try:
            plan_id, operation_id, requested_project, expected, data = _request_data(
                request, "complete"
            )
            if self._store is None:
                return self._unavailable(plan_id, "task_plan_backend_not_configured")
            project, memory_name = self._scope(plan_id)
            if not project or requested_project != project:
                raise TaskPlanFailure("project_scope_mismatch", "conflict")
            request_hash = self._request_hash_for(plan_id, project, "complete", data)
            with self._store.locked(plan_id):
                raw = self._store.read(plan_id)
                if raw is None:
                    archived = self._store.read(plan_id, archived=True)
                    if archived is None:
                        raise TaskPlanFailure("plan_not_found", "conflict")
                    snapshot = self._parse_plan(archived, plan_id, project)
                    current_revision = snapshot.revision
                    state = _current_state(snapshot)
                    _, memory_name = self._scope(plan_id, archived=True)
                    if _locate_replay(snapshot, operation_id, request_hash):
                        return self._make_receipt(
                            status="replayed",
                            reason="identical_completion_replay_after_archive",
                            plan_id=plan_id,
                            state="completed",
                            before_revision=expected,
                            current_revision=snapshot.revision,
                            replayed=True,
                            preservation=True,
                            readback="verified",
                            project_root=project,
                            memory_name=memory_name,
                        )
                    raise TaskPlanFailure("plan_already_archived", "conflict")
                current_revision = _sha(raw)
                before_revision = current_revision
                snapshot = self._parse_plan(raw, plan_id, project)
                state = _current_state(snapshot)
                if _locate_replay(snapshot, operation_id, request_hash):
                    return self._make_receipt(
                        status="replayed",
                        reason="identical_operation_replay",
                        plan_id=plan_id,
                        state="completed",
                        before_revision=expected,
                        current_revision=snapshot.revision,
                        replayed=True,
                        preservation=True,
                        readback="verified",
                        project_root=project,
                        memory_name=memory_name,
                    )
                archived = self._store.read(plan_id, archived=True)
                if archived is not None:
                    self._parse_plan(archived, plan_id, project)
                    raise TaskPlanFailure("archive_collision", "conflict")
                _check_expected(expected, raw)
                if snapshot.completed:
                    raise TaskPlanFailure("plan_already_completed", "conflict")
                records = dict(snapshot.records)
                active_ids = set(snapshot.active_ids)
                resolved = set(snapshot.resolved_blockers)
                _apply_records(records, active_ids, resolved, data["records"], completion=True)
                if not any(record["kind"] == "result" for record in data["records"]):
                    raise TaskPlanFailure("completion_result_required")
                unresolved = tuple(
                    sorted(
                        record_id
                        for record_id, record in records.items()
                        if record["kind"] == "blocker" and record_id not in resolved
                    )
                )
                evidence = _validate_evidence(
                    records, active_ids, unresolved, data["criterion_evidence"]
                )
                data["criterion_evidence"] = evidence
                updated = self._append_event_for(
                    raw, plan_id, project, operation_id, "complete", request_hash, data
                )
                parsed = self._parse_plan(updated, plan_id, project)
                status, actual = self._store.write(plan_id, raw, updated)
                current_revision = _sha(actual) if actual is not None else None
                state = _current_state(parsed)
                if status == "conflict":
                    return self._make_receipt(
                        status="conflict",
                        reason="state_changed_during_write",
                        plan_id=plan_id,
                        state=self._observed_state_for(actual, plan_id, project),
                        before_revision=before_revision,
                        current_revision=current_revision,
                        project_root=project,
                        memory_name=memory_name,
                    )
                if status == "unavailable":
                    return self._make_receipt(
                        status="unavailable",
                        reason="atomic_write_unavailable",
                        plan_id=plan_id,
                        state=_current_state(snapshot),
                        before_revision=before_revision,
                        current_revision=current_revision,
                        readback="not_applicable",
                        project_root=project,
                        memory_name=memory_name,
                    )
                if status != "written" or actual != updated:
                    return self._make_receipt(
                        status="uncertain",
                        reason="write_readback_uncertain",
                        plan_id=plan_id,
                        state=self._observed_state_for(actual, plan_id, project),
                        before_revision=before_revision,
                        current_revision=current_revision,
                        changed_ids=[record["record_id"] for record in data["records"]],
                        preservation=bool(actual and actual.startswith(parsed.legacy)),
                        readback="mismatch_or_unavailable",
                        reconciliation="required",
                        project_root=project,
                        memory_name=memory_name,
                    )
                return self._make_receipt(
                    status="completed",
                    reason="completion_evidence_recorded",
                    plan_id=plan_id,
                    state="completed",
                    before_revision=before_revision,
                    current_revision=current_revision,
                    changed_ids=[record["record_id"] for record in data["records"]],
                    preservation=actual.startswith(parsed.legacy),
                    readback="verified",
                    project_root=project,
                    memory_name=memory_name,
                )
        except TaskPlanFailure as exc:
            return self._make_receipt(
                status=exc.status,
                reason=exc.reason,
                plan_id=plan_id,
                state=state,
                before_revision=before_revision,
                current_revision=current_revision,
                project_root=project,
                memory_name=memory_name,
            )
        except Exception:
            return self._make_receipt(
                status="unavailable",
                reason="task_plan_backend_unavailable",
                plan_id=plan_id,
                state=state,
                before_revision=before_revision,
                current_revision=current_revision,
                project_root=project,
                memory_name=memory_name,
            )

    def archive(self, request: dict[str, Any]) -> dict[str, Any]:
        plan_id: str | None = None
        project: str | None = None
        memory_name: str | None = None
        before_revision: str | None = None
        current_revision: str | None = None
        state = "unknown"
        try:
            if not isinstance(request, dict) or set(request) != {
                "project_root",
                "plan_id",
                "expected_revision",
            }:
                raise TaskPlanFailure("invalid_request_fields")
            requested_project = request["project_root"]
            if (
                not isinstance(requested_project, str)
                or not Path(requested_project).is_absolute()
                or len(requested_project) > 4096
            ):
                raise TaskPlanFailure("invalid_project_root")
            plan_id = _validate_plan_id(request["plan_id"])
            expected = _validate_revision(request["expected_revision"])
            assert expected is not None
            if self._store is None:
                return self._unavailable(plan_id, "task_plan_backend_not_configured")
            project, source_name = self._scope(plan_id)
            _, target_name = self._scope(plan_id, archived=True)
            memory_name = source_name
            if not project or requested_project != project:
                raise TaskPlanFailure("project_scope_mismatch", "conflict")
            with self._store.locked(plan_id):
                source = self._store.read(plan_id)
                if source is None:
                    target = self._store.read(plan_id, archived=True)
                    if target is None:
                        raise TaskPlanFailure("plan_not_found", "conflict")
                    snapshot = self._parse_plan(target, plan_id, project)
                    current_revision = snapshot.revision
                    state = _current_state(snapshot)
                    if (
                        current_revision == expected
                        and snapshot.completed
                        and snapshot.events
                        and snapshot.events[-1]["operation"] == "complete"
                    ):
                        return self._make_receipt(
                            status="already_archived",
                            reason="identical_archive_replay",
                            plan_id=plan_id,
                            state="completed",
                            before_revision=expected,
                            current_revision=current_revision,
                            preservation=True,
                            readback="verified",
                            replayed=True,
                            project_root=project,
                            memory_name=target_name,
                        )
                    raise TaskPlanFailure("archive_reconciliation_mismatch", "conflict")
                current_revision = _sha(source)
                before_revision = current_revision
                snapshot = self._parse_plan(source, plan_id, project)
                state = _current_state(snapshot)
                if current_revision != expected:
                    raise TaskPlanFailure("stale_revision", "conflict")
                if not snapshot.completed:
                    raise TaskPlanFailure("plan_not_completed")
                existing_archive = self._store.read(plan_id, archived=True)
                if existing_archive is not None:
                    self._parse_plan(existing_archive, plan_id, project)
                    raise TaskPlanFailure("archive_collision", "conflict")
                status, actual = self._store.archive(plan_id, source)
                current_revision = _sha(actual) if actual is not None else None
                if status == "archived" and actual == source:
                    return self._make_receipt(
                        status="archived",
                        reason="completed_plan_moved_without_overwrite",
                        plan_id=plan_id,
                        state="completed",
                        before_revision=expected,
                        current_revision=current_revision,
                        preservation=True,
                        readback="verified",
                        project_root=project,
                        memory_name=target_name,
                    )
                if status == "unavailable":
                    return self._make_receipt(
                        status="unavailable",
                        reason="archive_primitive_unavailable",
                        plan_id=plan_id,
                        state="completed",
                        before_revision=before_revision,
                        current_revision=_sha(actual) if actual is not None else None,
                        preservation=actual == source,
                        readback="not_applicable",
                        project_root=project,
                        memory_name=source_name,
                    )
                reason = {
                    "collision": "archive_collision",
                    "conflict": "state_changed_during_archive",
                    "unavailable": "archive_unavailable",
                }.get(status, "archive_interrupted")
                return self._make_receipt(
                    status="conflict" if status in {"collision", "conflict"} else "uncertain",
                    reason=reason,
                    plan_id=plan_id,
                    state="completed",
                    before_revision=before_revision,
                    current_revision=current_revision,
                    preservation=actual == source,
                    readback="uncertain",
                    reconciliation="required",
                    project_root=project,
                    memory_name=source_name,
                )
        except TaskPlanFailure as exc:
            return self._make_receipt(
                status=exc.status,
                reason=exc.reason,
                plan_id=plan_id,
                state=state,
                before_revision=before_revision,
                current_revision=current_revision,
                project_root=project,
                memory_name=memory_name,
                reconciliation="required" if exc.status == "uncertain" else "not_required",
            )
        except Exception:
            return self._make_receipt(
                status="unavailable",
                reason="task_plan_backend_unavailable",
                plan_id=plan_id,
                state=state,
                before_revision=before_revision,
                current_revision=current_revision,
                project_root=project,
                memory_name=memory_name,
            )

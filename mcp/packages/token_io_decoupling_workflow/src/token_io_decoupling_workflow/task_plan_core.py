from __future__ import annotations

import contextlib
import hashlib
import importlib
import json
import os
import re
import stat
import tempfile
from collections.abc import Generator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

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
_HEADER_PREFIX = b"~~~json task-plan-header-v1\n"
_HEADER_SUFFIX = b"\n~~~\n"
_EVENT_PREFIX = b"~~~json task-plan-event-v1\n"
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


def _parse_snapshot(raw: bytes, plan_id: str, project_root: str | None = None) -> _Snapshot:
    if len(raw) > MAX_PLAN_BYTES:
        raise TaskPlanFailure("plan_too_large")
    marker_count = raw.count(_HEADER_PREFIX)
    if marker_count == 0:
        return _Snapshot(raw, raw, (), {}, frozenset(), frozenset(), False)
    if marker_count != 1:
        raise TaskPlanFailure("history_invalid")
    marker = raw.index(_HEADER_PREFIX)
    if marker and raw[marker - 1] not in b"\r\n":
        raise TaskPlanFailure("history_invalid")
    line_end = raw.find(_HEADER_SUFFIX, marker + len(_HEADER_PREFIX))
    if line_end < 0:
        raise TaskPlanFailure("history_invalid")
    header_end = line_end + len(_HEADER_SUFFIX)
    header = _json_object(raw[marker + len(_HEADER_PREFIX) : line_end])
    if set(header) != {
        "version",
        "plan_id",
        "project_root",
        "legacy_length",
        "legacy_revision",
    }:
        raise TaskPlanFailure("history_invalid")
    if (
        header["version"] != 1
        or header["plan_id"] != plan_id
        or not isinstance(header["project_root"], str)
        or (project_root is not None and header["project_root"] != project_root)
    ):
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
        if not raw.startswith(_EVENT_PREFIX, position):
            raise TaskPlanFailure("history_invalid")
        if position and raw[position - 1] not in b"\r\n":
            raise TaskPlanFailure("history_invalid")
        event_start = position + len(_EVENT_PREFIX)
        event_end = raw.find(_EVENT_SUFFIX, event_start)
        if event_end < 0:
            raise TaskPlanFailure("history_invalid")
        event = _json_object(raw[event_start:event_end])
        expected_keys = {
            "version",
            "plan_id",
            "project_root",
            "operation_id",
            "operation",
            "request_hash",
            "previous_revision",
            "data",
        }
        if set(event) != expected_keys or event["version"] != 1:
            raise TaskPlanFailure("history_invalid")
        if (
            event["plan_id"] != plan_id
            or event["project_root"] != header["project_root"]
            or (project_root is not None and event["project_root"] != project_root)
            or event["operation"] not in {"update", "complete"}
        ):
            raise TaskPlanFailure("history_identity_mismatch")
        op_id = _validate_id(event["operation_id"], _REQUEST_ID, "history_invalid")
        if not isinstance(event["data"], dict):
            raise TaskPlanFailure("history_invalid")
        request_hash = _request_hash(
            plan_id, event["project_root"], event["operation"], event["data"]
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


def _request_hash(plan_id: str, project_root: str, operation: str, data: dict[str, Any]) -> str:
    return _sha(
        _canonical_json(
            {
                "plan_id": plan_id,
                "project_root": project_root,
                "operation": operation,
                "data": data,
            }
        )
    )


def _event_line(event: dict[str, Any]) -> bytes:
    return _EVENT_PREFIX + _canonical_json(event) + _EVENT_SUFFIX


def _append_event(
    raw: bytes | None,
    plan_id: str,
    project_root: str,
    operation_id: str,
    operation: str,
    request_hash: str,
    data: dict[str, Any],
) -> bytes:
    if raw is None:
        legacy = b""
        separator = b""
        header = {
            "version": 1,
            "plan_id": plan_id,
            "project_root": project_root,
            "legacy_length": 0,
            "legacy_revision": _sha(legacy),
        }
        prefix = separator + _HEADER_PREFIX + _canonical_json(header) + _HEADER_SUFFIX
        previous = _sha(legacy)
    else:
        snapshot = _parse_snapshot(raw, plan_id, project_root)
        if snapshot.events:
            prefix = b""
        else:
            separator = b"" if not raw or raw.endswith((b"\n", b"\r")) else b"\n"
            header = {
                "version": 1,
                "plan_id": plan_id,
                "project_root": project_root,
                "legacy_length": len(raw),
                "legacy_revision": _sha(raw),
            }
            prefix = separator + _HEADER_PREFIX + _canonical_json(header) + _HEADER_SUFFIX
        previous = _sha(raw)
    event = {
        "version": 1,
        "plan_id": plan_id,
        "project_root": project_root,
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


def _observed_state(raw: bytes | None, plan_id: str | None, project_root: str | None) -> str:
    if plan_id is None or project_root is None:
        return "unknown"
    if raw is None:
        return "absent"
    try:
        return _current_state(_parse_snapshot(raw, plan_id, project_root))
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
) -> dict[str, Any]:
    return {
        "status": status,
        "reason": reason,
        "plan_id": plan_id,
        "project_root": project_root,
        "memory_name": memory_name,
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

    def __init__(self, memory_manager: object, project_root: str | Path) -> None:
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
        root_value = getattr(memory_manager, "_project_memory_dir", None)
        if not isinstance(root_value, (str, Path)):
            raise TaskPlanFailure("serena_project_memory_unavailable", "unavailable")
        root_path = Path(root_value)
        try:
            root_stat = root_path.lstat()
            if (
                not root_path.is_absolute()
                or stat.S_ISLNK(root_stat.st_mode)
                or not stat.S_ISDIR(root_stat.st_mode)
            ):
                raise TaskPlanFailure("serena_project_memory_invalid", "unavailable")
            self.memory_root = root_path.resolve(strict=True)
            project_path = Path(project_root)
            if not project_path.is_absolute():
                raise TaskPlanFailure("project_root_must_be_absolute", "unavailable")
            self.project_root = str(project_path.resolve(strict=True))
            if not Path(self.project_root).is_dir():
                raise TaskPlanFailure("project_root_unavailable", "unavailable")
        except TaskPlanFailure:
            raise
        except OSError as exc:
            raise TaskPlanFailure("serena_project_memory_unavailable", "unavailable") from exc
        self._manager = memory_manager

    def capability(self) -> dict[str, Any]:
        return {
            "status": "configured",
            "reason_code": "explicit_serena_manager_injected",
            "project_root": self.project_root,
            "namespace": "plans/PLAN-<plan_id>",
            "archive_namespace": "archive-plans/PLAN-<plan_id>",
        }

    def _memory_name(self, plan_id: str, archived: bool) -> str:
        prefix = "archive-plans" if archived else "plans"
        return f"{prefix}/PLAN-{plan_id}"

    def _fixed_path(self, plan_id: str, archived: bool) -> Path:
        namespace = "archive-plans" if archived else "plans"
        return self.memory_root / namespace / f"PLAN-{plan_id}.md"

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
        namespace = path.parent
        try:
            if namespace.is_symlink():
                raise TaskPlanFailure("memory_namespace_symlink_rejected", "unavailable")
            if namespace.exists() and not namespace.is_dir():
                raise TaskPlanFailure("memory_namespace_invalid", "unavailable")
            if path.is_symlink():
                raise TaskPlanFailure("memory_file_symlink_rejected", "unavailable")
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
        if fcntl is None:
            raise TaskPlanFailure("posix_file_lock_unavailable", "unavailable")
        lock_path = self.memory_root / ".token-io-task-plan.lock"
        try:
            if lock_path.is_symlink():
                raise TaskPlanFailure("lock_file_symlink_rejected", "unavailable")
            flags = os.O_CREAT | os.O_RDWR
            flags |= getattr(os, "O_NOFOLLOW", 0)
            descriptor = os.open(lock_path, flags, 0o600)
        except TaskPlanFailure:
            raise
        except OSError as exc:
            raise TaskPlanFailure("plan_lock_unavailable", "unavailable") from exc
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            yield
        except OSError as exc:
            raise TaskPlanFailure("plan_lock_unavailable", "unavailable") from exc
        finally:
            try:
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
                "namespace": None,
            }
        describe = getattr(self._store, "capability", None)
        if not callable(describe):
            return {
                "status": "unavailable",
                "reason_code": "task_plan_backend_interface_unsupported",
                "project_root": None,
                "namespace": None,
            }
        try:
            return describe()
        except Exception:
            return {
                "status": "unavailable",
                "reason_code": "task_plan_backend_unavailable",
                "project_root": None,
                "namespace": None,
            }

    def _unavailable(self, plan_id: str | None, reason: str) -> dict[str, Any]:
        return _receipt(
            status="unavailable",
            reason=reason,
            plan_id=plan_id,
            state="unknown",
            before_revision=None,
            current_revision=None,
        )

    def _scope(self, plan_id: str, archived: bool = False) -> tuple[str | None, str | None]:
        if self._store is None:
            return None, None
        project = getattr(self._store, "project_root", None)
        name = f"{'archive-plans' if archived else 'plans'}/PLAN-{plan_id}"
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
            request_hash = _request_hash(plan_id, project, "update", data)
            with self._store.locked(plan_id):
                raw = self._store.read(plan_id)
                current_revision = _sha(raw) if raw is not None else None
                before_revision = current_revision
                snapshot = _parse_snapshot(raw, plan_id, project) if raw is not None else None
                state = _current_state(snapshot)
                if snapshot is not None and snapshot.completed:
                    raise TaskPlanFailure("plan_completed", "conflict")
                archived = self._store.read(plan_id, archived=True)
                if archived is not None:
                    _parse_snapshot(archived, plan_id, project)
                    memory_name = f"archive-plans/PLAN-{plan_id}"
                    raise TaskPlanFailure("plan_already_archived", "conflict")
                if snapshot is not None and _locate_replay(snapshot, operation_id, request_hash):
                    return _receipt(
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
                updated = _append_event(
                    raw, plan_id, project, operation_id, "update", request_hash, data
                )
                parsed = _parse_snapshot(updated, plan_id, project)
                status, actual = self._store.write(plan_id, raw, updated)
                current_revision = _sha(actual) if actual is not None else None
                state = _current_state(parsed)
                if status == "conflict":
                    return _receipt(
                        status="conflict",
                        reason="state_changed_during_write",
                        plan_id=plan_id,
                        state=_observed_state(actual, plan_id, project),
                        before_revision=before_revision,
                        current_revision=current_revision,
                        project_root=project,
                        memory_name=memory_name,
                    )
                if status == "unavailable":
                    return _receipt(
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
                    return _receipt(
                        status="uncertain",
                        reason="write_readback_uncertain",
                        plan_id=plan_id,
                        state=_observed_state(actual, plan_id, project),
                        before_revision=before_revision,
                        current_revision=current_revision,
                        changed_ids=[record["record_id"] for record in data["records"]],
                        preservation=bool(actual and actual.startswith(parsed.legacy)),
                        readback="mismatch_or_unavailable",
                        reconciliation="required",
                        project_root=project,
                        memory_name=memory_name,
                    )
                return _receipt(
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
            return _receipt(
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
            return _receipt(
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
            request_hash = _request_hash(plan_id, project, "complete", data)
            with self._store.locked(plan_id):
                raw = self._store.read(plan_id)
                if raw is None:
                    archived = self._store.read(plan_id, archived=True)
                    if archived is None:
                        raise TaskPlanFailure("plan_not_found", "conflict")
                    snapshot = _parse_snapshot(archived, plan_id, project)
                    current_revision = snapshot.revision
                    state = _current_state(snapshot)
                    memory_name = f"archive-plans/PLAN-{plan_id}"
                    if _locate_replay(snapshot, operation_id, request_hash):
                        return _receipt(
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
                snapshot = _parse_snapshot(raw, plan_id, project)
                state = _current_state(snapshot)
                if _locate_replay(snapshot, operation_id, request_hash):
                    return _receipt(
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
                    _parse_snapshot(archived, plan_id, project)
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
                updated = _append_event(
                    raw, plan_id, project, operation_id, "complete", request_hash, data
                )
                parsed = _parse_snapshot(updated, plan_id, project)
                status, actual = self._store.write(plan_id, raw, updated)
                current_revision = _sha(actual) if actual is not None else None
                state = _current_state(parsed)
                if status == "conflict":
                    return _receipt(
                        status="conflict",
                        reason="state_changed_during_write",
                        plan_id=plan_id,
                        state=_observed_state(actual, plan_id, project),
                        before_revision=before_revision,
                        current_revision=current_revision,
                        project_root=project,
                        memory_name=memory_name,
                    )
                if status == "unavailable":
                    return _receipt(
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
                    return _receipt(
                        status="uncertain",
                        reason="write_readback_uncertain",
                        plan_id=plan_id,
                        state=_observed_state(actual, plan_id, project),
                        before_revision=before_revision,
                        current_revision=current_revision,
                        changed_ids=[record["record_id"] for record in data["records"]],
                        preservation=bool(actual and actual.startswith(parsed.legacy)),
                        readback="mismatch_or_unavailable",
                        reconciliation="required",
                        project_root=project,
                        memory_name=memory_name,
                    )
                return _receipt(
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
            return _receipt(
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
            return _receipt(
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
            target_name = f"archive-plans/PLAN-{plan_id}"
            memory_name = source_name
            if not project or requested_project != project:
                raise TaskPlanFailure("project_scope_mismatch", "conflict")
            with self._store.locked(plan_id):
                source = self._store.read(plan_id)
                if source is None:
                    target = self._store.read(plan_id, archived=True)
                    if target is None:
                        raise TaskPlanFailure("plan_not_found", "conflict")
                    snapshot = _parse_snapshot(target, plan_id, project)
                    current_revision = snapshot.revision
                    state = _current_state(snapshot)
                    if (
                        current_revision == expected
                        and snapshot.completed
                        and snapshot.events
                        and snapshot.events[-1]["operation"] == "complete"
                    ):
                        return _receipt(
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
                snapshot = _parse_snapshot(source, plan_id, project)
                state = _current_state(snapshot)
                if current_revision != expected:
                    raise TaskPlanFailure("stale_revision", "conflict")
                if not snapshot.completed:
                    raise TaskPlanFailure("plan_not_completed")
                existing_archive = self._store.read(plan_id, archived=True)
                if existing_archive is not None:
                    _parse_snapshot(existing_archive, plan_id, project)
                    raise TaskPlanFailure("archive_collision", "conflict")
                status, actual = self._store.archive(plan_id, source)
                current_revision = _sha(actual) if actual is not None else None
                if status == "archived" and actual == source:
                    return _receipt(
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
                    return _receipt(
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
                return _receipt(
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
            return _receipt(
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
            return _receipt(
                status="unavailable",
                reason="task_plan_backend_unavailable",
                plan_id=plan_id,
                state=state,
                before_revision=before_revision,
                current_revision=current_revision,
                project_root=project,
                memory_name=memory_name,
            )

"""核验任务计划历史头部、身份和原始字节链。"""

from __future__ import annotations

from typing import Any

from .codec import _json_object, _request_hash
from .constants import (
    _EVENT_PREFIX,
    _EVENT_SUFFIX,
    _EVENT_V2_PREFIX,
    _HEADER_PREFIX,
    _HEADER_SUFFIX,
    _HEADER_V2_PREFIX,
    _REPOSITORY_ID,
    _REQUEST_ID,
    MAX_EVENTS,
    MAX_PLAN_BYTES,
)
from .records import _apply_records, _validate_evidence, _validate_id, _validate_record
from .types import TaskPlanFailure, _HistoryHeader, _sha, _Snapshot


def _read_history_block(
    raw: bytes, position: int, prefix: bytes, suffix: bytes
) -> tuple[dict[str, Any], int]:
    """读取一个完整的行边界块，不重新编码原始字节。"""
    if not raw.startswith(prefix, position):
        raise TaskPlanFailure("history_invalid")
    if position and raw[position - 1] not in b"\r\n":
        raise TaskPlanFailure("history_invalid")
    start = position + len(prefix)
    end = raw.find(suffix, start)
    if end < 0:
        raise TaskPlanFailure("history_invalid")
    return _json_object(raw[start:end]), end + len(suffix)


def _validate_history_header_identity(
    header: dict[str, Any],
    version: int,
    plan_id: str,
    project_root: str | None,
    repository_id: str | None,
) -> str:
    if version == 1:
        identity_key = "project_root"
        expected_identity = project_root
    else:
        identity_key = "repository_id"
        expected_identity = repository_id
    expected_keys = {"version", "plan_id", identity_key, "legacy_length", "legacy_revision"}
    if set(header) != expected_keys or header["version"] != version:
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
    return identity_key


def _history_legacy_prefix(raw: bytes, marker: int, header: dict[str, Any]) -> bytes:
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
    return legacy


def _parse_history_header(
    raw: bytes, plan_id: str, project_root: str | None, repository_id: str | None
) -> _HistoryHeader | None:
    v1_marker_count = raw.count(_HEADER_PREFIX)
    marker_count = v1_marker_count + raw.count(_HEADER_V2_PREFIX)
    if marker_count == 0:
        return None
    if marker_count != 1:
        raise TaskPlanFailure("history_invalid")
    version = 1 if v1_marker_count else 2
    prefix = _HEADER_PREFIX if version == 1 else _HEADER_V2_PREFIX
    marker = raw.index(prefix)
    header, end = _read_history_block(raw, marker, prefix, _HEADER_SUFFIX)
    identity_key = _validate_history_header_identity(
        header, version, plan_id, project_root, repository_id
    )
    legacy = _history_legacy_prefix(raw, marker, header)
    if end > len(raw):
        raise TaskPlanFailure("history_invalid")
    return _HistoryHeader(version, plan_id, identity_key, header[identity_key], legacy, end)


def _validate_history_event_identity(event: dict[str, Any], header: _HistoryHeader) -> None:
    expected_keys = {
        "version",
        "plan_id",
        header.identity_key,
        "operation_id",
        "operation",
        "request_hash",
        "previous_revision",
        "data",
    }
    if set(event) != expected_keys or event["version"] != header.version:
        raise TaskPlanFailure("history_invalid")
    # 头部已核验调用方绑定，每个事件必须沿用这一身份。
    if (
        event["plan_id"] != header.plan_id
        or event[header.identity_key] != header.identity
        or event["operation"] not in {"update", "complete"}
    ):
        raise TaskPlanFailure("history_identity_mismatch")
    if header.version == 2 and not _REPOSITORY_ID.fullmatch(event["repository_id"]):
        raise TaskPlanFailure("history_identity_mismatch")


def _validate_history_event(
    event: dict[str, Any],
    header: _HistoryHeader,
    previous_revision: str,
    operation_ids: set[str],
) -> None:
    """先核验事件身份与请求摘要，再检查链和重复操作，保留错误优先级。"""
    _validate_history_event_identity(event, header)
    operation_id = _validate_id(event["operation_id"], _REQUEST_ID, "history_invalid")
    if not isinstance(event["data"], dict):
        raise TaskPlanFailure("history_invalid")
    request_hash = _request_hash(
        header.plan_id,
        event["project_root"] if header.version == 1 else "",
        event["operation"],
        event["data"],
        repository_id=event["repository_id"] if header.version == 2 else None,
    )
    if event["request_hash"] != request_hash:
        raise TaskPlanFailure("history_request_hash_mismatch")
    if event["previous_revision"] != previous_revision:
        raise TaskPlanFailure("history_chain_mismatch")
    if operation_id in operation_ids:
        raise TaskPlanFailure("history_duplicate_operation_id")
    operation_ids.add(operation_id)


def _apply_history_event(
    event: dict[str, Any],
    records: dict[str, dict[str, Any]],
    active_ids: set[str],
    resolved_blockers: set[str],
    completed: bool,
) -> bool:
    """重放记录并校验完成证据，返回新的完成状态。"""
    data = event["data"]
    if set(data) != (
        {"records"} if event["operation"] == "update" else {"records", "criterion_evidence"}
    ):
        raise TaskPlanFailure("history_invalid")
    additions = data["records"]
    if completed:
        raise TaskPlanFailure("history_after_completion")
    normalized = (
        [_validate_record(record) for record in additions] if isinstance(additions, list) else []
    )
    if normalized != additions:
        raise TaskPlanFailure("history_record_invalid")
    completion = event["operation"] == "complete"
    _apply_records(records, active_ids, resolved_blockers, normalized, completion=completion)
    if not completion:
        return False
    if not any(record["kind"] == "result" for record in normalized):
        raise TaskPlanFailure("completion_result_required")
    unresolved = tuple(
        sorted(
            record_id
            for record_id, record in records.items()
            if record["kind"] == "blocker" and record_id not in resolved_blockers
        )
    )
    evidence = _validate_evidence(records, active_ids, unresolved, data["criterion_evidence"])
    if evidence != data["criterion_evidence"]:
        raise TaskPlanFailure("history_invalid")
    return True


def _replay_history(raw: bytes, header: _HistoryHeader) -> _Snapshot:
    events: list[dict[str, Any]] = []
    records: dict[str, dict[str, Any]] = {}
    active_ids: set[str] = set()
    resolved_blockers: set[str] = set()
    operation_ids: set[str] = set()
    completed = False
    position = header.end
    event_prefix = _EVENT_PREFIX if header.version == 1 else _EVENT_V2_PREFIX
    while position < len(raw):
        event, end = _read_history_block(raw, position, event_prefix, _EVENT_SUFFIX)
        previous = _sha(header.legacy) if not events else _sha(raw[:position])
        _validate_history_event(event, header, previous, operation_ids)
        completed = _apply_history_event(event, records, active_ids, resolved_blockers, completed)
        events.append(event)
        if len(events) > MAX_EVENTS:
            raise TaskPlanFailure("history_too_large")
        position = end
    return _Snapshot(
        raw,
        header.legacy,
        tuple(events),
        records,
        frozenset(active_ids),
        frozenset(resolved_blockers),
        completed,
    )


def _parse_snapshot(
    raw: bytes,
    plan_id: str,
    project_root: str | None = None,
    *,
    repository_id: str | None = None,
) -> _Snapshot:
    """按头部身份和原始字节链重放计划；无历史标记时保留整个旧正文。"""
    if len(raw) > MAX_PLAN_BYTES:
        raise TaskPlanFailure("plan_too_large")
    header = _parse_history_header(raw, plan_id, project_root, repository_id)
    if header is None:
        return _Snapshot(raw, raw, (), {}, frozenset(), frozenset(), False)
    return _replay_history(raw, header)

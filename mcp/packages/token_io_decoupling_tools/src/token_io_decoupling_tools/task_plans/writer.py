"""向已核验的计划追加规范事件，保留已有历史字节。"""

from __future__ import annotations

from typing import Any

from .codec import _canonical_json, _event_line, _history_identity
from .constants import _HEADER_PREFIX, _HEADER_SUFFIX, _HEADER_V2_PREFIX, MAX_PLAN_BYTES
from .history import _parse_snapshot
from .types import TaskPlanFailure, _sha


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

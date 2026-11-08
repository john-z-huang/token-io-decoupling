"""任务计划的规范 JSON、请求摘要与事件编码。"""

from __future__ import annotations

import json
from typing import Any

from .constants import _EVENT_PREFIX, _EVENT_SUFFIX, _EVENT_V2_PREFIX, _REPOSITORY_ID
from .types import TaskPlanFailure, _sha


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

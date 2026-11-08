"""报告写入、内容指纹与递归脱敏，避免保存原始异常和凭据。"""

from __future__ import annotations

import hashlib
import json
import math
import os
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path

_REDACTED_KEYS = {
    "api_key",
    "authorization",
    "base_url",
    "headers",
    "raw_error",
    "raw_exception",
    "error_message",
    "exception_message",
}


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _canonical_hash(value: object) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return _sha256(payload)


def _write_json(fd: int, report: Mapping[str, object]) -> None:
    payload = (
        json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"
    ).encode("utf-8")
    os.lseek(fd, 0, os.SEEK_SET)
    os.ftruncate(fd, 0)
    offset = 0
    while offset < len(payload):
        offset += os.write(fd, payload[offset:])
    os.fsync(fd)


def _reserve_output(path_value: str | Path) -> tuple[Path, int]:
    requested = Path(path_value).expanduser()
    if not requested.name:
        raise ValueError("output_must_name_a_new_file")
    parent = requested.parent.resolve(strict=True)
    if not parent.is_dir():
        raise ValueError("output_parent_must_be_a_directory")
    output_path = parent / requested.name
    fd = os.open(output_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    return output_path, fd


def _safe_mapping(value: Mapping[object, object]) -> dict[str, object]:
    result = {}
    for key, item in value.items():
        key_text = str(key)
        if key_text.lower() not in _REDACTED_KEYS:
            result[key_text] = _json_safe(item)
    return result


def _safe_model(value: object) -> object:
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        try:
            return _json_safe(model_dump(mode="json"))
        except Exception:
            # 模型序列化是外部扩展边界，失败只保留类型，不记录原始诊断。
            return {"value_type": type(value).__name__}
    return {"value_type": type(value).__name__}


def _safe_scalar(value: float | Path | BaseException) -> object:
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, Path):
        return value.as_posix()
    return {"error_type": type(value).__name__}


def _json_safe(value: object) -> object:
    if value is None or type(value) in {bool, int, str}:
        return value
    if isinstance(value, (float, Path, BaseException)):
        return _safe_scalar(value)
    if isinstance(value, Mapping):
        return _safe_mapping(value)
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return _safe_model(value)

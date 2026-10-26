"""Shared serialization, time, hash, and safe SQL primitives."""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from token_io_decoupling_core.state_models import (
    OutputClass,
)

DEFAULT_STATE_ROOT = Path.home() / ".local" / "state" / "token-io-decoupling"
_SAFE_COMPONENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_WORKER_OUTPUT_CLASSES = {OutputClass.CODE_CONFIGURATION, OutputClass.SKILL_INSTRUCTIONS}


def _nonempty(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _hash_json(value: object) -> str:
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def _one(
    connection: sqlite3.Connection,
    sql: str,
    parameters: tuple[object, ...] = (),
) -> sqlite3.Row | None:
    connection.row_factory = sqlite3.Row
    return connection.execute(sql, parameters).fetchone()

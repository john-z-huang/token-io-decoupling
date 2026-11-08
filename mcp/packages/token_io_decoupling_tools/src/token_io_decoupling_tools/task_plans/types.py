"""任务计划快照、存储协议和稳定异常。"""

from __future__ import annotations

import contextlib
import hashlib
from collections.abc import Generator
from dataclasses import dataclass
from typing import Any, Protocol


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


@dataclass(frozen=True)
class _HistoryHeader:
    """已核验调用方身份和旧正文的历史头部，保留事件起始字节偏移。"""

    version: int
    plan_id: str
    identity_key: str
    identity: str
    legacy: bytes
    end: int

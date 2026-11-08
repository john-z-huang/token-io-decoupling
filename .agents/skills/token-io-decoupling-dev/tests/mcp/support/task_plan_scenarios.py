"""任务计划测试的内存存储协作者、请求和临时文件后端。"""

from __future__ import annotations

import hashlib
import threading
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

from token_io_decoupling_tools.task_plan_core import (
    SerenaMemoryStore,
    TaskPlanService,
)


@dataclass
class _State:
    plans: dict[str, bytes] = field(default_factory=dict)
    archives: dict[str, bytes] = field(default_factory=dict)
    lock: threading.RLock = field(default_factory=threading.RLock)
    lock_calls: int = 0
    read_calls: int = 0
    write_mode: str = "normal"
    archive_mode: str = "normal"


class _TestSerenaMemoryStore(SerenaMemoryStore):
    """A test-only store collaborator; production construction requires Serena MemoryManager."""

    def __init__(self, project_root: str, state: _State | None = None) -> None:
        self.project_root = project_root
        self.state = state or _State()

    def capability(self) -> dict[str, object]:
        return {
            "status": "configured",
            "reason_code": "test_collaborator",
            "project_root": self.project_root,
            "storage_scope": "project",
            "repository_id": None,
            "namespace": "plans/PLAN-<plan_id>",
            "archive_namespace": "archive-plans/PLAN-<plan_id>",
        }

    @contextmanager
    def locked(self, plan_id: str) -> Generator[None, None, None]:
        with self.state.lock:
            self.state.lock_calls += 1
            yield

    def read(self, plan_id: str, *, archived: bool = False) -> bytes | None:
        with self.state.lock:
            self.state.read_calls += 1
            collection = self.state.archives if archived else self.state.plans
            return collection.get(plan_id)

    def write(
        self, plan_id: str, expected: bytes | None, content: bytes
    ) -> tuple[str, bytes | None]:
        with self.state.lock:
            current = self.state.plans.get(plan_id)
            if current != expected:
                return "conflict", current
            if self.state.write_mode == "unavailable":
                return "unavailable", current
            self.state.plans[plan_id] = content
            if self.state.write_mode == "mutated_unverified":
                return "uncertain", content[:-1]
            return "written", content

    def archive(self, plan_id: str, expected: bytes) -> tuple[str, bytes | None]:
        with self.state.lock:
            source = self.state.plans.get(plan_id)
            if source != expected:
                return "conflict", source
            if plan_id in self.state.archives:
                return "collision", source
            self.state.archives[plan_id] = source
            if self.state.archive_mode == "linked_before_unlink":
                return "uncertain", source
            del self.state.plans[plan_id]
            return "archived", source


class _FilesystemMemoryManager:
    def __init__(self, memory_root: Path) -> None:
        self._project_memory_dir = memory_root

    def _check_not_ignored(self, memory_name: str) -> None:
        del memory_name

    def _check_write_access(self, memory_name: str, write: bool) -> None:
        del memory_name, write

    def get_memory_file_path(self, memory_name: str) -> Path:
        path = self._project_memory_dir / f"{memory_name}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        return path


def _record(
    record_id: str,
    kind: str,
    text: str | None = None,
    *,
    outcome: str | None = None,
    resolves: str | None = None,
    supersedes: str | None = None,
    supersedes_reason: str | None = None,
) -> dict[str, object]:
    return {
        "record_id": record_id,
        "kind": kind,
        "text": text or f"Text for {record_id}",
        "sources": ["verified user/task context"],
        "outcome": outcome,
        "resolves_blocker_id": resolves,
        "supersedes_id": supersedes,
        "supersedes_reason": supersedes_reason,
    }


def _update(
    project: str,
    plan_id: str,
    expected: str | None,
    operation_id: str,
    *records: dict[str, object],
) -> dict[str, object]:
    return {
        "project_root": project,
        "plan_id": plan_id,
        "expected_revision": expected,
        "request_id": operation_id,
        "records": list(records),
    }


def _complete(
    project: str,
    plan_id: str,
    expected: str,
    operation_id: str,
    evidence: list[dict[str, str]],
    *records: dict[str, object],
) -> dict[str, object]:
    return {
        "project_root": project,
        "plan_id": plan_id,
        "expected_revision": expected,
        "request_id": operation_id,
        "criterion_evidence": evidence,
        "records": list(records),
    }


def _revision(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _service(
    tmp_path, state: _State | None = None
) -> tuple[TaskPlanService, _TestSerenaMemoryStore]:
    root = str(tmp_path.resolve())
    store = _TestSerenaMemoryStore(root, state)
    return TaskPlanService(store), store


def _filesystem_service(tmp_path) -> tuple[TaskPlanService, SerenaMemoryStore]:
    project_root = tmp_path / "project"
    project_root.mkdir()
    memory_root = tmp_path / "serena-memory"
    memory_root.mkdir()
    store = object.__new__(SerenaMemoryStore)
    store.project_root = str(project_root.resolve())
    store.memory_root = memory_root.resolve()
    store._manager = _FilesystemMemoryManager(store.memory_root)
    return TaskPlanService(store), store


def _archive(project: str, plan_id: str, expected: str) -> dict[str, object]:
    return {"project_root": project, "plan_id": plan_id, "expected_revision": expected}

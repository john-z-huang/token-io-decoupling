"""绑定 Serena MemoryManager 的任务计划存储接口。"""

from __future__ import annotations

import contextlib
import importlib
import os
import stat
from collections.abc import Generator
from pathlib import Path
from typing import Any, Literal

from . import store_io as _store_io
from .constants import _GLOBAL_MEMORY_PREFIX, _REPOSITORY_ID
from .identity import _canonical_plan_project_root, _memory_root_for, _repository_id_for_checkout
from .records import _validate_plan_id
from .types import TaskPlanFailure


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

        self.project_root = _canonical_plan_project_root(project_root)

        self.memory_root = _memory_root_for(memory_manager, storage_scope)

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

    def _namespace_root_for(self, path: Path) -> Path:
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
        return checked_root

    @staticmethod
    def _check_namespace_components(path: Path, checked_root: Path) -> None:
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

    def _check_namespace(self, path: Path) -> None:
        if self.memory_root.is_symlink():
            raise TaskPlanFailure("memory_root_symlink_rejected", "unavailable")
        try:
            checked_root = self._namespace_root_for(path)
            self._check_namespace_components(path, checked_root)
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
        with _store_io.locked(self, plan_id):
            yield

    def _read_path(self, path: Path) -> bytes | None:
        return _store_io.read_path(self, path)

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

    def _read_after_failure(self, path: Path) -> bytes | None:
        return _store_io.read_after_failure(self, path)

    def _read_archive_failure(
        self, source: Path, target: Path
    ) -> tuple[bytes | None, bytes | None]:
        return _store_io.read_archive_failure(self, source, target)

    def _archive_readback(
        self, source: Path, target: Path, expected: bytes
    ) -> tuple[str, bytes | None]:
        return _store_io.archive_readback(self, source, target, expected)

    @staticmethod
    def _archive_failure_status(
        source_bytes: bytes | None, target_bytes: bytes | None, expected: bytes
    ) -> tuple[str, bytes | None]:
        return _store_io.archive_failure_status(source_bytes, target_bytes, expected)

    def write(
        self, plan_id: str, expected: bytes | None, content: bytes
    ) -> tuple[str, bytes | None]:
        return _store_io.write(self, plan_id, expected, content)

    def _archive_links_match(
        self, source: Path, target: Path, source_stat: os.stat_result, expected: bytes
    ) -> bool:
        return _store_io.archive_links_match(self, source, target, source_stat, expected)

    def archive(self, plan_id: str, expected: bytes) -> tuple[str, bytes | None]:
        return _store_io.archive(self, plan_id, expected)

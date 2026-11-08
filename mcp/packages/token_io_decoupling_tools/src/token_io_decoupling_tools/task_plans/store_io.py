"""计划文件的有界读取、原子写入、无覆盖归档和锁。"""

from __future__ import annotations

import contextlib
import os
import stat
import tempfile
from collections.abc import Generator
from pathlib import Path
from typing import TYPE_CHECKING

from .constants import MAX_PLAN_BYTES
from .records import _validate_plan_id
from .types import TaskPlanFailure

if TYPE_CHECKING:
    from .store import SerenaMemoryStore

try:
    import fcntl
except ImportError:  # pragma: no cover - exercised on non-POSIX hosts
    fcntl = None  # type: ignore[assignment]


def _discard_plan_temporary(temp_path: Path) -> None:
    try:
        temp_path.unlink()
    except FileNotFoundError:
        pass


def _failed_plan_write_status(actual: bytes | None, expected: bytes | None, content: bytes) -> str:
    if actual == content:
        return "uncertain"
    if actual == expected:
        return "unavailable"
    return "uncertain"


@contextlib.contextmanager
def locked(store: SerenaMemoryStore, plan_id: str) -> Generator[None, None, None]:
    _validate_plan_id(plan_id)
    store._assert_current_binding()
    if fcntl is None:
        raise TaskPlanFailure("posix_file_lock_unavailable", "unavailable")
    store._check_namespace(store._fixed_path(plan_id, False))
    store._check_namespace(store._fixed_path(plan_id, True))
    lock_path = store.memory_root / ".token-io-task-plan.lock"
    store._check_namespace(lock_path)
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
        store._assert_current_binding()
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


def read_path(store: SerenaMemoryStore, path: Path) -> bytes | None:
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


def read_after_failure(store: SerenaMemoryStore, path: Path) -> bytes | None:
    try:
        return store._read_path(path)
    except TaskPlanFailure:
        return None


def read_archive_failure(
    store: SerenaMemoryStore, source: Path, target: Path
) -> tuple[bytes | None, bytes | None]:
    try:
        target_bytes = store._read_path(target)
        source_bytes = store._read_path(source)
    except TaskPlanFailure:
        target_bytes = None
        source_bytes = None
    return source_bytes, target_bytes


def archive_readback(
    store: SerenaMemoryStore, source: Path, target: Path, expected: bytes
) -> tuple[str, bytes | None]:
    actual = store._read_path(target)
    if actual == expected and store._read_path(source) is None:
        return "archived", actual
    return "uncertain", actual


def archive_failure_status(
    source_bytes: bytes | None, target_bytes: bytes | None, expected: bytes
) -> tuple[str, bytes | None]:
    if source_bytes != expected and target_bytes is None:
        return "conflict", source_bytes
    if source_bytes == expected and target_bytes is None:
        return "unavailable", source_bytes
    return "uncertain", target_bytes


def write(
    store: SerenaMemoryStore, plan_id: str, expected: bytes | None, content: bytes
) -> tuple[str, bytes | None]:
    if len(content) > MAX_PLAN_BYTES:
        return "plan_too_large", None
    path = store._canonical_path(plan_id, False, create_parent=True)
    effect_started = False
    try:
        current = store._read_path(path)
        if current != expected:
            return "conflict", current
        descriptor, temporary = tempfile.mkstemp(prefix=".task-plan-", dir=path.parent)
        temp_path = Path(temporary)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            store._check_namespace(path)
            latest = store._read_path(path)
            if latest != expected:
                return "conflict", latest
            if expected is None:
                try:
                    effect_started = True
                    os.link(temp_path, path, follow_symlinks=False)
                except FileExistsError:
                    effect_started = False
                    return "conflict", store._read_path(path)
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
            _discard_plan_temporary(temp_path)
        actual = store._read_path(path)
        if actual == content:
            return "written", actual
        return "uncertain", actual
    except TaskPlanFailure:
        if not effect_started:
            raise
        actual = store._read_after_failure(path)
        return "uncertain", actual
    except OSError:
        actual = store._read_after_failure(path)
        return _failed_plan_write_status(actual, expected, content), actual


def archive_links_match(
    store: SerenaMemoryStore,
    source: Path,
    target: Path,
    source_stat: os.stat_result,
    expected: bytes,
) -> bool:
    linked_source = source.lstat()
    linked_target = target.lstat()
    if (linked_source.st_dev, linked_source.st_ino) != (
        source_stat.st_dev,
        source_stat.st_ino,
    ) or (linked_target.st_dev, linked_target.st_ino) != (
        source_stat.st_dev,
        source_stat.st_ino,
    ):
        return False
    if store._read_path(target) != expected or store._read_path(source) != expected:
        return False
    return True


def archive(store: SerenaMemoryStore, plan_id: str, expected: bytes) -> tuple[str, bytes | None]:
    store._assert_current_binding()
    source_name = store._memory_name(plan_id, False)
    target_name = store._memory_name(plan_id, True)
    store._policy(source_name, write=True)
    store._policy(target_name, write=True)
    source = store._canonical_path(plan_id, False, create_parent=False)
    target = store._canonical_path(plan_id, True, create_parent=True)
    effect_started = False
    try:
        source_before = store._read_path(source)
        if source_before != expected:
            return "conflict", source_before
        if store._read_path(target) is not None:
            return "collision", source_before
        source_stat = source.lstat()
        if not stat.S_ISREG(source_stat.st_mode):
            return "unavailable", source_before
        store._check_namespace(source)
        store._check_namespace(target)
        effect_started = True
        os.link(source, target, follow_symlinks=False)
        if not store._archive_links_match(source, target, source_stat, expected):
            return "uncertain", store._read_path(target)
        os.unlink(source)
        for directory in {source.parent, target.parent}:
            dir_fd = os.open(directory, os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        return store._archive_readback(source, target, expected)
    except FileExistsError:
        effect_started = False
        return "collision", store._read_path(source)
    except TaskPlanFailure:
        if not effect_started:
            raise
        target_bytes = store._read_after_failure(target)
        return "uncertain", target_bytes
    except (OSError, TypeError, NotImplementedError):
        source_bytes, target_bytes = store._read_archive_failure(source, target)
        return store._archive_failure_status(source_bytes, target_bytes, expected)

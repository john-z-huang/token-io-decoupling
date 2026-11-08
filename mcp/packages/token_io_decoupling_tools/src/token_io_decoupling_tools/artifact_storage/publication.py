"""具备基线复核和回读检查的文件发布与原子替换。"""

from __future__ import annotations

import errno
import os
import secrets
from typing import TYPE_CHECKING, Literal

from .filesystem import MaterializationStorageError

if TYPE_CHECKING:
    from .service import MaterializationStorage


def publish_project_file(
    store: MaterializationStorage,
    path: str,
    content: bytes,
    *,
    operation: Literal["create", "replace"],
    baseline_state: Literal["absent", "sha256"],
    baseline_sha256: str | None,
    candidate_sha256: str,
    limit: int,
) -> tuple[Literal["applied", "already_identical", "conflict", "uncertain"], str | None]:
    parent_fd, leaf = store.open_project_parent(path)
    try:
        try:
            current, current_mode = store.read_file(parent_fd, leaf, limit=limit)
        except MaterializationStorageError:
            return "conflict", None
        if current is not None and store._sha256(current) == candidate_sha256:
            return "already_identical", candidate_sha256
        if not store._matches_baseline(current, baseline_state, baseline_sha256):
            return "conflict", store._sha256(current) if current is not None else None
        try:
            published = store._atomic_project_write(
                parent_fd,
                leaf,
                content,
                operation=operation,
                baseline_state=baseline_state,
                baseline_sha256=baseline_sha256,
                candidate_sha256=candidate_sha256,
                existing_mode=current_mode,
                limit=limit,
            )
        except MaterializationStorageError as exc:
            if exc.reason == "materialization_write_uncertain":
                return "uncertain", None
            raise
        if not published:
            return "already_identical", candidate_sha256
        try:
            readback, _ = store.read_file(parent_fd, leaf, limit=limit)
        except MaterializationStorageError:
            return "uncertain", None
        if readback is None:
            return "uncertain", None
        actual_hash = store._sha256(readback)
        if actual_hash != candidate_sha256:
            return "uncertain", actual_hash
        return "applied", actual_hash
    finally:
        os.close(parent_fd)


def reconcile_create_collision(
    store: MaterializationStorage,
    parent_fd: int,
    leaf: str,
    candidate_sha256: str,
    limit: int,
    exc: OSError,
) -> bool:
    current, _ = store.read_file(parent_fd, leaf, limit=limit)
    if current is not None and store._sha256(current) == candidate_sha256:
        return False
    raise MaterializationStorageError("materialization_create_target_occupied") from exc


def atomic_project_write(
    store: MaterializationStorage,
    parent_fd: int,
    leaf: str,
    content: bytes,
    *,
    operation: Literal["create", "replace"],
    baseline_state: Literal["absent", "sha256"],
    baseline_sha256: str | None,
    candidate_sha256: str,
    existing_mode: int | None,
    limit: int,
) -> bool:
    temp_name, temp_fd = store._new_temp_file(parent_fd, 0o666 if operation == "create" else 0o600)
    try:
        store._write_all(temp_fd, content)
        if operation == "replace":
            safe_mode = existing_mode if existing_mode is not None else 0o600
            os.fchmod(temp_fd, safe_mode & 0o777)
        os.fsync(temp_fd)
        os.close(temp_fd)
        temp_fd = -1
        current, _ = store.read_file(parent_fd, leaf, limit=limit)
        if current is not None and store._sha256(current) == candidate_sha256:
            return False
        if not store._matches_baseline(current, baseline_state, baseline_sha256):
            raise MaterializationStorageError("materialization_baseline_conflict")
        if operation == "create":
            os.link(
                temp_name,
                leaf,
                src_dir_fd=parent_fd,
                dst_dir_fd=parent_fd,
                follow_symlinks=False,
            )
            os.unlink(temp_name, dir_fd=parent_fd)
        else:
            os.replace(temp_name, leaf, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
        os.fsync(parent_fd)
        return True
    except MaterializationStorageError:
        raise
    except OSError as exc:
        if operation == "create" and exc.errno == errno.EEXIST:
            return store._reconcile_create_collision(parent_fd, leaf, candidate_sha256, limit, exc)
        raise MaterializationStorageError("materialization_write_uncertain") from exc
    finally:
        if temp_fd >= 0:
            os.close(temp_fd)
        try:
            os.unlink(temp_name, dir_fd=parent_fd)
        except OSError:
            pass


def write_once(
    store: MaterializationStorage, directory_fd: int, target: str, content: bytes, mode: int
) -> None:
    temp_name, fd = store._new_temp_file(directory_fd, 0o600)
    try:
        store._write_all(fd, content)
        os.fchmod(fd, mode)
        os.fsync(fd)
        os.close(fd)
        fd = -1
        os.link(
            temp_name,
            target,
            src_dir_fd=directory_fd,
            dst_dir_fd=directory_fd,
            follow_symlinks=False,
        )
        os.unlink(temp_name, dir_fd=directory_fd)
        os.fsync(directory_fd)
    except OSError as exc:
        raise MaterializationStorageError("artifact_write_failed") from exc
    finally:
        if fd >= 0:
            os.close(fd)
        try:
            os.unlink(temp_name, dir_fd=directory_fd)
        except OSError:
            pass


def atomic_replace(
    store: MaterializationStorage, directory_fd: int, target: str, content: bytes, mode: int
) -> None:
    temp_name, fd = store._new_temp_file(directory_fd, 0o600)
    try:
        store._write_all(fd, content)
        os.fchmod(fd, mode)
        os.fsync(fd)
        os.close(fd)
        fd = -1
        os.replace(temp_name, target, src_dir_fd=directory_fd, dst_dir_fd=directory_fd)
        os.fsync(directory_fd)
    except OSError as exc:
        raise MaterializationStorageError("artifact_receipt_write_failed") from exc
    finally:
        if fd >= 0:
            os.close(fd)
        try:
            os.unlink(temp_name, dir_fd=directory_fd)
        except OSError:
            pass


def new_temp_file(directory_fd: int, mode: int) -> tuple[str, int]:
    for _ in range(5):
        name = f".tmp-{secrets.token_hex(16)}"
        try:
            fd = os.open(
                name,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
                mode,
                dir_fd=directory_fd,
            )
            return name, fd
        except FileExistsError:
            continue
    raise MaterializationStorageError("temporary_name_collision")


def write_all(fd: int, content: bytes) -> None:
    view = memoryview(content)
    while view:
        written = os.write(fd, view)
        if written <= 0:
            raise OSError("short_write")
        view = view[written:]

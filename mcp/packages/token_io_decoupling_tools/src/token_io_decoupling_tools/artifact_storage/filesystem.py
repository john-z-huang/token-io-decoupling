"""通过固定目录描述符有界读取项目和候选文件。"""

from __future__ import annotations

import os
import stat
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .service import MaterializationStorage


class MaterializationStorageError(Exception):
    """Sanitized storage failure with a stable reason code."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def read_file(
    store: MaterializationStorage, directory_fd: int, leaf: str, *, limit: int
) -> tuple[bytes | None, int | None]:
    flags = os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
    flags |= getattr(os, "O_NONBLOCK", 0)
    try:
        fd = os.open(leaf, flags, dir_fd=directory_fd)
    except FileNotFoundError:
        return None, None
    except OSError as exc:
        raise MaterializationStorageError("materialization_target_unavailable") from exc
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size > limit:
            raise MaterializationStorageError("materialization_target_not_bounded_regular_file")
        chunks: list[bytes] = []
        remaining = limit + 1
        while remaining > 0:
            chunk = os.read(fd, min(65_536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        content = b"".join(chunks)
        after = os.fstat(fd)
        linked = os.stat(leaf, dir_fd=directory_fd, follow_symlinks=False)
        if (
            len(content) > limit
            or not store._same_file_state(before, after)
            or not store._same_file_state(after, linked)
        ):
            raise MaterializationStorageError("materialization_target_changed_during_read")
        return content, stat.S_IMODE(after.st_mode)
    except OSError as exc:
        raise MaterializationStorageError("materialization_target_unavailable") from exc
    finally:
        os.close(fd)


def read_project_file(store: MaterializationStorage, path: str, *, limit: int) -> bytes | None:
    parent_fd, leaf = store.open_project_parent(path)
    try:
        content, _ = store.read_file(parent_fd, leaf, limit=limit)
        return content
    finally:
        os.close(parent_fd)


def open_project_parent(store: MaterializationStorage, path: str) -> tuple[int, str]:
    parts = path.split("/")
    if not parts or any(part in {"", ".", ".."} for part in parts):
        raise MaterializationStorageError("materialization_path_invalid")
    current_fd = os.dup(store.project_fd)
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
    try:
        for part in parts[:-1]:
            next_fd = os.open(part, flags, dir_fd=current_fd)
            os.close(current_fd)
            current_fd = next_fd
        return current_fd, parts[-1]
    except OSError as exc:
        os.close(current_fd)
        raise MaterializationStorageError("materialization_parent_unavailable") from exc

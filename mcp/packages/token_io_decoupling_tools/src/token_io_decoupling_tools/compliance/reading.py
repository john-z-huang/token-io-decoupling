"""按固定目录描述符读取候选，复核文件及路径身份。"""

from __future__ import annotations

import os
import stat
from dataclasses import dataclass
from typing import TYPE_CHECKING

from token_io_decoupling_core.compliance_core import (
    MAX_BATCH_UTF8_BYTES,
)

if TYPE_CHECKING:
    from .service import CompliancePreflightService


@dataclass(frozen=True)
class _ReadResult:
    state: str
    data: bytes | None = None


def read_target_presence(service: CompliancePreflightService, path: str) -> bool | None:
    read = service._read_relative(path)
    if read.state == "missing":
        result: bool | None = False
    elif read.state == "present" and read.data is not None:
        try:
            read.data.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            result = None
        else:
            result = True
    else:
        result = None
    return result


def oversized_file_result(
    service: CompliancePreflightService, parts: list[str], metadata: os.stat_result
) -> _ReadResult:
    if not service._relative_path_matches(parts, metadata):
        return _ReadResult("unavailable")
    return _ReadResult("present")


def read_candidate_descriptor(
    service: CompliancePreflightService, file_fd: int, parts: list[str]
) -> _ReadResult:
    metadata = os.fstat(file_fd)
    if not stat.S_ISREG(metadata.st_mode):
        return _ReadResult("unavailable")
    if metadata.st_size > MAX_BATCH_UTF8_BYTES:
        return service._oversized_file_result(parts, metadata)
    chunks: list[bytes] = []
    remaining = MAX_BATCH_UTF8_BYTES + 1
    while remaining > 0:
        chunk = os.read(file_fd, min(65_536, remaining))
        if not chunk:
            break
        chunks.append(chunk)
        remaining -= len(chunk)
    data = b"".join(chunks)
    if len(data) > MAX_BATCH_UTF8_BYTES:
        return service._oversized_file_result(parts, metadata)
    after_read = os.fstat(file_fd)
    if not _same_file_state(metadata, after_read):
        return _ReadResult("unavailable")
    if not service._relative_path_matches(parts, after_read):
        return _ReadResult("unavailable")
    return _ReadResult("present", data)


def read_relative(service: CompliancePreflightService, path: str) -> _ReadResult:
    """Read a UTF-8-agnostic bounded file through pinned directory descriptors."""
    if service._closed:
        return _ReadResult("unavailable")
    current_fd = -1
    file_fd = -1
    try:
        parts = path.split("/")
        current_fd = os.dup(service._root_fd)
        directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
        for part in parts[:-1]:
            next_fd = os.open(part, directory_flags, dir_fd=current_fd)
            os.close(current_fd)
            current_fd = next_fd
        file_flags = os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
        file_flags |= getattr(os, "O_NONBLOCK", 0)
        file_fd = os.open(parts[-1], file_flags, dir_fd=current_fd)
        return service._read_candidate_descriptor(file_fd, parts)
    except FileNotFoundError:
        return _ReadResult("missing")
    except (OSError, NotImplementedError, ValueError):
        return _ReadResult("unavailable")
    finally:
        if file_fd >= 0:
            os.close(file_fd)
        if current_fd >= 0:
            os.close(current_fd)


def relative_path_matches(
    service: CompliancePreflightService, parts: list[str], expected: os.stat_result
) -> bool:
    """Re-open the complete path from the pinned root and compare its final inode."""
    current_fd = -1
    probe_fd = -1
    try:
        current_fd = os.dup(service._root_fd)
        directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
        for part in parts[:-1]:
            next_fd = os.open(part, directory_flags, dir_fd=current_fd)
            os.close(current_fd)
            current_fd = next_fd
        file_flags = os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
        file_flags |= getattr(os, "O_NONBLOCK", 0)
        probe_fd = os.open(parts[-1], file_flags, dir_fd=current_fd)
        current = os.fstat(probe_fd)
        return stat.S_ISREG(current.st_mode) and _same_file_state(expected, current)
    except (OSError, NotImplementedError, ValueError):
        return False
    finally:
        if probe_fd >= 0:
            os.close(probe_fd)
        if current_fd >= 0:
            os.close(current_fd)


def _same_file_state(left: os.stat_result, right: os.stat_result) -> bool:
    return (
        left.st_dev == right.st_dev
        and left.st_ino == right.st_ino
        and left.st_mode == right.st_mode
        and left.st_size == right.st_size
        and left.st_mtime_ns == right.st_mtime_ns
        and left.st_ctime_ns == right.st_ctime_ns
    )

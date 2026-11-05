"""Read bounded tails from an explicitly bound Serena Memory store."""

from __future__ import annotations

import codecs
import errno
import importlib
import os
import stat
from collections import deque
from pathlib import Path
from typing import Any

MAX_TAIL_LINES = 10_000
MAX_CONTENT_CHARS = 64_000
MAX_CHANGED_CONTENT_CHARS = 64_000
MAX_MEMORY_PATH_CHARS = 4_096
_MEMORY_REF_PREFIX = "mem:"


class _MemoryReadError(Exception):
    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


class SerenaMemoryReadService:
    """Read a bounded tail from a configured Serena MemoryManager."""

    def __init__(
        self,
        memory_manager: object | None = None,
        project_root: str | Path | None = None,
    ) -> None:
        self._manager = None
        self._project_root: Path | None = None
        self._project_memory_root: Path | None = None
        self._global_memory_root: Path | None = None
        self._encoding = "utf-8"
        self._startup_reason = "serena_memory_backend_not_configured"

        if memory_manager is None and project_root is None:
            return
        if memory_manager is None or project_root is None:
            self._startup_reason = "serena_memory_binding_incomplete"
            return

        try:
            manager_module = importlib.import_module("serena.memories.memory_manager")
        except ImportError:
            self._startup_reason = "serena_memory_manager_unavailable"
            return
        manager_type = getattr(manager_module, "MemoryManager", None)
        if not isinstance(manager_type, type) or not isinstance(memory_manager, manager_type):
            self._startup_reason = "serena_memory_manager_required"
            return
        if not callable(getattr(memory_manager, "_sanitize_name", None)) or not callable(
            getattr(memory_manager, "_check_not_ignored", None)
        ):
            self._startup_reason = "serena_memory_manager_interface_unsupported"
            return

        project_path = Path(project_root)
        if not project_path.is_absolute():
            self._startup_reason = "project_root_must_be_absolute"
            return
        try:
            project_path = project_path.resolve(strict=True)
            if not project_path.is_dir():
                self._startup_reason = "project_root_unavailable"
                return
        except OSError:
            self._startup_reason = "project_root_unavailable"
            return

        project_root_value = getattr(memory_manager, "_project_memory_dir", None)
        global_root_value = getattr(memory_manager, "_global_memory_dir", None)
        project_memory_root = self._validated_directory_root(project_root_value)
        global_memory_root = self._validated_directory_root(global_root_value)
        if project_root_value is not None and project_memory_root is None:
            self._startup_reason = "serena_project_memory_root_invalid"
            return
        if global_memory_root is None:
            self._startup_reason = "serena_global_memory_root_invalid"
            return

        encoding = getattr(memory_manager, "_encoding", None)
        if not isinstance(encoding, str) or not encoding:
            self._startup_reason = "serena_memory_encoding_unavailable"
            return
        try:
            codecs.lookup(encoding)
        except LookupError:
            self._startup_reason = "serena_memory_encoding_unsupported"
            return

        self._manager = memory_manager
        self._project_root = project_path
        self._project_memory_root = project_memory_root
        self._global_memory_root = global_memory_root
        self._encoding = encoding
        self._startup_reason = "explicit_serena_memory_manager_injected"

    @staticmethod
    def _secure_open_available() -> bool:
        return (
            hasattr(os, "O_NOFOLLOW")
            and hasattr(os, "O_DIRECTORY")
            and hasattr(os, "supports_dir_fd")
            and os.open in os.supports_dir_fd
            and os.stat in os.supports_dir_fd
            and os.stat in getattr(os, "supports_follow_symlinks", set())
        )

    @staticmethod
    def _validated_directory_root(value: object) -> Path | None:
        if not isinstance(value, (str, Path)):
            return None
        path = Path(value)
        if not path.is_absolute():
            return None
        try:
            mode = path.lstat().st_mode
            if stat.S_ISLNK(mode) or not stat.S_ISDIR(mode):
                return None
            resolved = path.resolve(strict=True)
            if resolved != path:
                return None
            return resolved
        except OSError:
            return None

    def capability(self) -> dict[str, Any]:
        status = "configured" if self._manager is not None else "unavailable"
        reason = (
            "secure_local_file_read_available"
            if self._secure_open_available()
            else "secure_dirfd_open_unsupported"
        )
        if self._manager is None:
            reason = self._startup_reason
        elif not self._secure_open_available():
            status = "unavailable"
        return {
            "status": status,
            "reason_code": reason,
            "project_root": str(self._project_root) if self._project_root else None,
            "project_memory_root": str(self._project_memory_root)
            if self._project_memory_root
            else None,
            "global_memory_root": str(self._global_memory_root)
            if self._global_memory_root
            else None,
            "encoding": self._encoding if self._manager is not None else None,
            "max_tail_lines": MAX_TAIL_LINES,
            "max_content_chars": MAX_CONTENT_CHARS,
        }

    def _binding_is_current(self) -> str | None:
        if self._manager is None or self._project_root is None:
            return self._startup_reason
        if not self._secure_open_available():
            return "secure_dirfd_open_unsupported"
        if getattr(self._manager, "_encoding", None) != self._encoding:
            return "serena_memory_encoding_binding_changed"
        try:
            if self._project_root.resolve(strict=True) != self._project_root:
                return "project_root_binding_changed"
            for attribute, expected in (
                ("_project_memory_dir", self._project_memory_root),
                ("_global_memory_dir", self._global_memory_root),
            ):
                value = getattr(self._manager, attribute, None)
                if expected is None:
                    if value is not None:
                        return "serena_memory_root_binding_changed"
                    continue
                current = self._validated_directory_root(value)
                if current != expected:
                    return "serena_memory_root_binding_changed"
        except OSError:
            return "serena_memory_root_unavailable"
        return None

    def _normalize_name(self, value: str) -> str:
        assert self._manager is not None
        name = self._manager._sanitize_name(value)
        if not isinstance(name, str) or not name:
            raise _MemoryReadError("memory_name_invalid")
        parts = name.split("/")
        if os.path.isabs(name) or any(part in {"", ".", ".."} for part in parts) or "\\" in name:
            raise _MemoryReadError("memory_path_invalid")
        return name

    def _resolve_memory(self, memory_path: str) -> tuple[str, Path, tuple[str, ...]]:
        if not isinstance(memory_path, str) or not memory_path.strip():
            raise _MemoryReadError("memory_path_invalid")
        if len(memory_path) > MAX_MEMORY_PATH_CHARS:
            raise _MemoryReadError("memory_path_too_large")
        raw = memory_path
        if raw.startswith(_MEMORY_REF_PREFIX):
            name = self._normalize_name(raw)
            global_scope = name == "global" or name.startswith("global/")
            root = self._global_memory_root if global_scope else self._project_memory_root
            if root is None or name == "global":
                raise _MemoryReadError("memory_scope_unavailable_or_invalid")
            relative_name = name[len("global/") :] if global_scope else name
            parts = tuple(relative_name.split("/"))
            parts = (*parts[:-1], parts[-1] + ".md")
            return name, root, parts

        raw_path = Path(raw)
        roots = (
            (self._project_memory_root, False),
            (self._global_memory_root, True),
        )
        if raw_path.is_absolute():
            candidate = raw_path
        else:
            assert self._project_root is not None
            if any(part in {"..", "."} for part in raw_path.parts):
                raise _MemoryReadError("memory_path_invalid")
            candidate = self._project_root / raw_path
        for root, global_scope in roots:
            if root is None:
                continue
            try:
                relative = candidate.relative_to(root)
            except ValueError:
                continue
            if not relative.parts or any(part in {"", ".", ".."} for part in relative.parts):
                raise _MemoryReadError("memory_path_invalid")
            if relative.suffix != ".md":
                raise _MemoryReadError("memory_path_not_markdown")
            logical = relative.with_suffix("").as_posix()
            name = "/".join((*(("global",) if global_scope else ()), logical))
            return name, root, relative.parts
        if raw_path.is_absolute():
            raise _MemoryReadError("memory_path_outside_memory_roots")

        # Relative names outside the configured project tree remain Serena logical names.
        name = self._normalize_name(raw)
        global_scope = name == "global" or name.startswith("global/")
        root = self._global_memory_root if global_scope else self._project_memory_root
        if root is None or name == "global":
            raise _MemoryReadError("memory_scope_unavailable_or_invalid")
        relative_name = name[len("global/") :] if global_scope else name
        parts = tuple(relative_name.split("/"))
        parts = (*parts[:-1], parts[-1] + ".md")
        return name, root, parts

    @staticmethod
    def _same_file_state(left: os.stat_result, right: os.stat_result) -> bool:
        return (
            left.st_dev,
            left.st_ino,
            left.st_mode,
            left.st_size,
            left.st_mtime_ns,
            left.st_ctime_ns,
        ) == (
            right.st_dev,
            right.st_ino,
            right.st_mode,
            right.st_size,
            right.st_mtime_ns,
            right.st_ctime_ns,
        )

    @staticmethod
    def _open_absolute_directory(path: Path) -> int:
        if not path.is_absolute() or any(part in {".", ".."} for part in path.parts[1:]):
            raise _MemoryReadError("memory_path_invalid")
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
        current_fd = os.open("/", flags)
        try:
            for part in path.parts[1:]:
                next_fd = os.open(part, flags, dir_fd=current_fd)
                os.close(current_fd)
                current_fd = next_fd
            return current_fd
        except OSError as exc:
            os.close(current_fd)
            reason = (
                "memory_symlink_or_directory_rejected"
                if exc.errno in {errno.ELOOP, errno.ENOTDIR}
                else "memory_path_unavailable"
            )
            raise _MemoryReadError(reason) from exc

    @staticmethod
    def _open_parent_directory(root_fd: int, parts: tuple[str, ...]) -> int:
        directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
        current_fd = os.dup(root_fd)
        try:
            for part in parts:
                next_fd = os.open(part, directory_flags, dir_fd=current_fd)
                os.close(current_fd)
                current_fd = next_fd
            return current_fd
        except OSError as exc:
            os.close(current_fd)
            reason = (
                "memory_symlink_or_directory_rejected"
                if exc.errno in {errno.ELOOP, errno.ENOTDIR}
                else "memory_path_unavailable"
            )
            raise _MemoryReadError(reason) from exc

    def _read_tail(
        self, root: Path, parts: tuple[str, ...], tail_lines: int
    ) -> tuple[str, int, int, int | None, int | None, bool]:
        assert self._manager is not None
        root_fd = self._open_absolute_directory(root)
        parent_fd: int | None = None
        file_fd: int | None = None
        try:
            parent_fd = self._open_parent_directory(root_fd, parts[:-1])
            file_flags = (
                os.O_RDONLY
                | os.O_NOFOLLOW
                | getattr(os, "O_CLOEXEC", 0)
                | getattr(os, "O_NONBLOCK", 0)
            )
            file_fd = os.open(parts[-1], file_flags, dir_fd=parent_fd)
            before = os.fstat(file_fd)
            if not stat.S_ISREG(before.st_mode):
                raise _MemoryReadError("memory_file_not_regular")

            decoder = codecs.getincrementaldecoder(self._encoding)(errors="strict")
            line_window: deque[tuple[int, int, int]] = deque(maxlen=tail_lines or 1)
            tail_buffer = ""
            total_chars = 0
            total_lines = 0
            current_line_start = 0
            last_character = ""

            def consume_text(text: str) -> None:
                nonlocal tail_buffer, total_chars, total_lines, current_line_start, last_character
                if not text:
                    return
                last_character = text[-1]
                tail_buffer = (tail_buffer + text)[-(MAX_CONTENT_CHARS + 65_536) :]
                cursor = 0
                while True:
                    newline = text.find("\n", cursor)
                    if newline < 0:
                        break
                    line_end = total_chars + newline + 1
                    total_lines += 1
                    if tail_lines > 0:
                        line_window.append((total_lines, current_line_start, line_end))
                    current_line_start = line_end
                    cursor = newline + 1
                total_chars += len(text)

            while True:
                chunk = os.read(file_fd, 65_536)
                if not chunk:
                    break
                consume_text(decoder.decode(chunk, final=False))
            consume_text(decoder.decode(b"", final=True))
            if total_chars > current_line_start:
                total_lines += 1
                if tail_lines > 0:
                    line_window.append((total_lines, current_line_start, total_chars))

            after = os.fstat(file_fd)
            linked = os.stat(parts[-1], dir_fd=parent_fd, follow_symlinks=False)
            absolute_path = root.joinpath(*parts)
            try:
                by_path = os.stat(absolute_path, follow_symlinks=False)
            except OSError as exc:
                raise _MemoryReadError("memory_changed_during_read") from exc
            root_after = os.stat(root, follow_symlinks=False)
            root_opened = os.fstat(root_fd)
            current_parent_fd = self._open_parent_directory(root_fd, parts[:-1])
            try:
                parent_unchanged = self._same_file_state(
                    os.fstat(parent_fd), os.fstat(current_parent_fd)
                )
            finally:
                os.close(current_parent_fd)
            if (
                not self._same_file_state(before, after)
                or not self._same_file_state(after, linked)
                or not self._same_file_state(after, by_path)
                or not self._same_file_state(root_opened, root_after)
                or not parent_unchanged
            ):
                raise _MemoryReadError("memory_changed_during_read")

            if tail_lines == 0:
                return "", total_lines, 0, None, None, last_character == "\n"
            if not line_window:
                return "", total_lines, 0, None, None, last_character == "\n"
            first_line = line_window[0]
            last_line = line_window[-1]
            start_offset = first_line[1]
            end_offset = last_line[2]
            returned_chars = end_offset - start_offset
            buffer_start = total_chars - len(tail_buffer)
            if returned_chars > MAX_CONTENT_CHARS or start_offset < buffer_start:
                raise _MemoryReadError("memory_tail_too_large")
            content = tail_buffer[start_offset - buffer_start : end_offset - buffer_start]
            returned_lines = len(line_window)
            start_line = first_line[0]
            end_line = last_line[0]
            return (
                content,
                total_lines,
                returned_lines,
                start_line,
                end_line,
                last_character == "\n",
            )
        except UnicodeError as exc:
            raise _MemoryReadError("memory_encoding_invalid") from exc
        except OSError as exc:
            if exc.errno in {errno.ELOOP, errno.ENOTDIR}:
                reason = "memory_symlink_or_directory_rejected"
            elif exc.errno == 2:
                reason = "memory_not_found"
            else:
                reason = "memory_read_failed"
            raise _MemoryReadError(reason) from exc
        finally:
            if file_fd is not None:
                os.close(file_fd)
            if parent_fd is not None:
                os.close(parent_fd)
            os.close(root_fd)

    def tail_read(self, memory_path: str, tail_lines: int) -> dict[str, Any]:
        if (
            isinstance(tail_lines, bool)
            or not isinstance(tail_lines, int)
            or not 0 <= tail_lines <= MAX_TAIL_LINES
        ):
            return self._failure("tail_lines_invalid")
        binding_error = self._binding_is_current()
        if binding_error:
            return self._failure(binding_error)
        try:
            memory_name, root, parts = self._resolve_memory(memory_path)
            assert self._manager is not None
            self._manager._check_not_ignored(memory_name)
            content, total, returned, start, end, ends_with_newline = self._read_tail(
                root, parts, tail_lines
            )
            binding_error = self._binding_is_current()
            if binding_error:
                return self._failure(binding_error)
            self._manager._check_not_ignored(memory_name)
            path = root.joinpath(*parts)
            return {
                "status": "available",
                "reason": "memory_tail_read",
                "reason_code": "memory_tail_read",
                "memory_name": memory_name,
                "resolved_path": str(path),
                "requested_tail_lines": tail_lines,
                "total_lines": total,
                "returned_lines": returned,
                "start_line": start,
                "end_line": end,
                "ends_with_newline": ends_with_newline,
                "content": content,
                "line_semantics": (
                    "LF/CRLF-delimited; no phantom line after final newline; 1-based bounds"
                ),
            }
        except _MemoryReadError as exc:
            return self._failure(exc.reason)
        except (OSError, ValueError, PermissionError) as exc:
            reason = (
                "memory_ignored_or_invalid" if isinstance(exc, ValueError) else "memory_read_failed"
            )
            return self._failure(reason)

    def write_check(
        self, memory_path: str, changed_content: str, tail_lines: int
    ) -> dict[str, Any]:
        if not isinstance(changed_content, str) or not changed_content:
            return self._check_failure("changed_content_invalid")
        if len(changed_content) > MAX_CHANGED_CONTENT_CHARS:
            return self._check_failure("changed_content_too_large")
        result = self.tail_read(memory_path, tail_lines)
        if result.get("status") != "available":
            return self._check_failure(str(result.get("reason_code", "memory_read_failed")))
        content = result["content"]
        position = content.find(changed_content)
        return {
            "status": "available",
            "reason": "memory_tail_match" if position >= 0 else "memory_tail_no_match",
            "reason_code": "memory_tail_match" if position >= 0 else "memory_tail_no_match",
            "success": position >= 0,
            "memory_name": result["memory_name"],
            "requested_tail_lines": result["requested_tail_lines"],
            "total_lines": result["total_lines"],
            "returned_lines": result["returned_lines"],
            "match_start": position if position >= 0 else None,
            "match_end": position + len(changed_content) if position >= 0 else None,
            "match_scope": "current_tail_content_only",
        }

    @staticmethod
    def _failure(reason: str) -> dict[str, Any]:
        return {
            "status": "unavailable",
            "reason": reason,
            "reason_code": reason,
            "content": "",
        }

    @staticmethod
    def _check_failure(reason: str) -> dict[str, Any]:
        return {
            "status": "unavailable",
            "reason": reason,
            "reason_code": reason,
            "success": False,
        }

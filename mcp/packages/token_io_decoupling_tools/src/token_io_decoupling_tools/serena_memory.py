"""Read-only access to the current project's local Serena Memory files."""

from __future__ import annotations

from collections import deque
from pathlib import Path, PureWindowsPath
from typing import Any

MAX_TAIL_LINES = 10_000
MAX_CONTENT_CHARS = 64_000
MAX_CHANGED_CONTENT_CHARS = 64_000
MAX_MEMORY_PATH_CHARS = 2_048
_MEMORY_REF_PREFIX = "mem:"


class _MemoryReadError(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class SerenaMemoryReadService:
    """Read bounded Memory tails under ``<startup cwd>/.serena/memories``."""

    def __init__(self, cwd: str | Path | None = None) -> None:
        self._project_root: Path | None = None
        self._memory_root: Path | None = None
        self._startup_reason = "serena_project_memory_directory_unavailable"
        try:
            project = Path.cwd() if cwd is None else Path(cwd)
            project = project.resolve(strict=True)
            if not project.is_dir():
                self._startup_reason = "project_root_unavailable"
                return
            self._project_root = project
            metadata = project / ".serena"
            memory_root = metadata / "memories"
            if metadata.is_symlink() or memory_root.is_symlink():
                self._startup_reason = "serena_project_memory_root_invalid"
                return
            if not metadata.is_dir() or not memory_root.is_dir():
                return
            self._memory_root = memory_root.resolve(strict=True)
            self._startup_reason = "secure_local_file_read_available"
        except (OSError, RuntimeError):
            self._startup_reason = "project_root_unavailable"

    def capability(self) -> dict[str, Any]:
        configured = self._project_root is not None and self._memory_root is not None
        return {
            "status": "configured" if configured else "unavailable",
            "reason_code": self._startup_reason,
            "project_root": str(self._project_root) if self._project_root else None,
            "project_memory_root": str(self._memory_root) if self._memory_root else None,
            "global_memory_root": None,
            "encoding": "utf-8",
            "max_tail_lines": MAX_TAIL_LINES,
            "max_content_chars": MAX_CONTENT_CHARS,
        }

    def _resolve_memory(self, memory_path: str) -> tuple[str, Path]:
        if not isinstance(memory_path, str) or not memory_path.strip():
            raise _MemoryReadError("memory_path_invalid")
        if len(memory_path) > MAX_MEMORY_PATH_CHARS:
            raise _MemoryReadError("memory_path_too_large")
        name = memory_path.strip()
        if name.startswith(_MEMORY_REF_PREFIX):
            name = name[len(_MEMORY_REF_PREFIX) :]
        if (
            not name
            or name == "global"
            or name.startswith("global/")
            or name.startswith("/")
            or "\\" in name
            or PureWindowsPath(name).is_absolute()
            or PureWindowsPath(name).drive
        ):
            raise _MemoryReadError("memory_path_invalid")
        parts = name.split("/")
        if any(part in {"", ".", ".."} or ":" in part for part in parts):
            raise _MemoryReadError("memory_path_invalid")
        if parts[-1].endswith(".md"):
            parts[-1] = parts[-1][:-3]
        if not parts[-1]:
            raise _MemoryReadError("memory_path_invalid")
        assert self._memory_root is not None
        candidate = self._memory_root.joinpath(*parts[:-1], parts[-1] + ".md")
        try:
            relative = candidate.relative_to(self._memory_root)
        except ValueError as exc:
            raise _MemoryReadError("memory_path_outside_project_memory") from exc
        if not relative.parts:
            raise _MemoryReadError("memory_path_invalid")
        return "/".join(parts), candidate

    def _verify_memory_hierarchy(self, path: Path) -> None:
        # Check each component before resolving so a symlink cannot redirect the read.
        assert self._memory_root is not None
        current = self._memory_root
        assert self._project_root is not None
        lexical_root = self._project_root / ".serena" / "memories"
        metadata = self._project_root / ".serena"
        if metadata.is_symlink() or lexical_root.is_symlink():
            raise _MemoryReadError("memory_symlink_rejected")
        try:
            if lexical_root.resolve(strict=True) != self._memory_root:
                raise _MemoryReadError("memory_root_changed")
        except (OSError, RuntimeError) as exc:
            raise _MemoryReadError("memory_root_changed") from exc
        if current.is_symlink():
            raise _MemoryReadError("memory_symlink_rejected")
        for part in path.relative_to(current).parts:
            current = current / part
            if current.is_symlink():
                raise _MemoryReadError("memory_symlink_rejected")

    @staticmethod
    def _read_memory_lines(path: Path, tail_lines: int) -> tuple[deque[str], int, str]:
        with path.open("r", encoding="utf-8", newline="") as stream:
            lines: deque[str] = deque(maxlen=tail_lines)
            total_lines = 0
            last_ending = ""
            if tail_lines == 0:
                for line in stream:
                    total_lines += 1
                    last_ending = line[-1:] if line else ""
            else:
                for line in stream:
                    total_lines += 1
                    lines.append(line)
                    last_ending = line[-1:] if line else ""
        return lines, total_lines, last_ending

    def _read_tail(
        self, memory_path: str, tail_lines: int
    ) -> tuple[str, Path, str, int, int, int | None, int | None, bool]:
        if self._memory_root is None:
            raise _MemoryReadError(self._startup_reason)
        memory_name, path = self._resolve_memory(memory_path)
        self._verify_memory_hierarchy(path)
        try:
            root = self._memory_root.resolve(strict=True)
            resolved = path.resolve(strict=True)
            resolved.relative_to(root)
            if not path.is_file():
                raise _MemoryReadError("memory_file_not_regular")
            lines, total_lines, last_ending = self._read_memory_lines(path, tail_lines)
        except _MemoryReadError:
            raise
        except FileNotFoundError as exc:
            raise _MemoryReadError("memory_not_found") from exc
        except UnicodeError as exc:
            raise _MemoryReadError("memory_encoding_invalid") from exc
        except (OSError, RuntimeError, ValueError) as exc:
            raise _MemoryReadError("memory_read_failed") from exc
        selected = list(lines)
        content = "".join(selected)
        if len(content) > MAX_CONTENT_CHARS:
            raise _MemoryReadError("memory_tail_too_large")
        returned_lines = len(selected)
        start_line = total_lines - returned_lines + 1 if returned_lines else None
        end_line = total_lines if returned_lines else None
        return (
            memory_name,
            path,
            content,
            total_lines,
            returned_lines,
            start_line,
            end_line,
            last_ending in {"\n", "\r"},
        )

    def tail_read(self, memory_path: str, tail_lines: int) -> dict[str, Any]:
        if (
            isinstance(tail_lines, bool)
            or not isinstance(tail_lines, int)
            or not 0 <= tail_lines <= MAX_TAIL_LINES
        ):
            return self._failure("tail_lines_invalid")
        try:
            name, path, content, total, returned, start, end, ends_with_newline = self._read_tail(
                memory_path, tail_lines
            )
            return {
                "status": "available",
                "reason": "memory_tail_read",
                "reason_code": "memory_tail_read",
                "memory_name": name,
                "resolved_path": str(path),
                "requested_tail_lines": tail_lines,
                "total_lines": total,
                "returned_lines": returned,
                "start_line": start,
                "end_line": end,
                "ends_with_newline": ends_with_newline,
                "content": content,
                "line_semantics": "Python text iteration; 1-based bounds; no phantom final line",
            }
        except _MemoryReadError as exc:
            return self._failure(exc.reason)

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
        position = result["content"].find(changed_content)
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

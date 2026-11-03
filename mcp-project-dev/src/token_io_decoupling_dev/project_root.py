"""Pin the configured project root and verify its fixed development markers."""

from __future__ import annotations

import os
import stat
import tomllib
from dataclasses import dataclass
from pathlib import Path

from .compiler import CompileError, _source_path, load_json_strict

OWNER_SOURCE = "mcp/packages/token_io_decoupling_core/src/token_io_decoupling_core/owner_paths.py"


@dataclass(frozen=True)
class PinnedProjectRoot:
    path: Path
    device: int
    inode: int

    @classmethod
    def open(cls, candidate: Path) -> PinnedProjectRoot:
        if not candidate.is_absolute():
            raise CompileError("project root must be an absolute path")
        try:
            path = candidate.resolve(strict=True)
            info = path.stat()
            if not stat.S_ISDIR(info.st_mode):
                raise CompileError("project root must be a directory")
            marker = _source_path(path, "mcp-project-dev/pyproject.toml")
            project = tomllib.loads(marker.read_text(encoding="utf-8")).get("project", {})
            if not isinstance(project, dict) or project.get("name") != "token-io-decoupling-dev":
                raise CompileError("project root does not contain the expected development marker")
            for relative, field, expected in (
                ("mcp/rule-registry.json", "contract_version", 2),
                ("mcp/rule-context-index.json", "schema_version", 1),
            ):
                value = load_json_strict(_source_path(path, relative))
                if (
                    not isinstance(value, dict)
                    or type(value.get(field)) is not int
                    or value[field] != expected
                ):
                    raise CompileError(f"unsupported project source version: {relative}")
            _source_path(path, OWNER_SOURCE)
        except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
            raise CompileError("project root or fixed development inputs are unavailable") from exc
        return cls(path, info.st_dev, info.st_ino)

    @property
    def identity(self) -> tuple[int, int]:
        return self.device, self.inode

    def verify(self) -> None:
        try:
            info = os.stat(self.path, follow_symlinks=False)
        except OSError as exc:
            raise CompileError("pinned project root is unavailable") from exc
        if not stat.S_ISDIR(info.st_mode) or (info.st_dev, info.st_ino) != self.identity:
            raise CompileError("pinned project root identity changed")

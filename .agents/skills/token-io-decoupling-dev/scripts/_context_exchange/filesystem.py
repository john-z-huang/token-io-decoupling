"""安全检查 Context Exchange 目录与来源路径，读取 Git 状态。"""

from __future__ import annotations

import os
import re
import stat
import subprocess
from pathlib import Path, PurePosixPath


def run_git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        check=False,
        text=True,
        capture_output=True,
    )


def git_output(root: Path, *args: str) -> str:
    result = run_git(root, *args)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout


def lstat_existing(path: Path, errors: list[str], label: str) -> os.stat_result | None:
    try:
        return path.lstat()
    except FileNotFoundError:
        return None
    except OSError as exc:
        errors.append(f"unable to inspect {label}: {exc}")
        return None


def is_symlink(mode: int) -> bool:
    return stat.S_ISLNK(mode)


def safe_source_path(root: Path, source: str, errors: list[str]) -> Path | None:
    """Return a repository-contained source path after lstat validation."""

    source = source.strip()
    if (
        not source
        or "\x00" in source
        or source.startswith(("/", "\\"))
        or re.match(r"^[A-Za-z]:", source)
    ):
        errors.append(f"source path must be repository-relative: {source or '<empty>'}")
        return None
    pure_source = PurePosixPath(source)
    if pure_source.is_absolute() or ".." in pure_source.parts or "\\" in source:
        errors.append(f"source path must not be absolute or contain parent traversal: {source}")
        return None

    candidate = root.joinpath(*pure_source.parts)
    root_real = root.resolve()
    current = root
    for part in pure_source.parts:
        current = current / part
        state = lstat_existing(current, errors, f"source path {source}")
        if state is None:
            return candidate
        if is_symlink(state.st_mode):
            errors.append(f"source path must not contain a symlink: {source}")
            return None

    try:
        candidate.resolve(strict=False).relative_to(root_real)
    except ValueError:
        errors.append(f"source path escapes the repository: {source}")
        return None

    final_state = lstat_existing(candidate, errors, f"source path {source}")
    if final_state is not None and not stat.S_ISREG(final_state.st_mode):
        errors.append(f"source path must be a regular file: {source}")
        return None
    return candidate

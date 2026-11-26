"""Shared bounded discovery of maintained Markdown files."""

from __future__ import annotations

import os
from pathlib import Path

_PRUNED_DIRECTORY_NAMES = frozenset(
    {
        ".cache",
        ".git",
        ".hypothesis",
        ".mypy_cache",
        ".nox",
        ".pytest_cache",
        ".ruff_cache",
        ".serena",
        ".tox",
        ".ty_cache",
        ".venv",
        "__pycache__",
        "build",
        "dist",
        "node_modules",
        "site-packages",
        "vendor",
        "venv",
    }
)


def discover_markdown(root: Path) -> list[Path]:
    """Return sorted maintained Markdown paths, including the compiled Skill.

    The returned paths are absolute when ``root`` is absolute and are never
    followed through directory or file symlinks. Retired source trees, build
    caches, and dependency directories are outside the maintained document set.
    """
    root = root.absolute()
    if not root.is_dir():
        raise NotADirectoryError(root)

    discovered: list[Path] = []
    for directory, child_directories, filenames in os.walk(root, topdown=True, followlinks=False):
        current = Path(directory)
        environment_marker = current / "pyvenv.cfg"
        if environment_marker.is_file() and not environment_marker.is_symlink():
            child_directories.clear()
            continue
        relative = current.relative_to(root).as_posix()
        child_directories[:] = sorted(
            name
            for name in child_directories
            if name not in _PRUNED_DIRECTORY_NAMES
            and not (current / name).is_symlink()
            and (relative != "." or name != "archive")
        )
        for filename in filenames:
            if not filename.endswith(".md") or "_NOT_USE_" in filename:
                continue
            candidate = current / filename
            if not candidate.is_symlink():
                discovered.append(candidate)

    return sorted(discovered, key=lambda path: path.relative_to(root).as_posix())

"""Derive a stable project key from local Git metadata without invoking Git."""

from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path


class ProjectIdentityError(ValueError):
    """The supplied repository metadata is absent, malformed, or unsafe."""


_GITDIR_LINE = re.compile(r"^gitdir:\s*(.+?)\s*$", re.IGNORECASE)


def _reject_symlink_components(path: Path) -> None:
    absolute = Path(os.path.abspath(path))
    parts = absolute.parts
    current = Path(parts[0])
    for part in parts[1:]:
        current /= part
        try:
            if current.is_symlink():
                raise ProjectIdentityError("repository identity path contains a symlink")
        except OSError as exc:
            raise ProjectIdentityError("repository identity path cannot be inspected") from exc


def project_id_from_git_common_dir(
    repository: Path | str, *, trusted_association: str | None = None
) -> str:
    """Return ``git-<sha256>`` shared by worktrees, distinct across separate clones.

    ``repository`` is an internal trusted-host input. It is never accepted from an MCP
    request. All path components used to locate the Git common directory are checked
    without resolving through symlinks.
    """
    root = Path(os.path.abspath(repository))
    _reject_symlink_components(root)
    if not root.is_dir():
        raise ProjectIdentityError("repository root is unavailable")
    marker = root / ".git"
    try:
        if marker.is_dir() and not marker.is_symlink():
            git_dir = marker
        elif marker.is_file() and not marker.is_symlink():
            match = _GITDIR_LINE.fullmatch(marker.read_text(encoding="utf-8").strip())
            if match is None:
                raise ProjectIdentityError("worktree .git marker is malformed")
            git_dir = Path(match.group(1))
            if not git_dir.is_absolute():
                git_dir = root / git_dir
        else:
            raise ProjectIdentityError("repository has no regular .git metadata")
        git_dir = Path(os.path.abspath(git_dir))
        _reject_symlink_components(git_dir)
        if not git_dir.is_dir():
            raise ProjectIdentityError("Git directory is unavailable")
        common_file = git_dir / "commondir"
        has_commondir = common_file.exists()
        if has_commondir:
            if common_file.is_symlink() or not common_file.is_file():
                raise ProjectIdentityError("Git commondir metadata is unsafe")
            common_value = common_file.read_text(encoding="utf-8").strip()
            if not common_value:
                raise ProjectIdentityError("Git commondir metadata is empty")
            common_dir = Path(common_value)
            if not common_dir.is_absolute():
                common_dir = git_dir / common_dir
        else:
            common_dir = git_dir
        common_dir = Path(os.path.abspath(common_dir))
        _reject_symlink_components(common_dir)
        if not common_dir.is_dir():
            raise ProjectIdentityError("Git common directory is unavailable")
        if has_commondir and not (
            git_dir.parent.name == "worktrees" and common_dir == git_dir.parent.parent
        ):
            raise ProjectIdentityError("Git common directory is outside its worktree metadata")
    except OSError as exc:
        raise ProjectIdentityError("Git metadata cannot be read safely") from exc
    if trusted_association is not None:
        association = trusted_association.strip()
        if not association:
            raise ProjectIdentityError("trusted project association is empty")
        digest = hashlib.sha256(association.encode("utf-8")).hexdigest()
        return f"association-{digest}"
    digest = hashlib.sha256(os.fsencode(common_dir)).hexdigest()
    return f"git-{digest}"

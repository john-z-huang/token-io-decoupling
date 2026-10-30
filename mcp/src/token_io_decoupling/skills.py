"""Install versioned Skill snapshots without touching legacy project checkouts."""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import tempfile
import zipfile
from importlib.metadata import version
from importlib.resources import files
from pathlib import Path, PurePosixPath

DEFAULT_NAME = "token-io-decoupling-skill"
LEGACY_NAME = "token-io-decoupling"
MARKER = ".token-io-skill.json"


def _fingerprints(root: Path) -> dict[str, str]:
    result = {}
    for path in root.rglob("*"):
        if path.is_symlink():
            raise ValueError("symbolic links are not managed Skill files")
        if path.is_file() and path != root / MARKER:
            result[path.relative_to(root).as_posix()] = hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
    return result


def install_skill(*, name: str = DEFAULT_NAME, update: bool = False) -> Path:
    """Publish only within the user's skills root; never accept an arbitrary destination."""
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name) or name == LEGACY_NAME:
        raise ValueError("choose a new lower-case Skill name; the legacy name is protected")
    home = Path.home()
    root = home / ".agents/skills"
    legacy = root / LEGACY_NAME
    target = root / name
    # Reject redirected roots too: do not write through a skills-root symlink into a checkout.
    for path in (home / ".agents", root, target):
        if path.is_symlink():
            raise ValueError("symbolic links in the installation path are refused")
    resolved = target.resolve()
    old = legacy.resolve()
    if resolved == old or resolved.is_relative_to(old) or old.is_relative_to(resolved):
        raise ValueError("destination overlaps the protected legacy project")
    if target.exists():
        if not update:
            raise ValueError(
                "destination already exists; use skills update for a managed installation"
            )
        if not target.is_dir() or (target / ".git").exists():
            raise ValueError("refusing to update a repository or unknown destination")
        marker = target / MARKER
        if marker.is_symlink() or not marker.is_file():
            raise ValueError("destination is not a managed installation")
        metadata = json.loads(marker.read_text())
        if (
            not isinstance(metadata, dict)
            or metadata.get("format") != 1
            or metadata.get("name") != name
            or metadata.get("files") != _fingerprints(target)
        ):
            raise ValueError("installation has local changes or invalid ownership metadata")
    elif update:
        raise ValueError("no installed Skill to update; use skills install first")
    payload = files("token_io_decoupling").joinpath("skill_bundle.zip").read_bytes()
    root.mkdir(parents=True, exist_ok=True)
    # Cooperating installers serialize before rechecking/publishing, never clobber a collision.
    lock = root / f".{name}.lock"
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise ValueError(
            "another installation is in progress; inspect the lock before retrying"
        ) from exc
    os.close(fd)
    try:
        with tempfile.TemporaryDirectory(prefix=f".{name}-", dir=root) as work:
            staged = Path(work) / "new"
            staged.mkdir()
            with zipfile.ZipFile(io.BytesIO(payload)) as archive:
                for entry in archive.infolist():
                    path = PurePosixPath(entry.filename)
                    if path.is_absolute() or ".." in path.parts or entry.is_dir():
                        raise ValueError("unsafe packaged Skill entry")
                    dest = staged / path
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    data = archive.read(entry)
                    if path.name in ("SKILL.md", "SKILL_zh_cn.md") and len(path.parts) == 1:
                        data = re.sub(
                            rb"(?m)^name: token-io-decoupling(?:-skill)?$",
                            b"name: " + name.encode(),
                            data,
                        )
                    dest.write_bytes(data)
            if not (staged / "SKILL.md").is_file():
                raise ValueError("packaged Skill entry missing")
            (staged / MARKER).write_text(
                json.dumps(
                    {
                        "format": 1,
                        "name": name,
                        "version": version("token-io-decoupling"),
                        "files": _fingerprints(staged),
                    },
                    sort_keys=True,
                )
            )
            if target.is_symlink():
                raise ValueError("destination changed during installation")
            if update:
                if (
                    json.loads((target / MARKER).read_text()) != metadata
                    or _fingerprints(target) != metadata["files"]
                ):
                    raise ValueError("installation changed during update")
                backup = Path(work) / "previous"
                target.rename(backup)
                try:
                    staged.rename(target)
                except OSError:
                    backup.rename(target)
                    raise
            else:
                if target.exists():
                    raise ValueError("destination appeared during installation")
                staged.rename(target)
    finally:
        lock.unlink()
    return target

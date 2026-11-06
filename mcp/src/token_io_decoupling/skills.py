"""Install versioned Skill snapshots without touching legacy project checkouts."""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import stat
import tempfile
import zipfile
from importlib.metadata import version
from importlib.resources import files
from pathlib import Path, PurePosixPath, PureWindowsPath

DEFAULT_NAME = "token-io-decoupling-skill"
LEGACY_NAME = "token-io-decoupling"
MARKER = ".token-io-skill.json"


def validate_skill_bundle(
    payload: bytes,
    *,
    expected_build_id: str | None = None,
    expected_files: dict[str, str] | None = None,
) -> tuple[dict, dict[str, bytes]]:
    """Validate the complete compiled archive before installation or packaging writes."""
    forbidden = {
        "_project",
        "rule_sources",
        "instruction-compiler",
        "tests",
        "benchmarks",
        "scripts",
        "sources",
    }
    try:
        contents = {}
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            for entry in archive.infolist():
                name = entry.filename
                path = PurePosixPath(name)
                if (
                    not name
                    or "\\" in name
                    or ":" in name
                    or "\x00" in name
                    or path.is_absolute()
                    or PureWindowsPath(name).drive
                    or path.as_posix() != name
                    or any(part.startswith(".") or part in forbidden for part in path.parts)
                    or entry.is_dir()
                    or stat.S_ISLNK(entry.external_attr >> 16)
                    or name in contents
                    or path.suffix not in {".md", ".yaml", ".json"}
                ):
                    raise ValueError("unsafe or non-product packaged Skill entry")
                contents[name] = archive.read(entry)
        manifest = json.loads(contents.get("manifest.json", b""))
        if not isinstance(manifest, dict):
            raise ValueError("compiled Skill manifest must be an object")
        build_id = manifest.get("build_id")
        declared = manifest.get("files")
        if (
            manifest.get("schema_version") != 2
            or not isinstance(build_id, str)
            or not build_id.strip()
            or not isinstance(declared, dict)
            or set(declared) != set(contents) - {"manifest.json"}
        ):
            raise ValueError("incompatible or incomplete compiled Skill manifest")
        if expected_build_id is not None and build_id != expected_build_id:
            raise ValueError("compiled Skill and core resources belong to different batches")
        for name, digest in declared.items():
            if not isinstance(digest, str) or digest != hashlib.sha256(contents[name]).hexdigest():
                raise ValueError("compiled Skill integrity check failed")
        if expected_files is not None and declared != expected_files:
            raise ValueError("compiled Skill files do not match the core instruction map")
        for name in ("SKILL.md", "SKILL_zh_cn.md", "agents/openai.yaml"):
            if not contents.get(name, b"").strip():
                raise ValueError("required compiled Skill content is missing or empty")
        return manifest, contents
    except (
        OSError,
        UnicodeError,
        KeyError,
        TypeError,
        RuntimeError,
        NotImplementedError,
        zipfile.BadZipFile,
    ) as exc:
        raise ValueError("compiled Skill bundle is malformed or unavailable") from exc


def _compiled_skill_identity() -> tuple[str, dict[str, str]]:
    """Read and verify the installed core batch without consulting author sources."""
    try:
        resources = files("token_io_decoupling_workflow").joinpath("_resources")
        manifest = json.loads(resources.joinpath("manifest.json").read_bytes())
        payload = resources.joinpath("instructions.json").read_bytes()
        instructions = json.loads(payload)
        if not isinstance(manifest, dict) or not isinstance(instructions, dict):
            raise ValueError("compiled core resources must be objects")
        build_id = manifest.get("build_id")
        if (
            manifest.get("schema_version") != 2
            or instructions.get("schema_version") != 2
            or not isinstance(build_id, str)
            or not build_id.strip()
            or instructions.get("build_id") != build_id
            or manifest.get("files") != {"instructions.json": hashlib.sha256(payload).hexdigest()}
        ):
            raise ValueError("compiled core resources are incompatible or corrupt")
        skill_files = instructions.get("skill_files")
        if (
            not isinstance(skill_files, dict)
            or not skill_files
            or not all(
                isinstance(name, str)
                and isinstance(digest, str)
                and re.fullmatch(r"[0-9a-f]{64}", digest)
                for name, digest in skill_files.items()
            )
        ):
            raise ValueError("compiled core Skill file map is missing or invalid")
        return build_id, skill_files
    except (OSError, UnicodeError, TypeError) as exc:
        raise ValueError("compiled core resources are unavailable") from exc


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
    payload = files("token_io_decoupling").joinpath("_resources/skill_bundle.zip").read_bytes()
    build_id, skill_files = _compiled_skill_identity()
    manifest, contents = validate_skill_bundle(
        payload, expected_build_id=build_id, expected_files=skill_files
    )
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
            for entry_name, data in contents.items():
                path = PurePosixPath(entry_name)
                dest = staged / path
                dest.parent.mkdir(parents=True, exist_ok=True)
                if path.name in ("SKILL.md", "SKILL_zh_cn.md") and len(path.parts) == 1:
                    data = re.sub(
                        rb"(?m)^name: token-io-decoupling(?:-skill)?$",
                        b"name: " + name.encode(),
                        data,
                    )
                dest.write_bytes(data)
            if not (staged / "SKILL.md").is_file():
                raise ValueError("packaged Skill entry missing")
            # The approved policy batch is unchanged by an installation-name substitution.
            installed_manifest = {
                **manifest,
                "files": {
                    key: digest
                    for key, digest in _fingerprints(staged).items()
                    if key != "manifest.json"
                },
            }
            (staged / "manifest.json").write_text(
                json.dumps(installed_manifest, sort_keys=True) + "\n", encoding="utf-8"
            )
            (staged / MARKER).write_text(
                json.dumps(
                    {
                        "format": 1,
                        "name": name,
                        "version": version("token-io-decoupling"),
                        "build_id": manifest["build_id"],
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

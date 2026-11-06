"""Install versioned Skill snapshots without touching legacy project checkouts."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
from importlib.metadata import version
from importlib.resources import files
from pathlib import Path, PurePosixPath

# 保留既有公开导入入口；实际归档校验由同一业务包的独立模块负责。
from token_io_decoupling.skill_bundle import SkillManifest, validate_skill_bundle

DEFAULT_NAME = "token-io-decoupling-skill"
LEGACY_NAME = "token-io-decoupling"
MARKER = ".token-io-skill.json"


def _compiled_skill_identity() -> tuple[str, dict[str, str]]:
    """从已安装 workflow 读取同批身份，不把旧 Skill 快照作为执行规则。"""
    try:
        resources = files("token_io_decoupling_workflow").joinpath("_resources")
        manifest = json.loads(resources.joinpath("manifest.json").read_bytes())
        payload = resources.joinpath("instructions.json").read_bytes()
        instructions = json.loads(payload)
        if not isinstance(manifest, dict) or not isinstance(instructions, dict):
            raise ValueError("compiled core resources must be objects")
        build_id = manifest.get("build_id")
        if (
            type(manifest.get("schema_version")) is not int
            or manifest["schema_version"] != 3
            or type(instructions.get("schema_version")) is not int
            or instructions["schema_version"] != 3
            or manifest.get("language") != "zh_cn"
            or instructions.get("language") != "zh_cn"
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


def _skill_destination(name: str) -> Path:
    """限定固定用户根并保护旧 checkout，先拒绝符号链接和相互覆盖。"""
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name) or name == LEGACY_NAME:
        raise ValueError("choose a new lower-case Skill name; the legacy name is protected")
    home = Path.home()
    root = home / ".agents/skills"
    target, legacy = root / name, root / LEGACY_NAME
    for path in (home / ".agents", root, target):
        if path.is_symlink():
            raise ValueError("symbolic links in the installation path are refused")
    resolved, old = target.resolve(), legacy.resolve()
    if resolved == old or resolved.is_relative_to(old) or old.is_relative_to(resolved):
        raise ValueError("destination overlaps the protected legacy project")
    return target


def _managed_metadata(target: Path, name: str, update: bool) -> dict | None:
    """只在归属及全部旧字节仍匹配时允许更新，不忽略用户本地修改。"""
    if not target.exists():
        if update:
            raise ValueError("no installed Skill to update; use skills install first")
        return None
    if not update:
        raise ValueError("destination already exists; use skills update for a managed installation")
    if not target.is_dir() or (target / ".git").exists():
        raise ValueError("refusing to update a repository or unknown destination")
    marker = target / MARKER
    if marker.is_symlink() or not marker.is_file():
        raise ValueError("destination is not a managed installation")
    metadata = json.loads(marker.read_text(encoding="utf-8"))
    if (
        not isinstance(metadata, dict)
        or metadata.get("format") != 1
        or metadata.get("name") != name
        or metadata.get("files") != _fingerprints(target)
    ):
        raise ValueError("installation has local changes or invalid ownership metadata")
    return metadata


def _write_installed_metadata(staged: Path, name: str, manifest: SkillManifest) -> None:
    """安装名称变化只重算本地字节指纹，批准的政策批次保持不变。"""
    installed_manifest = {
        **manifest,
        "files": {
            key: digest for key, digest in _fingerprints(staged).items() if key != "manifest.json"
        },
    }
    (staged / "manifest.json").write_text(
        json.dumps(installed_manifest, sort_keys=True) + "\n", encoding="utf-8"
    )
    metadata = {
        "format": 1,
        "name": name,
        "version": version("token-io-decoupling"),
        "build_id": manifest["build_id"],
        "files": _fingerprints(staged),
    }
    (staged / MARKER).write_text(json.dumps(metadata, sort_keys=True), encoding="utf-8")


def _stage_skill(
    staged: Path, name: str, manifest: SkillManifest, contents: dict[str, bytes]
) -> None:
    """准备完整新快照并重算安装元数据，此阶段不替换现有受管目标。"""
    staged.mkdir()
    for entry_name, data in contents.items():
        path = PurePosixPath(entry_name)
        destination = staged / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        if path.name == "SKILL.md" and len(path.parts) == 1:
            data = re.sub(
                rb"(?m)^name: token-io-decoupling(?:-skill)?$",
                b"name: " + name.encode(),
                data,
            )
        destination.write_bytes(data)
    _write_installed_metadata(staged, name, manifest)


def _replace_skill_snapshot(staged: Path, target: Path) -> None:
    # 旧副本不放入自动清理的 staging 目录，双重故障时仍可由操作者恢复。
    """发布失败先回滚；双重失败时保留自动清理范围外的完整旧副本。"""
    backup_root = Path(tempfile.mkdtemp(prefix=f".{target.name}-backup-", dir=target.parent))
    backup = backup_root / "previous"
    try:
        target.rename(backup)
    except OSError:
        backup_root.rmdir()
        raise
    try:
        staged.rename(target)
    except OSError:
        try:
            backup.rename(target)
        except OSError as exc:
            raise OSError(
                f"Skill update and rollback failed; previous snapshot preserved at {backup}"
            ) from exc
        backup_root.rmdir()
        raise
    shutil.rmtree(backup_root)


def _publish_skill(staged: Path, target: Path, metadata: dict | None) -> None:
    """在锁内再次核对目标归属，再进入可恢复的快照替换事务。"""
    if target.is_symlink():
        raise ValueError("destination changed during installation")
    if metadata is None:
        if target.exists():
            raise ValueError("destination appeared during installation")
        staged.rename(target)
        return
    if (
        json.loads((target / MARKER).read_text(encoding="utf-8")) != metadata
        or _fingerprints(target) != metadata["files"]
    ):
        raise ValueError("installation changed during update")
    _replace_skill_snapshot(staged, target)


def install_skill(*, name: str = DEFAULT_NAME, update: bool = False) -> Path:
    """只在固定用户 skills 根目录发布完整中文快照，不接受任意目标路径。"""
    target = _skill_destination(name)
    metadata = _managed_metadata(target, name, update)
    payload = files("token_io_decoupling").joinpath("_resources/skill_bundle.zip").read_bytes()
    build_id, skill_files = _compiled_skill_identity()
    manifest, contents = validate_skill_bundle(
        payload, expected_build_id=build_id, expected_files=skill_files
    )
    root = target.parent
    root.mkdir(parents=True, exist_ok=True)
    lock = root / f".{name}.lock"
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise ValueError(
            "another installation is in progress; inspect the lock before retrying"
        ) from exc
    os.close(descriptor)
    try:
        with tempfile.TemporaryDirectory(prefix=f".{name}-", dir=root) as work:
            staged = Path(work) / "new"
            _stage_skill(staged, name, manifest, contents)
            _publish_skill(staged, target, metadata)
    finally:
        lock.unlink()
    return target

"""将已编译的 Hooks Skill 发布至本地受管理目录。"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
from pathlib import Path
from tempfile import mkdtemp

DEFAULT_NAME = "token-io-decoupling"
MARKER = ".token-io-skill.json"
SKILLS_DIRECTORY = Path(".agents/skills")


def _present(path: Path) -> bool:
    return path.is_symlink() or path.exists()


def _destination(
    name: str, project_root: Path | None, skills_dir: Path | None,
) -> tuple[Path, Path]:
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
        raise ValueError("Skill 名称须由小写字母、数字和单个分隔连字符组成")
    if skills_dir is not None:
        if project_root is not None:
            raise ValueError("--skills-dir 和 --project-root 只能指定一项")
        requested = skills_dir.expanduser()
        root = Path(os.path.abspath(requested))
        if requested.resolve() != root:
            raise ValueError(f"Skill 根目录不能经过符号链接：{requested}")
        return root, root / name
    home = Path.home().resolve()
    if project_root is None:
        return home, home / SKILLS_DIRECTORY / name
    if not project_root.is_absolute() or not project_root.is_dir() or project_root == home:
        raise ValueError("项目级安装需要已存在的项目绝对目录")
    return project_root, project_root / SKILLS_DIRECTORY / name


def _check_destination(root: Path, target: Path) -> None:
    if any(part.casefold() == ".git" for part in root.parts):
        raise ValueError(f"拒绝写入 Git 元数据：{root}")
    if root.resolve() != root or (root.exists() and not root.is_dir()):
        raise ValueError(f"Skill 根目录必须是普通目录：{root}")
    cursor = root
    for part in target.relative_to(root).parts:
        cursor /= part
        if cursor.is_symlink() or (cursor.exists() and not cursor.is_dir()):
            raise ValueError(f"Skill 目录必须是普通目录：{cursor}")
        if _present(cursor / ".git"):
            raise ValueError(f"拒绝写入 Git checkout：{cursor}")


def _fingerprints(root: Path) -> dict[str, str]:
    files = {}
    for path in root.rglob("*"):
        if path.is_symlink():
            raise ValueError(f"Skill 安装包含符号链接：{path}")
        if path.is_file() and path != root / MARKER:
            files[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
        elif path != root / MARKER and not path.is_dir():
            raise ValueError(f"Skill 安装包含特殊文件：{path}")
    return files


def _snapshot(target: Path, name: str) -> dict | None:
    if not target.exists():
        return None
    marker = target / MARKER
    if marker.is_symlink() or not marker.is_file():
        raise ValueError(f"目标不是受管理的 Skill：{target}")
    payload = json.loads(marker.read_text(encoding="utf-8"))
    if (
        not isinstance(payload, dict)
        or payload.get("format") != 1
        or payload.get("name") != name
        or payload.get("files") != _fingerprints(target)
    ):
        raise ValueError(f"Skill 有本地修改或安装标记无效：{target}")
    return payload


def update_local_skill(
    outputs: dict[Path, str], name: str = DEFAULT_NAME, *,
    project_root: Path | None = None, skills_dir: Path | None = None,
    install_only: bool = False,
) -> Path:
    """向选定的本地目录发布受管理的 Skill。"""
    root, target = _destination(name, project_root, skills_dir)
    _check_destination(root, target)
    target.parent.mkdir(parents=True, exist_ok=True)
    lock = target.parent / f".{name}.lock"
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as error:
        raise ValueError(f"Skill 更新已加锁，请核实：{lock}") from error
    os.close(descriptor)
    try:
        _check_destination(root, target)
        before = _snapshot(target, name)
        if install_only and before is not None:
            raise ValueError(f"Skill 已安装，请使用 --update-skill：{target}")
        work = Path(mkdtemp(prefix=f".{name}-", dir=target.parent))
        backup = work / "previous"
        keep_backup = False
        try:
            staged = work / "new"
            staged.mkdir()
            for relative, body in outputs.items():
                if relative == Path("SKILL.md"):
                    body = re.sub(rf"(?m)^name: {re.escape(DEFAULT_NAME)}$", f"name: {name}", body)
                destination = staged / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text(body, encoding="utf-8")
            (staged / MARKER).write_text(
                json.dumps(
                    {"format": 1, "name": name, "files": _fingerprints(staged)},
                    ensure_ascii=False,
                    sort_keys=True,
                ) + "\n",
                encoding="utf-8",
            )
            _check_destination(root, target)
            if _snapshot(target, name) != before:
                raise ValueError(f"Skill 目标在更新期间发生变化：{target}")
            if before is not None:
                target.rename(backup)
            try:
                staged.rename(target)
            except OSError:
                if before is not None:
                    keep_backup = True
                    if _present(target):
                        raise ValueError(f"发布失败，原 Skill 保留于：{backup}")
                    try:
                        backup.rename(target)
                    except OSError as error:
                        raise ValueError(f"恢复失败，原 Skill 保留于：{backup}") from error
                    keep_backup = False
                raise
        finally:
            if not keep_backup:
                shutil.rmtree(work)
    finally:
        lock.unlink()
    return target

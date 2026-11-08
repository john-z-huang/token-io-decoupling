"""保留其它配置，以备份及原子替换注册本包的静态 Hook。"""

from __future__ import annotations

import json
import os
import shlex
import stat
import tempfile
from pathlib import Path

EVENTS = (
    "SessionStart",
    "UserPromptSubmit",
    "PreToolUse",
    "PostToolUse",
    "SubagentStop",
    "Stop",
)


def default_hooks_path() -> Path:
    """遵循宿主的 CODEX_HOME，未设置时使用用户配置目录。"""
    return Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex") / "hooks.json"


def _load_config(path: Path) -> tuple[dict, bytes | None]:
    if path.is_symlink():
        raise ValueError("hooks file must not be a symbolic link")
    original = path.read_bytes() if path.exists() else None
    config = json.loads(original) if original is not None else {}
    if not isinstance(config, dict) or not isinstance(config.get("hooks", {}), dict):
        raise ValueError("hooks configuration must contain an object")
    return config, original


def _merge_hooks(config: dict, command: str) -> bool:
    hooks = config.setdefault("hooks", {})
    changed = False
    for event in EVENTS:
        groups = hooks.setdefault(event, [])
        if not isinstance(groups, list) or any(not isinstance(group, dict) for group in groups):
            raise ValueError("hook event must contain matcher groups")
        handlers = [group.get("hooks", []) for group in groups]
        if any(not isinstance(items, list) for items in handlers):
            raise ValueError("hook group must contain a handler list")
        if any(
            isinstance(item, dict) and item.get("command") == command
            for items in handlers
            for item in items
        ):
            continue
        groups.append(
            {
                "hooks": [
                    {
                        "type": "command",
                        "command": command,
                        "timeout": 10,
                        "statusMessage": "检查 token-io-decoupling 事件契约",
                    }
                ]
            }
        )
        changed = True
    return changed


def _write_config(path: Path, encoded: bytes, original: bytes | None) -> str | None:
    path.parent.mkdir(parents=True, exist_ok=True)
    backup = None
    mode = stat.S_IMODE(path.stat().st_mode) if original is not None else 0o600
    with tempfile.NamedTemporaryFile(
        dir=path.parent, prefix=".token-io-hooks-", delete=False
    ) as file:
        temporary = Path(file.name)
        file.write(encoded)
        file.flush()
        os.fsync(file.fileno())
    try:
        os.chmod(temporary, mode)
        # 并发编辑时保留现场，不把较新的用户内容覆盖掉。
        current = path.read_bytes() if path.exists() else None
        if path.is_symlink() or current != original:
            raise ValueError("hooks configuration changed during registration")
        if original is not None:
            with tempfile.NamedTemporaryFile(
                dir=path.parent, prefix="hooks.json.token-io-", suffix=".bak", delete=False
            ) as file:
                file.write(original)
                backup = file.name
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    return backup


def register_hooks(path: Path, executable: Path, *, dry_run: bool = False) -> dict:
    """注册六种静态事件；不更改信任记录、启用状态或已有其它 Hook。"""
    if not executable.is_absolute():
        raise ValueError("hook executable must be an absolute path")
    config, original = _load_config(path)
    changed = _merge_hooks(config, shlex.quote(str(executable)))
    backup = None
    if changed and not dry_run:
        encoded = (json.dumps(config, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        backup = _write_config(path, encoded, original)
    return {"path": str(path), "changed": changed, "dry_run": dry_run, "backup": backup}

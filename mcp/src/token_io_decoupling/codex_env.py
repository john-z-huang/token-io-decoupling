"""Safely add environment-variable forwarding names to existing Codex MCP servers."""

from __future__ import annotations

import errno
import os
import re
import stat
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any

import tomlkit
from tomlkit.exceptions import ParseError

DEFAULT_ENV_VARS = ("OPENAI_API_KEY", "OPENAI_BASE_URL")


class CodexEnvError(RuntimeError):
    """A safe, user-displayable Codex configuration error."""


def config_path(explicit: Path | None = None) -> Path:
    """Resolve Codex's config path without reading credential values."""
    if explicit is not None:
        return explicit.expanduser()
    codex_home = os.environ.get("CODEX_HOME")
    root = Path(codex_home).expanduser() if codex_home else Path.home() / ".codex"
    return root / "config.toml"


def _read_target(path: Path, *, allow_missing: bool) -> tuple[bytes, os.stat_result] | None:
    try:
        path_info = path.lstat()
    except FileNotFoundError:
        if allow_missing:
            return None
        raise CodexEnvError("Codex config file does not exist") from None
    except OSError:
        raise CodexEnvError("Codex config file could not be inspected") from None
    if stat.S_ISLNK(path_info.st_mode) or not stat.S_ISREG(path_info.st_mode):
        raise CodexEnvError("Codex config target must be a regular, non-symlink file")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        if exc.errno == errno.ELOOP:
            raise CodexEnvError("Codex config target must be a regular, non-symlink file") from None
        raise CodexEnvError("Codex config file could not be inspected") from None
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or (info.st_dev, info.st_ino) != (
            path_info.st_dev,
            path_info.st_ino,
        ):
            raise CodexEnvError("Codex config target changed during inspection")
        chunks = []
        while chunk := os.read(descriptor, 1024 * 1024):
            chunks.append(chunk)
        return b"".join(chunks), info
    except CodexEnvError:
        raise
    except OSError:
        raise CodexEnvError("Codex config file could not be read") from None
    finally:
        os.close(descriptor)


def _parse(raw: bytes) -> tomlkit.TOMLDocument:
    try:
        return tomlkit.parse(raw.decode("utf-8"))
    except (UnicodeDecodeError, ParseError):
        raise CodexEnvError("Codex config is not valid UTF-8 TOML") from None


def _server_table(document: Any, name: str, *, allow_missing: bool) -> Any | None:
    servers = document.get("mcp_servers")
    if servers is None:
        if allow_missing:
            return None
        raise CodexEnvError("Codex config has no mcp_servers table")
    if not isinstance(servers, dict):
        raise CodexEnvError("Codex mcp_servers setting must be a table")
    server = servers.get(name)
    if server is None:
        if allow_missing:
            return None
        raise CodexEnvError(f"Codex server section is missing: {name}")
    if not isinstance(server, dict):
        raise CodexEnvError(f"Codex server section is malformed: {name}")
    if "url" in server or "http_headers" in server:
        raise CodexEnvError(f"Codex server is not stdio: {name}")
    command = server.get("command")
    args = server.get("args", [])
    if (
        not isinstance(command, str)
        or not command
        or not isinstance(args, list)
        or not all(isinstance(arg, str) for arg in args)
    ):
        raise CodexEnvError(f"Codex server is not a valid stdio registration: {name}")
    env_vars = server.get("env_vars", [])
    if not isinstance(env_vars, list):
        raise CodexEnvError(f"Codex env_vars must be an array: {name}")
    for item in env_vars:
        if isinstance(item, str):
            continue
        if isinstance(item, dict):
            var_name, source = item.get("name"), item.get("source", "local")
            if not isinstance(var_name, str) or source not in ("local", "remote"):
                raise CodexEnvError(f"Codex env_vars entry is malformed: {name}")
            continue
        raise CodexEnvError(f"Codex env_vars entry is malformed: {name}")
    return server


def validate_setup_config(
    path: Path, server_names: tuple[str, ...], *, allow_replaced_conflicts: bool = False
) -> None:
    """Preflight a Codex config before registration, allowing new sections."""
    snapshot = _read_target(path, allow_missing=True)
    if snapshot is None:
        return
    document = _parse(snapshot[0])
    servers = document.get("mcp_servers")
    if servers is not None and not isinstance(servers, dict):
        raise CodexEnvError("Codex mcp_servers setting must be a table")
    for name in server_names:
        server = servers.get(name) if isinstance(servers, dict) else None
        if server is None:
            continue
        if not isinstance(server, dict):
            raise CodexEnvError(f"Codex server section is malformed: {name}")
        if allow_replaced_conflicts:
            continue
        _server_table(document, name, allow_missing=True)


_HTTP_POLICY_FIELDS = (
    "default_tools_approval_mode",
    "tools",
    "enabled_tools",
    "disabled_tools",
    "startup_timeout_sec",
    "tool_timeout_sec",
    "required",
)


def capture_replacement_settings(
    path: Path,
    server_names: tuple[str, ...],
    pending_names: tuple[str, ...] = (),
    env_names: tuple[str, ...] = DEFAULT_ENV_VARS,
) -> dict[str, dict[str, Any]]:
    """Snapshot user settings that Codex's registration upsert would discard."""
    if not server_names:
        return {}
    snapshot = _read_target(path, allow_missing=True)
    if snapshot is None:
        return {}
    document = _parse(snapshot[0])
    if pending_names and tomlkit.dumps(document).encode("utf-8") != snapshot[0]:
        raise CodexEnvError(
            "Codex config uses a TOML layout that cannot be safely rewritten without reformatting"
        )
    servers = document.get("mcp_servers")
    if servers is None:
        return {}
    if not isinstance(servers, dict):
        raise CodexEnvError("Codex mcp_servers setting must be a table")
    preserved: dict[str, dict[str, Any]] = {}
    for name in server_names:
        server = servers.get(name)
        if server is None:
            if name not in pending_names:
                raise CodexEnvError(f"Codex server section is missing: {name}")
            continue
        if not isinstance(server, dict):
            raise CodexEnvError(f"Codex server section is malformed: {name}")
        replacing = name in pending_names
        if "url" in server or "http_headers" in server:
            if not replacing:
                raise CodexEnvError(f"Codex server is not stdio: {name}")
            preserved[name] = {
                key: deepcopy(server[key]) for key in _HTTP_POLICY_FIELDS if key in server
            }
            continue
        _server_table(document, name, allow_missing=False)
        _check_forwarding_sources(server, name, env_names)
        if replacing:
            preserved[name] = {
                key: deepcopy(value)
                for key, value in server.items()
                if key not in {"command", "args", "enabled"}
            }
    return preserved


def _check_forwarding_sources(server: Any, server_name: str, env_names: tuple[str, ...]) -> None:
    current = server.get("env_vars", [])
    sources: dict[str, set[str]] = {}
    for item in current:
        if isinstance(item, str):
            sources.setdefault(item, set()).add("local")
        else:
            sources.setdefault(str(item["name"]), set()).add(str(item.get("source", "local")))
    for name in env_names:
        if "remote" in sources.get(name, set()):
            raise CodexEnvError(
                f"Codex env_vars marks {name} as remote for {server_name}; refusing to override"
            )


def _restore_settings(server: Any, values: dict[str, Any]) -> bool:
    if not values:
        return False
    for key, value in values.items():
        server[key] = deepcopy(value)
    return True


def _merge_names(server: Any, server_name: str, env_names: tuple[str, ...]) -> bool:
    current = server.get("env_vars")
    if current is None:
        current = tomlkit.array().multiline(False)
        server["env_vars"] = current
    sources: dict[str, set[str]] = {}
    for item in current:
        if isinstance(item, str):
            sources.setdefault(str(item), set()).add("local")
        else:
            sources.setdefault(str(item["name"]), set()).add(str(item.get("source", "local")))
    _check_forwarding_sources(server, server_name, env_names)
    changed = False
    for name in env_names:
        if name not in sources:
            current.append(name)
            sources[name] = {"local"}
            changed = True
    if not changed and "env_vars" not in server:
        del server["env_vars"]
    return changed


def _without_target_env_vars(document: Any, names: tuple[str, ...]) -> Any:
    clone = deepcopy(document)
    servers = clone.get("mcp_servers", {})
    for name in names:
        server = servers.get(name)
        if isinstance(server, dict):
            server.pop("env_vars", None)
    return clone


def merge_env_vars(
    path: Path,
    server_names: tuple[str, ...],
    env_names: tuple[str, ...] = DEFAULT_ENV_VARS,
    *,
    dry_run: bool = False,
    preserved_settings: dict[str, dict[str, Any]] | None = None,
) -> tuple[str, ...]:
    """Atomically merge names into existing selected stdio registrations."""
    if not server_names or len(set(server_names)) != len(server_names):
        raise CodexEnvError("select one or more distinct Codex server names")
    if (
        not env_names
        or len(set(env_names)) != len(env_names)
        or not all(
            isinstance(name, str) and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name)
            for name in env_names
        )
    ):
        raise CodexEnvError("environment variable names must be distinct nonempty strings")
    snapshot = _read_target(path, allow_missing=False)
    assert snapshot is not None
    original, info = snapshot
    document = _parse(original)
    original_roundtrip = tomlkit.dumps(document).encode("utf-8")
    servers = document.get("mcp_servers")
    if not isinstance(servers, dict):
        raise CodexEnvError("Codex config has no valid mcp_servers table")
    selected = {name: _server_table(document, name, allow_missing=False) for name in server_names}
    expected_baseline = deepcopy(document)
    expected_servers = expected_baseline.get("mcp_servers", {})
    for name, values in (preserved_settings or {}).items():
        if name not in selected:
            raise CodexEnvError(f"preserved settings do not match a selected server: {name}")
        for key, value in values.items():
            expected_servers[name][key] = deepcopy(value)
    expected_without_targets = _without_target_env_vars(expected_baseline, server_names)
    changed = set()
    for name, values in (preserved_settings or {}).items():
        if _restore_settings(selected[name], values):
            changed.add(name)
    changed.update(name for name in server_names if _merge_names(selected[name], name, env_names))
    changed_names = tuple(name for name in server_names if name in changed)
    if not changed_names:
        return ()
    if original_roundtrip != original:
        raise CodexEnvError(
            "Codex config uses a TOML layout that cannot be safely rewritten without reformatting"
        )
    rendered = tomlkit.dumps(document).encode("utf-8")
    verified = _parse(rendered)
    if _without_target_env_vars(verified, server_names) != expected_without_targets:
        raise CodexEnvError("Codex config validation failed; no changes were written")
    if dry_run:
        return changed_names
    try:
        current = _read_target(path, allow_missing=False)
        assert current is not None
        current_bytes, current_info = current
        if (
            (current_info.st_dev, current_info.st_ino) != (info.st_dev, info.st_ino)
            or stat.S_IMODE(current_info.st_mode) != stat.S_IMODE(info.st_mode)
            or current_bytes != original
        ):
            raise CodexEnvError("Codex config changed during update; retry after reviewing it")
    except OSError:
        raise CodexEnvError("Codex config could not be rechecked before update") from None
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=path.parent, prefix=f".{path.name}.", delete=False
        ) as f:
            temp_path = Path(f.name)
            f.write(rendered)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(temp_path, stat.S_IMODE(info.st_mode))
        current = _read_target(path, allow_missing=False)
        assert current is not None
        current_bytes, current_info = current
        if (
            (current_info.st_dev, current_info.st_ino) != (info.st_dev, info.st_ino)
            or stat.S_IMODE(current_info.st_mode) != stat.S_IMODE(info.st_mode)
            or current_bytes != original
        ):
            raise CodexEnvError("Codex config changed during update; retry after reviewing it")
        os.replace(temp_path, path)
        temp_path = None
    except CodexEnvError:
        raise
    except OSError:
        raise CodexEnvError("Codex config could not be updated") from None
    finally:
        if temp_path is not None:
            try:
                temp_path.unlink()
            except OSError:
                pass
    return changed_names

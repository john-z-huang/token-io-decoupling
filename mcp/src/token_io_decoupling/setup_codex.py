"""Preflight and configure the installed launcher in Codex CLI."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sysconfig
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path
from typing import Any

from token_io_decoupling_core.profiles import PROFILE_SERVER_NAMES

from token_io_decoupling.codex_env import (
    DEFAULT_ENV_VARS,
    CodexEnvError,
    capture_replacement_settings,
    config_path,
    merge_env_vars,
)

_TIMEOUT_SECONDS = 15
_ENTRY_POINT_NAME = "token-io-decoupling"
_ENTRY_POINT_VALUE = "token_io_decoupling.cli:main"


class SetupError(RuntimeError):
    """A safe, user-displayable setup failure."""


@dataclass(frozen=True)
class Registration:
    name: str
    command: str
    args: tuple[str, ...]
    enabled: bool


def _installed_executable() -> Path:
    try:
        distribution = metadata.distribution("token-io-decoupling")
        scripts_directory = Path(sysconfig.get_path("scripts"))
    except (metadata.PackageNotFoundError, OSError, TypeError, ValueError) as exc:
        raise SetupError("token-io-decoupling installation metadata is unavailable") from exc
    entry_point = next(
        (
            item
            for item in distribution.entry_points
            if item.group == "console_scripts" and item.name == _ENTRY_POINT_NAME
        ),
        None,
    )
    if entry_point is None or entry_point.value != _ENTRY_POINT_VALUE:
        raise SetupError("installed token-io-decoupling entry point is unavailable")
    candidates = [scripts_directory / _ENTRY_POINT_NAME]
    if os.name == "nt":
        candidates.append(scripts_directory / f"{_ENTRY_POINT_NAME}.exe")
    executable = next((path for path in candidates if path.is_file()), None)
    if executable is None:
        raise SetupError("installed token-io-decoupling executable was not found")
    try:
        executable = executable.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise SetupError("installed token-io-decoupling executable could not be resolved") from exc
    if os.name != "nt" and not os.access(executable, os.X_OK):
        raise SetupError("installed token-io-decoupling executable is not executable")
    return executable


def _run(argv: list[str]) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(
            argv, check=False, capture_output=True, text=True, timeout=_TIMEOUT_SECONDS, shell=False
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise SetupError(f"command failed or timed out: {argv[0]}") from exc
    if result.returncode != 0:
        raise SetupError(f"command failed ({result.returncode}): {argv[0]}")
    return result


def _json_output(argv: list[str]) -> Any:
    result = _run(argv)
    try:
        return json.loads(result.stdout)
    except (json.JSONDecodeError, TypeError) as exc:
        raise SetupError(f"command returned invalid JSON: {argv[0]}") from exc


def _registration(value: Any, expected_name: str) -> Registration:
    if not isinstance(value, dict) or value.get("name") != expected_name:
        raise SetupError(f"Codex returned an invalid registration for {expected_name}")
    transport = value.get("transport")
    if not isinstance(transport, dict):
        raise SetupError(f"Codex returned an invalid transport for {expected_name}")
    enabled = value.get("enabled")
    if not isinstance(enabled, bool):
        raise SetupError(f"Codex returned an invalid enabled state for {expected_name}")
    transport_type = transport.get("type")
    if transport_type == "http":
        return Registration(expected_name, "", (), enabled)
    if transport_type != "stdio":
        raise SetupError(f"Codex returned an unsupported transport type for {expected_name}")
    command = transport.get("command")
    args = transport.get("args", [])
    if (
        not isinstance(command, str)
        or not isinstance(args, list)
        or not all(isinstance(item, str) for item in args)
    ):
        raise SetupError(f"Codex returned an invalid stdio registration for {expected_name}")
    return Registration(expected_name, command, tuple(args), enabled)


def _listed_names(value: Any) -> set[str]:
    if isinstance(value, dict):
        servers = value.get("servers", value.get("mcpServers"))
        if isinstance(servers, dict):
            if not all(
                isinstance(name, str) and isinstance(item, dict) for name, item in servers.items()
            ):
                raise SetupError("Codex returned a malformed MCP server listing")
            return set(servers)
        value = servers
    if not isinstance(value, list):
        raise SetupError("Codex returned an invalid MCP server listing")
    names: set[str] = set()
    for item in value:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            raise SetupError("Codex returned a malformed MCP server listing entry")
        name = item["name"]
        if name in names:
            raise SetupError("Codex returned a duplicate MCP server listing entry")
        names.add(name)
    return names


def _same_registration(existing: Registration | None, executable: Path, profile: str) -> bool:
    expected_args = ("start-mcp-server", "--profile", profile)
    if existing is None or not existing.enabled or existing.args != expected_args:
        return False
    try:
        return Path(existing.command).resolve(strict=True) == executable
    except (OSError, RuntimeError):
        return False


def setup_codex(
    *,
    profile: str | None = None,
    all_profiles: bool = False,
    dry_run: bool = False,
    replace: bool = False,
) -> int:
    if profile is not None and profile not in PROFILE_SERVER_NAMES:
        raise SetupError(f"unknown server profile: {profile}")
    if profile is not None and all_profiles:
        raise SetupError("a profile cannot be combined with all_profiles")
    profiles = [profile] if profile is not None else list(PROFILE_SERVER_NAMES)
    executable = _installed_executable()
    add_commands = {
        item: [
            "codex",
            "mcp",
            "add",
            PROFILE_SERVER_NAMES[item],
            "--",
            str(executable),
            "start-mcp-server",
            "--profile",
            item,
        ]
        for item in profiles
    }
    if dry_run:
        print("Dry run: no Codex command or configuration preflight was run.")
        for item in profiles:
            print(json.dumps(add_commands[item]))
        names = [PROFILE_SERVER_NAMES[item] for item in profiles]
        print(f"Would merge env_vars {list(DEFAULT_ENV_VARS)!r} into: {', '.join(names)}")
        return 0

    codex = shutil.which("codex")
    if codex is None:
        raise SetupError("Codex CLI was not found on PATH")
    prefix = str(Path(codex).resolve())
    _run([prefix, "--version"])
    listed_names = _listed_names(_json_output([prefix, "mcp", "list", "--json"]))
    existing: dict[str, Registration | None] = {}
    for item in profiles:
        name = PROFILE_SERVER_NAMES[item]
        if name not in listed_names:
            existing[item] = None
            continue
        try:
            existing[item] = _registration(
                _json_output([prefix, "mcp", "get", name, "--json"]), name
            )
        except SetupError as exc:
            raise SetupError(f"Codex registration preflight failed for {name}: {exc}") from exc

    pending: list[str] = []
    for item in profiles:
        current = existing[item]
        if _same_registration(current, executable, item):
            continue
        if current is not None and not replace:
            raise SetupError(
                f"Codex server {PROFILE_SERVER_NAMES[item]} has a conflicting configuration; "
                "use --replace"
            )
        pending.append(item)

    selected_names = tuple(PROFILE_SERVER_NAMES[item] for item in profiles)
    try:
        preserved_settings = capture_replacement_settings(
            config_path(),
            selected_names,
            tuple(PROFILE_SERVER_NAMES[item] for item in pending),
            DEFAULT_ENV_VARS,
        )
    except CodexEnvError as exc:
        raise SetupError(f"Codex environment forwarding preflight failed: {exc}") from exc

    applied: list[str] = []
    forwarded: list[str] = []
    stable = tuple(
        item
        for item in selected_names
        if item not in {PROFILE_SERVER_NAMES[pending_item] for pending_item in pending}
    )
    try:
        if stable:
            forwarded.extend(merge_env_vars(config_path(), stable))
    except CodexEnvError as exc:
        raise SetupError(
            f"registrations unchanged; environment forwarding pending for "
            f"[{', '.join(stable)}]: {exc}"
        ) from exc
    for index, item in enumerate(pending):
        name = PROFILE_SERVER_NAMES[item]
        try:
            _run([prefix, *add_commands[item][1:]])
        except SetupError as exc:
            remaining = [PROFILE_SERVER_NAMES[p] for p in pending[index:]]
            raise SetupError(
                f"registration stopped after applying [{', '.join(applied) or 'none'}]; "
                f"pending [{', '.join(remaining)}]; environment forwarding completed for "
                f"[{', '.join(forwarded) or 'none'}] and was not run for pending registrations: "
                f"{exc}"
            ) from exc
        applied.append(name)
        try:
            forwarded.extend(
                merge_env_vars(
                    config_path(),
                    (name,),
                    preserved_settings={name: preserved_settings[name]}
                    if name in preserved_settings
                    else None,
                )
            )
        except CodexEnvError as exc:
            remaining = [PROFILE_SERVER_NAMES[p] for p in pending[index + 1 :]]
            forwarding_pending = [name, *remaining]
            raise SetupError(
                f"registration commands applied [{', '.join(applied)}]; pending registrations "
                f"[{', '.join(remaining) or 'none'}]; environment forwarding completed for "
                f"[{', '.join(forwarded) or 'none'}]; forwarding pending for "
                f"[{', '.join(forwarding_pending)}]: {exc}"
            ) from exc
    for item in profiles:
        if item not in pending:
            print(f"already configured: {PROFILE_SERVER_NAMES[item]}")
    if applied:
        print("configured: " + ", ".join(applied))
    if forwarded:
        print("updated environment forwarding: " + ", ".join(forwarded))
    else:
        print("environment forwarding already configured: " + ", ".join(selected_names))
    return 0

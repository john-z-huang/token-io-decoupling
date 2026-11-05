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


def _same_registration(
    existing: Registration | None, executable: Path, profile: str, extra_args: tuple[str, ...] = ()
) -> bool:
    expected_args = ("start-mcp-server", "--profile", profile, *extra_args)
    if existing is None or not existing.enabled or existing.args != expected_args:
        return False
    try:
        return Path(existing.command).resolve(strict=True) == executable
    except (OSError, RuntimeError):
        return False


def _known_memory_args(arguments: tuple[str, ...]) -> bool:
    return (
        len(arguments) == 4
        and arguments[0] == "--serena-project-root"
        and arguments[2] == "--serena-python"
        and Path(arguments[1]).is_absolute()
        and Path(arguments[3]).is_absolute()
    )


def _serena_launch_args(
    project_root: Path | str | None,
    python_executable: Path | str | None,
    *,
    dry_run: bool,
) -> tuple[str, ...]:
    if project_root is None:
        if python_executable is not None:
            raise SetupError("--serena-python requires --serena-project-root")
        return ()
    project = Path(project_root).expanduser()
    if not project.is_absolute():
        raise SetupError("--serena-project-root must be an absolute project directory")
    python_path = Path(python_executable).expanduser() if python_executable is not None else None
    if python_path is not None and not python_path.is_absolute():
        raise SetupError("--serena-python must be an absolute interpreter path")
    if dry_run:
        return (
            "--serena-project-root",
            str(project),
            "--serena-python",
            str(python_path)
            if python_path is not None
            else "<uv-tool-dir>/serena-agent/bin/python",
        )
    try:
        project = project.resolve(strict=True)
        if not project.is_dir():
            raise OSError("not a project directory")
    except OSError as exc:
        raise SetupError("Serena target project directory is unavailable") from exc
    if python_path is None:
        uv = shutil.which("uv")
        if uv is None:
            raise SetupError("uv is required to discover Serena; use --serena-python to override")
        directory = _run([uv, "tool", "dir"]).stdout.strip()
        if not directory or "\n" in directory or not Path(directory).is_absolute():
            raise SetupError("uv returned an invalid tool directory")
        python_path = Path(directory) / "serena-agent" / "bin" / "python"
    try:
        # Resolving bin/python itself would select the base interpreter and lose its venv.
        python_path = python_path.parent.resolve(strict=True) / python_path.name
        if not python_path.is_file() or not os.access(python_path, os.X_OK):
            raise OSError("interpreter unavailable")
    except OSError as exc:
        raise SetupError("Serena uv tool Python was not found; supply --serena-python") from exc
    from token_io_decoupling.serena_memory_runtime import IsolatedSerenaMemoryService

    capability = IsolatedSerenaMemoryService(project, python_path).capability()
    if capability.get("status") != "configured":
        reason = capability.get("reason_code", "serena_backend_unavailable")
        if (
            not isinstance(reason, str)
            or len(reason) > 96
            or not all(character in "abcdefghijklmnopqrstuvwxyz0123456789_" for character in reason)
        ):
            reason = "serena_backend_unavailable"
        raise SetupError(
            f"Serena Memory preflight failed ({reason}); configuration was not written"
        )
    return ("--serena-project-root", str(project), "--serena-python", str(python_path))


def setup_codex(
    *,
    profile: str | None = None,
    all_profiles: bool = False,
    dry_run: bool = False,
    replace: bool = False,
    serena_project_root: Path | str | None = None,
    serena_python: Path | str | None = None,
) -> int:
    if profile is not None and profile not in PROFILE_SERVER_NAMES:
        raise SetupError(f"unknown server profile: {profile}")
    if profile is not None and all_profiles:
        raise SetupError("a profile cannot be combined with all_profiles")
    profiles = [profile] if profile is not None else list(PROFILE_SERVER_NAMES)
    if "workflow" not in profiles and (
        serena_project_root is not None or serena_python is not None
    ):
        raise SetupError("Serena Memory configuration requires the workflow profile")
    memory_args = _serena_launch_args(serena_project_root, serena_python, dry_run=dry_run)
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
    if memory_args:
        add_commands["workflow"].extend(memory_args)
    if dry_run:
        print("Dry run: no Codex command or configuration preflight was run.")
        for item in profiles:
            print(json.dumps(add_commands[item]))
        names = [PROFILE_SERVER_NAMES[item] for item in profiles]
        print(f"Would merge env_vars {list(DEFAULT_ENV_VARS)!r} into: {', '.join(names)}")
        if memory_args:
            if serena_python is None:
                print("Would discover Serena Python with uv tool dir; discovery was not run.")
            print("Would forward the SERENA_HOME variable name to the workflow server.")
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
    current_workflow = existing.get("workflow")
    if (
        not memory_args
        and current_workflow is not None
        and current_workflow.args[:3] == ("start-mcp-server", "--profile", "workflow")
        and _known_memory_args(current_workflow.args[3:])
    ):
        memory_args = current_workflow.args[3:]
        add_commands["workflow"].extend(memory_args)
    for item in profiles:
        current = existing[item]
        suffix = memory_args if item == "workflow" else ()
        if _same_registration(current, executable, item, suffix):
            continue
        managed_memory_upgrade = (
            bool(suffix) and item == "workflow" and _same_registration(current, executable, item)
        )
        if current is not None and not replace and not managed_memory_upgrade:
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
            workflow_name = PROFILE_SERVER_NAMES["workflow"]
            if memory_args and workflow_name in stable:
                forwarded.extend(
                    merge_env_vars(
                        config_path(), (workflow_name,), (*DEFAULT_ENV_VARS, "SERENA_HOME")
                    )
                )
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
                    (*DEFAULT_ENV_VARS, "SERENA_HOME")
                    if item == "workflow" and memory_args
                    else DEFAULT_ENV_VARS,
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
        print("updated environment forwarding: " + ", ".join(dict.fromkeys(forwarded)))
    else:
        print("environment forwarding already configured: " + ", ".join(selected_names))
    if memory_args:
        print("Serena Memory backend configured for workflow; reload that MCP server.")
    elif "workflow" in profiles:
        print(
            "Serena Memory is not configured; use --serena-project-root to enable its read tools."
        )
    return 0

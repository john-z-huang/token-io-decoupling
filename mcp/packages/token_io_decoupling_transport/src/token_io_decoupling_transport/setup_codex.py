"""Preflight and configure the two installed local MCP servers in Codex."""

from __future__ import annotations

import argparse
import asyncio
import os
import sysconfig
from copy import deepcopy
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path
from typing import Any

import tomlkit
from mcp import Client, StdioServerParameters
from tomlkit.exceptions import ParseError

from token_io_decoupling_core.server_tools import (
    TOOLS_SERVER_NAME,
    TOOLS_SERVER_TOOLS,
    WORKFLOW_SERVER_NAME,
    WORKFLOW_TOOLS,
)
from token_io_decoupling_transport.codex_env import (
    DEFAULT_ENV_VARS,
    TOOLS_ENV_VARS,
    CodexEnvError,
    ConfigSnapshot,
    atomic_write_config,
    config_path,
    read_config_snapshot,
)
from token_io_decoupling_transport.tool_metadata import STANDARD_INSTALL_NOTICE

_TIMEOUT_SECONDS = 20
_ENTRY_POINTS = {
    WORKFLOW_SERVER_NAME: (
        "token-io-decoupling-workflow",
        "token_io_decoupling_workflow.cli:main",
    ),
    TOOLS_SERVER_NAME: ("token-io-decoupling-tools", "token_io_decoupling_tools.cli:main"),
}


class SetupError(RuntimeError):
    """A safe, user-displayable setup failure."""


@dataclass(frozen=True)
class SetupPlan:
    path: Path
    snapshot: ConfigSnapshot
    rendered: bytes
    changed: bool


def _installed_executable(name: str, value: str) -> Path:
    try:
        distribution = metadata.distribution(name)
        scripts = Path(sysconfig.get_path("scripts"))
    except (metadata.PackageNotFoundError, OSError, TypeError, ValueError) as exc:
        raise SetupError("installed executable metadata is unavailable") from exc
    entry = next(
        (
            item
            for item in distribution.entry_points
            if item.group == "console_scripts" and item.name == name
        ),
        None,
    )
    if entry is None or entry.value != value:
        raise SetupError(f"installed executable metadata is invalid: {name}")
    candidates = [scripts / name]
    if os.name == "nt":
        candidates.append(scripts / f"{name}.exe")
    path = next((candidate for candidate in candidates if candidate.is_file()), None)
    if path is None:
        raise SetupError(f"installed executable is missing: {name}")
    try:
        resolved = path.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise SetupError(f"installed executable cannot be resolved: {name}") from exc
    if not resolved.is_absolute() or (os.name != "nt" and not os.access(resolved, os.X_OK)):
        raise SetupError(f"installed executable is not runnable: {name}")
    return resolved


def _installed_servers(selection: str = "both") -> dict[str, Path]:
    names = {
        "both": (WORKFLOW_SERVER_NAME, TOOLS_SERVER_NAME),
        "workflow": (WORKFLOW_SERVER_NAME,),
        "tools": (TOOLS_SERVER_NAME,),
    }.get(selection)
    if names is None:
        raise SetupError("unknown server selection")
    paths = {name: _installed_executable(*_ENTRY_POINTS[name]) for name in names}
    if len(set(paths.values())) != len(paths):
        raise SetupError("workflow and tools must resolve to distinct installed executables")
    return paths


def _string_list(value: Any, field: str, name: str) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)) or not all(isinstance(item, str) for item in value):
        raise SetupError(f"Codex {field} must contain strings: {name}")
    return tuple(value)


def _servers_table(document: Any) -> Any:
    servers = document.get("mcp_servers")
    if servers is None:
        servers = tomlkit.table()
        document["mcp_servers"] = servers
    if not isinstance(servers, dict):
        raise SetupError("Codex mcp_servers setting must be a table")
    return servers


def _current_table(servers: Any, name: str) -> Any | None:
    server = servers.get(name)
    if server is None:
        return None
    if not isinstance(server, dict):
        raise SetupError(f"Codex server section is malformed: {name}")
    if any(key in server for key in ("url", "http_headers", "env_http_headers")):
        raise SetupError(f"Codex server is not a supported stdio registration: {name}")
    command = server.get("command")
    if not isinstance(command, str) or not command:
        raise SetupError(f"Codex stdio command is invalid: {name}")
    _string_list(server.get("args", []), "args", name)
    if "enabled" in server and not isinstance(server["enabled"], bool):
        raise SetupError(f"Codex enabled state is invalid: {name}")
    if "cwd" in server and not isinstance(server["cwd"], str):
        raise SetupError(f"Codex cwd is invalid: {name}")
    if "env" in server and (
        not isinstance(server["env"], dict)
        or not all(
            isinstance(key, str) and isinstance(value, str) for key, value in server["env"].items()
        )
    ):
        raise SetupError(f"Codex env is invalid: {name}")
    for field in ("enabled_tools", "disabled_tools"):
        if field in server:
            _string_list(server[field], field, name)
    if "default_tools_approval_mode" in server and not isinstance(
        server["default_tools_approval_mode"], str
    ):
        raise SetupError(f"Codex default tools approval mode is invalid: {name}")
    for field in ("startup_timeout_sec", "tool_timeout_sec"):
        if field in server and (
            isinstance(server[field], bool) or not isinstance(server[field], (int, float))
        ):
            raise SetupError(f"Codex {field} is invalid: {name}")
    if "required" in server and not isinstance(server["required"], bool):
        raise SetupError(f"Codex required state is invalid: {name}")
    return server


def _set_launch(server: Any, command: Path) -> None:
    server["command"] = str(command)
    args = server.get("args")
    if hasattr(args, "clear"):
        args.clear()
    else:
        server["args"] = tomlkit.array().multiline(False)


def _append_default_env(server: Any, name: str, env_names: tuple[str, ...]) -> None:
    values = server.get("env_vars")
    if values is None:
        values = tomlkit.array().multiline(False)
        server["env_vars"] = values
    if not isinstance(values, (list, tuple)):
        raise SetupError(f"Codex env_vars must be an array: {name}")
    names: dict[str, str] = {}
    for value in values:
        if isinstance(value, str):
            key, source = value, "local"
        elif isinstance(value, dict):
            key, source = value.get("name"), value.get("source", "local")
            if not isinstance(key, str) or source not in {"local", "remote"}:
                raise SetupError(f"Codex env_vars entry is malformed: {name}")
        else:
            raise SetupError(f"Codex env_vars entry is malformed: {name}")
        if key in names and names[key] != source:
            raise SetupError(f"Codex env_vars source conflict: {name}")
        names[key] = source
    for key in env_names:
        if names.get(key) == "remote":
            raise SetupError(f"Codex env_vars source conflict: {name}")
        if key not in names:
            values.append(key)
            names[key] = "local"


def _parse(snapshot: ConfigSnapshot) -> Any:
    try:
        return tomlkit.parse(snapshot.raw.decode("utf-8"))
    except (UnicodeDecodeError, ParseError) as exc:
        raise SetupError("Codex config is not valid UTF-8 TOML") from exc


def _without_current_tables(document: Any, names: Any = _ENTRY_POINTS) -> bytes:
    copy = deepcopy(document)
    servers = copy.get("mcp_servers")
    if isinstance(servers, dict):
        for name in names:
            servers.pop(name, None)
        if not servers:
            copy.pop("mcp_servers", None)
    return tomlkit.dumps(copy).encode("utf-8")


def _build_plan(paths: dict[str, Path], path: Path) -> SetupPlan:
    try:
        snapshot = read_config_snapshot(path)
    except CodexEnvError as exc:
        raise SetupError(f"Codex config preflight failed: {exc}") from exc
    document = _parse(snapshot)
    original = deepcopy(document)
    servers = _servers_table(document)
    env_names_by_server = {
        WORKFLOW_SERVER_NAME: DEFAULT_ENV_VARS,
        TOOLS_SERVER_NAME: TOOLS_ENV_VARS,
    }
    for name in paths:
        env_names = env_names_by_server[name]
        server = _current_table(servers, name)
        if server is None:
            server = tomlkit.table()
            server["enabled"] = True
            servers[name] = server
        _set_launch(server, paths[name])
        _append_default_env(server, name, env_names)
    if _without_current_tables(original, paths) != _without_current_tables(document, paths):
        raise SetupError("Codex config validation failed; unrelated settings would change")
    rendered = tomlkit.dumps(document).encode("utf-8")
    if rendered != snapshot.raw and snapshot.raw:
        if tomlkit.dumps(original).encode("utf-8") != snapshot.raw:
            raise SetupError(
                "Codex config uses a TOML layout that cannot be safely rewritten "
                "without reformatting"
            )
    return SetupPlan(path, snapshot, rendered, rendered != snapshot.raw)


async def _discover(path: Path, expected: frozenset[str], name: str) -> None:
    try:
        async with asyncio.timeout(_TIMEOUT_SECONDS):
            async with Client(
                StdioServerParameters(command=str(path), args=[]), mode="auto"
            ) as client:
                listed = await client.list_tools()
    except Exception as exc:
        raise SetupError(f"installed MCP discovery failed: {name}") from exc
    names = [tool.name for tool in listed.tools]
    if len(names) != len(set(names)) or set(names) != expected:
        raise SetupError(f"installed MCP inventory is invalid: {name}")


def _validate_installed_discovery(paths: dict[str, Path]) -> None:
    if len(WORKFLOW_TOOLS) != 11 or len(TOOLS_SERVER_TOOLS) != 41:
        raise SetupError("fixed MCP tool manifests do not match the required inventory")
    inventories = {WORKFLOW_SERVER_NAME: WORKFLOW_TOOLS, TOOLS_SERVER_NAME: TOOLS_SERVER_TOOLS}
    for name, path in paths.items():
        asyncio.run(_discover(path, inventories[name], name))


def setup_codex(*, dry_run: bool = False, server: str = "both") -> int:
    paths = _installed_servers(server)
    plan = _build_plan(paths, config_path())
    if dry_run:
        print("Dry run: no MCP executable was started and no Codex configuration was written.")
        for name in paths:
            print(f"Would configure {name}: {paths[name]} (args=[])")
        for name in paths:
            env_names = TOOLS_ENV_VARS if name == TOOLS_SERVER_NAME else DEFAULT_ENV_VARS
            print(f"Would merge environment variable names for {name}: " + ", ".join(env_names))
        print(STANDARD_INSTALL_NOTICE)
        return 0

    _validate_installed_discovery(paths)
    if plan.changed:
        try:
            atomic_write_config(plan.path, plan.snapshot, plan.rendered)
            if read_config_snapshot(plan.path).raw != plan.rendered:
                raise SetupError("Codex config changed after the atomic update; review it manually")
        except CodexEnvError as exc:
            raise SetupError(f"Codex config update failed: {exc}") from exc
        print("configured: " + ", ".join(paths))
        print("updated environment forwarding for selected registrations")
    else:
        print("already configured: " + ", ".join(paths))
    print(STANDARD_INSTALL_NOTICE)
    return 0


def dispatch_setup(server: str, argv: list[str]) -> int:
    """Configure just the executable belonging to the calling distribution."""
    parser = argparse.ArgumentParser(prog=f"token-io-decoupling-{server} setup codex")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    try:
        return setup_codex(server=server, dry_run=args.dry_run)
    except SetupError as exc:
        print(f"setup failed: {exc}")
        return 2

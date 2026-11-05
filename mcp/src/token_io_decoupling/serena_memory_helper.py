"""One-shot, read-only Serena Memory helper for an isolated Serena interpreter."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import stat
import sys
from pathlib import Path
from typing import Any

_MAX_INPUT_BYTES = 450_000
_MAX_CONFIG_BYTES = 1_000_000
_MAX_OUTPUT_BYTES = 1_000_000
_DEFAULT_PROJECT_DATA_DIR = "$projectDir/.serena"
_PROJECT_DIR_TOKEN = re.compile(r"\$([A-Za-z_]\w*)")
_READ_ONLY_BLOCKED_EVENTS = frozenset(
    {
        "os.remove",
        "os.rename",
        "os.rmdir",
        "os.chmod",
        "os.fchmod",
        "os.chown",
        "os.fchown",
        "os.link",
        "os.symlink",
        "os.truncate",
        "os.ftruncate",
        "os.utime",
        "shutil.copyfile",
        "shutil.copymode",
        "shutil.copystat",
        "shutil.move",
        "subprocess.Popen",
        "os.system",
        "os.exec",
        "os.spawn",
        "os.fork",
        "os.posix_spawn",
        "socket.connect",
        "socket.connect_ex",
        "socket.bind",
        "socket.sendto",
        "socket.sendmsg",
        "socket.getaddrinfo",
        "socket.gethostbyname",
        "socket.gethostbyaddr",
        "socket.getnameinfo",
    }
)


class _HelperUnavailable(Exception):
    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


def _read_only_audit(event: str, arguments: tuple[Any, ...]) -> None:
    if event == "os.mkdir":
        path = arguments[0] if arguments else None
        exists = False
        try:
            exists = isinstance(path, (str, bytes, os.PathLike)) and os.path.isdir(path)
        except OSError:
            pass
        if exists:
            # Path.mkdir(exist_ok=True) treats this as its normal existing-directory case.
            raise FileExistsError("read-only helper")
        raise PermissionError("read-only helper")
    if event == "open":
        mode = arguments[1] if len(arguments) > 1 else None
        flags = arguments[2] if len(arguments) > 2 else 0
        write_flags = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND
        if (isinstance(mode, str) and any(flag in mode for flag in "wax+")) or (
            isinstance(flags, int) and flags & write_flags
        ):
            raise PermissionError("read-only helper")
    if event in _READ_ONLY_BLOCKED_EVENTS:
        raise PermissionError("read-only helper")


def _install_read_only_audit_hook() -> None:
    # This fails closed for observable Python audit events; it is not an OS sandbox and cannot
    # constrain native extensions that bypass Python's audit hooks.
    sys.addaudithook(_read_only_audit)


def _failure(action: str, reason: str) -> dict[str, Any]:
    result: dict[str, Any] = {
        "status": "unavailable",
        "reason": reason,
        "reason_code": reason,
    }
    if action == "tail_read":
        result["content"] = ""
    elif action == "write_check":
        result["success"] = False
    return result


def _read_yaml_mapping(path: Path) -> dict[str, Any]:
    try:
        file_stat = path.lstat()
        if stat.S_ISLNK(file_stat.st_mode) or not stat.S_ISREG(file_stat.st_mode):
            raise _HelperUnavailable("serena_config_file_invalid")
        if file_stat.st_size > _MAX_CONFIG_BYTES:
            raise _HelperUnavailable("serena_config_file_too_large")
        with path.open("rb") as stream:
            raw = stream.read(_MAX_CONFIG_BYTES + 1)
        if len(raw) > _MAX_CONFIG_BYTES:
            raise _HelperUnavailable("serena_config_file_too_large")
        yaml_module = importlib.import_module("ruamel.yaml")
        YAML = yaml_module.YAML
        parser = YAML(typ="safe")
        parser.allow_duplicate_keys = False
        value = parser.load(raw.decode("utf-8", errors="strict"))
    except _HelperUnavailable:
        raise
    except Exception as exc:
        raise _HelperUnavailable("serena_config_read_failed") from exc
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise _HelperUnavailable("serena_config_shape_invalid")
    return value


def _patterns(config: dict[str, Any], key: str) -> list[str]:
    value = config.get(key, [])
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise _HelperUnavailable("serena_memory_patterns_invalid")
    return list(value)


def _existing_directory(path: Path, reason: str) -> Path:
    if not path.is_absolute():
        raise _HelperUnavailable(reason)
    try:
        mode = path.lstat().st_mode
        if stat.S_ISLNK(mode) or not stat.S_ISDIR(mode):
            raise _HelperUnavailable(reason)
        resolved = path.resolve(strict=True)
    except _HelperUnavailable:
        raise
    except OSError as exc:
        raise _HelperUnavailable(reason) from exc
    if resolved != path:
        raise _HelperUnavailable(reason)
    return resolved


def _serena_home(environment: dict[str, str]) -> Path:
    configured = environment.get("SERENA_HOME")
    if configured is not None and configured.strip():
        home = Path(configured.strip())
    else:
        home = Path.home() / ".serena"
    return _existing_directory(home, "serena_home_unavailable")


def _project_data_directory(project_root: Path, global_config: dict[str, Any]) -> Path:
    template = global_config.get("project_serena_folder_location", _DEFAULT_PROJECT_DATA_DIR)
    if not isinstance(template, str) or not template:
        raise _HelperUnavailable("project_serena_folder_location_invalid")
    placeholders = {
        "projectDir": str(project_root),
        "projectFolderName": project_root.name,
    }

    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        if name not in placeholders:
            raise _HelperUnavailable("project_serena_folder_placeholder_invalid")
        return placeholders[name]

    configured = Path(os.path.abspath(_PROJECT_DIR_TOKEN.sub(replace, template)))
    default = project_root / ".serena"
    if configured.is_dir():
        return _existing_directory(configured, "project_serena_data_directory_unavailable")
    if configured != default and default.is_dir():
        return _existing_directory(default, "project_serena_data_directory_unavailable")
    raise _HelperUnavailable("project_serena_data_directory_unavailable")


def _load_configuration(
    project_root: str | Path, environment: dict[str, str]
) -> tuple[Path, Path, list[str], list[str]]:
    project = Path(project_root)
    if not project.is_absolute():
        raise _HelperUnavailable("project_root_must_be_absolute")
    try:
        project = project.resolve(strict=True)
    except OSError as exc:
        raise _HelperUnavailable("project_root_unavailable") from exc
    if not project.is_dir():
        raise _HelperUnavailable("project_root_unavailable")

    home = _serena_home(environment)
    global_config = _read_yaml_mapping(home / "serena_config.yml")
    data_directory = _project_data_directory(project, global_config)
    project_config_path = data_directory / "project.yml"
    project_config = _read_yaml_mapping(project_config_path)
    local_path = data_directory / "project.local.yml"
    try:
        local_path.lstat()
    except FileNotFoundError:
        pass
    else:
        project_config.update(_read_yaml_mapping(local_path))

    ignored = _patterns(global_config, "ignored_memory_patterns") + _patterns(
        project_config, "ignored_memory_patterns"
    )
    read_only = _patterns(global_config, "read_only_memory_patterns") + _patterns(
        project_config, "read_only_memory_patterns"
    )
    if global_config.get("edit_global_memories") is False:
        read_only.append("global/.*")
    for pattern in (*ignored, *read_only):
        try:
            re.compile(pattern)
        except re.error as exc:
            raise _HelperUnavailable("serena_memory_pattern_invalid") from exc

    global_memory_root = _existing_directory(
        home / "memories" / "global", "serena_global_memory_directory_unavailable"
    )
    _existing_directory(data_directory / "memories", "serena_project_memory_directory_unavailable")
    return data_directory, global_memory_root, read_only, ignored


def _load_service(service_file: Path, project_root: str | Path) -> Any:
    data_directory, global_root, read_only, ignored = _load_configuration(
        project_root, dict(os.environ)
    )
    if service_file.name != "serena_memory.py" or not service_file.is_absolute():
        raise _HelperUnavailable("serena_service_source_invalid")
    try:
        file_stat = service_file.lstat()
        if stat.S_ISLNK(file_stat.st_mode) or not stat.S_ISREG(file_stat.st_mode):
            raise _HelperUnavailable("serena_service_source_invalid")
        spec = importlib.util.spec_from_file_location(
            "_token_io_decoupling_serena_memory", service_file
        )
        if spec is None or spec.loader is None:
            raise _HelperUnavailable("serena_service_source_invalid")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except _HelperUnavailable:
        raise
    except Exception as exc:
        raise _HelperUnavailable("serena_service_source_invalid") from exc

    try:
        serena_constants = importlib.import_module("serena.constants")
        memory_manager_module = importlib.import_module("serena.memories.memory_manager")
    except Exception as exc:
        raise _HelperUnavailable("serena_manager_unavailable") from exc
    SERENA_FILE_ENCODING = serena_constants.SERENA_FILE_ENCODING
    MemoryManager = memory_manager_module.MemoryManager

    required_parameters = {
        "serena_data_folder",
        "read_only_memory_patterns",
        "ignored_memory_patterns",
    }
    import inspect

    try:
        if not required_parameters.issubset(inspect.signature(MemoryManager).parameters):
            raise _HelperUnavailable("serena_manager_interface_unsupported")
        manager = MemoryManager(
            str(data_directory),
            read_only_memory_patterns=read_only,
            ignored_memory_patterns=ignored,
        )
    except _HelperUnavailable:
        raise
    except Exception as exc:
        raise _HelperUnavailable("serena_manager_initialization_failed") from exc
    if (
        type(manager) is not MemoryManager
        or getattr(manager, "_encoding", None) != SERENA_FILE_ENCODING
        or Path(getattr(manager, "_project_memory_dir", "")) != data_directory / "memories"
        or Path(getattr(manager, "_global_memory_dir", "")) != global_root
    ):
        raise _HelperUnavailable("serena_manager_interface_unsupported")
    try:
        return module.SerenaMemoryReadService(manager, project_root)
    except Exception as exc:
        raise _HelperUnavailable("serena_service_initialization_failed") from exc


def _dispatch(request: dict[str, Any], service: Any) -> dict[str, Any]:
    protocol = request.get("protocol")
    action = request.get("action")
    if protocol != 1 or action not in {"capability", "tail_read", "write_check"}:
        raise _HelperUnavailable("serena_request_invalid")
    if action == "capability":
        if set(request) != {"protocol", "action"}:
            raise _HelperUnavailable("serena_request_invalid")
        return service.capability()
    if action == "tail_read":
        if set(request) != {"protocol", "action", "memory_path", "tail_lines"}:
            raise _HelperUnavailable("serena_request_invalid")
        return service.tail_read(request["memory_path"], request["tail_lines"])
    if set(request) != {
        "protocol",
        "action",
        "memory_path",
        "changed_content",
        "tail_lines",
    }:
        raise _HelperUnavailable("serena_request_invalid")
    return service.write_check(
        request["memory_path"], request["changed_content"], request["tail_lines"]
    )


def _run(service_file: Path, project_root: str | Path) -> int:
    raw = sys.stdin.buffer.read(_MAX_INPUT_BYTES + 1)
    if len(raw) > _MAX_INPUT_BYTES:
        result = _failure("tail_read", "serena_request_too_large")
    else:
        try:
            request = json.loads(raw.decode("ascii"))
            if not isinstance(request, dict):
                raise _HelperUnavailable("serena_request_invalid")
            action = request.get("action")
            if action not in {"capability", "tail_read", "write_check"}:
                raise _HelperUnavailable("serena_request_invalid")
            _install_read_only_audit_hook()
            service = _load_service(service_file, project_root)
            result = _dispatch(request, service)
        except _HelperUnavailable as exc:
            action = locals().get("action", "capability")
            result = _failure(action, exc.reason)
        except Exception:
            action = locals().get("action", "capability")
            result = _failure(action, "serena_helper_internal_error")
    try:
        output = json.dumps(result, ensure_ascii=True, separators=(",", ":")).encode("ascii")
    except (TypeError, ValueError):
        output = json.dumps(_failure("capability", "serena_helper_response_invalid")).encode(
            "ascii"
        )
    if len(output) > _MAX_OUTPUT_BYTES:
        output = json.dumps(_failure("capability", "serena_helper_output_too_large")).encode(
            "ascii"
        )
    sys.stdout.buffer.write(output + b"\n")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--service-file", required=True)
    parser.add_argument("--project-root", required=True)
    args = parser.parse_args()
    return _run(Path(args.service_file), args.project_root)


if __name__ == "__main__":
    raise SystemExit(main())

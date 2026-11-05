"""Isolated process proxy for the read-only Serena Memory service."""

from __future__ import annotations

import json
import os
import selectors
import subprocess
import time
from pathlib import Path
from typing import Any

from token_io_decoupling_workflow import serena_memory
from token_io_decoupling_workflow.serena_memory import SerenaMemoryReadService

MAX_REQUEST_BYTES = 450_000
MAX_RESPONSE_BYTES = 1_000_000
HELPER_TIMEOUT_SECONDS = 20.0
_PROTOCOL_VERSION = 1


class IsolatedSerenaMemoryService(SerenaMemoryReadService):
    """Proxy Memory operations to a fixed helper in the Serena interpreter."""

    def __init__(self, project_root: str | Path, python_executable: str | Path) -> None:
        super().__init__()
        self._project_root = Path(project_root)
        self._python_executable = Path(python_executable)
        self._helper_script = Path(__file__).with_name("serena_memory_helper.py")
        self._service_source = Path(serena_memory.__file__ or "")
        self._timeout_seconds = HELPER_TIMEOUT_SECONDS
        self._configuration_reason: str | None = None

        if not self._project_root.is_absolute():
            self._configuration_reason = "project_root_must_be_absolute"
        elif not self._project_root.is_dir():
            self._configuration_reason = "project_root_unavailable"
        elif not self._python_executable.is_absolute():
            self._configuration_reason = "serena_python_must_be_absolute"
        elif not self._python_executable.is_file() or not os.access(
            self._python_executable, os.X_OK
        ):
            self._configuration_reason = "serena_python_unavailable"
        elif not self._helper_script.is_file() or not self._service_source.is_file():
            self._configuration_reason = "serena_helper_unavailable"

    def capability(self) -> dict[str, Any]:
        if self._configuration_reason:
            return self._failure(self._configuration_reason)
        return self._invoke("capability", {})

    def tail_read(self, memory_path: str, tail_lines: int) -> dict[str, Any]:
        if self._configuration_reason:
            return self._failure(self._configuration_reason)
        return self._invoke("tail_read", {"memory_path": memory_path, "tail_lines": tail_lines})

    def write_check(
        self, memory_path: str, changed_content: str, tail_lines: int
    ) -> dict[str, Any]:
        if self._configuration_reason:
            return self._check_failure(self._configuration_reason)
        return self._invoke(
            "write_check",
            {
                "memory_path": memory_path,
                "changed_content": changed_content,
                "tail_lines": tail_lines,
            },
        )

    def _invoke(self, action: str, arguments: dict[str, Any]) -> dict[str, Any]:
        request = {"protocol": _PROTOCOL_VERSION, "action": action, **arguments}
        try:
            request_bytes = json.dumps(request, ensure_ascii=True, separators=(",", ":")).encode(
                "ascii"
            )
        except (TypeError, ValueError):
            return self._unavailable_for(action, "serena_request_invalid")
        if len(request_bytes) > MAX_REQUEST_BYTES:
            return self._unavailable_for(action, "serena_request_too_large")

        environment = {
            key: value
            for key, value in os.environ.items()
            if key
            in {
                "PATH",
                "HOME",
                "USERPROFILE",
                "SERENA_HOME",
                "LANG",
                "LC_ALL",
                "LC_CTYPE",
                "TMPDIR",
            }
        }
        command = [
            str(self._python_executable),
            "-B",
            "-I",
            str(self._helper_script),
            "--service-file",
            str(self._service_source),
            "--project-root",
            str(self._project_root),
        ]
        deadline = time.monotonic() + self._timeout_seconds
        try:
            process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                cwd=self._project_root,
                env=environment,
                close_fds=True,
                shell=False,
            )
        except (OSError, ValueError):
            return self._unavailable_for(action, "serena_helper_start_failed")

        try:
            response = self._exchange(process, request_bytes, deadline)
        except TimeoutError:
            self._terminate(process)
            return self._unavailable_for(action, "serena_helper_timeout")
        except _HelperOutputTooLarge:
            self._terminate(process)
            return self._unavailable_for(action, "serena_helper_output_too_large")
        except (OSError, ValueError):
            self._terminate(process)
            return self._unavailable_for(action, "serena_helper_io_failed")
        finally:
            self._close_process_pipes(process)

        try:
            returncode = process.wait(timeout=max(deadline - time.monotonic(), 0.1))
        except subprocess.TimeoutExpired:
            self._terminate(process)
            return self._unavailable_for(action, "serena_helper_timeout")
        if returncode != 0:
            return self._unavailable_for(action, "serena_helper_failed")
        try:
            decoded = json.loads(response.decode("ascii"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return self._unavailable_for(action, "serena_helper_response_invalid")
        if not isinstance(decoded, dict) or not self._valid_response(action, decoded, arguments):
            return self._unavailable_for(action, "serena_helper_response_invalid")
        return decoded

    def _exchange(self, process: subprocess.Popen[bytes], payload: bytes, deadline: float) -> bytes:
        if process.stdin is None or process.stdout is None:
            raise OSError("helper pipes are unavailable")
        stdin_fd = process.stdin.fileno()
        stdout_fd = process.stdout.fileno()
        os.set_blocking(stdin_fd, False)
        os.set_blocking(stdout_fd, False)
        selector = selectors.DefaultSelector()
        output = bytearray()
        written = 0
        stdin_open = True
        stdout_open = True
        try:
            selector.register(process.stdin, selectors.EVENT_WRITE, "stdin")
            selector.register(process.stdout, selectors.EVENT_READ, "stdout")
            while stdin_open or stdout_open:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError
                events = selector.select(remaining)
                if not events and process.poll() is None:
                    continue
                for key, mask in events:
                    if key.data == "stdin" and mask & selectors.EVENT_WRITE:
                        try:
                            count = os.write(stdin_fd, payload[written : written + 65_536])
                        except BrokenPipeError:
                            count = 0
                        if count <= 0:
                            selector.unregister(process.stdin)
                            process.stdin.close()
                            stdin_open = False
                        else:
                            written += count
                            if written == len(payload):
                                selector.unregister(process.stdin)
                                process.stdin.close()
                                stdin_open = False
                    elif key.data == "stdout" and mask & selectors.EVENT_READ:
                        chunk = os.read(stdout_fd, 65_536)
                        if not chunk:
                            selector.unregister(process.stdout)
                            process.stdout.close()
                            stdout_open = False
                        else:
                            output.extend(chunk)
                            if len(output) > MAX_RESPONSE_BYTES:
                                raise _HelperOutputTooLarge
                if process.poll() is not None and not events and stdout_open:
                    continue
            return bytes(output)
        finally:
            selector.close()

    def _valid_response(
        self, action: str, response: dict[str, Any], arguments: dict[str, Any]
    ) -> bool:
        statuses = {
            "capability": {"configured", "unavailable"},
            "tail_read": {"available", "unavailable"},
            "write_check": {"available", "unavailable"},
        }
        if response.get("status") not in statuses.get(action, set()):
            return False
        if not isinstance(response.get("reason"), str) and not isinstance(
            response.get("reason_code"), str
        ):
            return False
        if response["status"] == "unavailable":
            if action == "tail_read":
                return response.get("content") == ""
            if action == "write_check":
                return response.get("success") is False
            return True
        if action == "capability":
            project_root = self._project_root
            if not isinstance(project_root, Path):
                return False
            try:
                expected_root = str(project_root.resolve(strict=True))
            except OSError:
                return False
            return (
                response.get("project_root") == expected_root
                and isinstance(response.get("project_memory_root"), str)
                and Path(response["project_memory_root"]).is_absolute()
                and isinstance(response.get("global_memory_root"), str)
                and Path(response["global_memory_root"]).is_absolute()
                and response.get("encoding") == "utf-8"
                and response.get("max_tail_lines") == 10_000
                and response.get("max_content_chars") == 64_000
            )
        if action == "tail_read":
            content = response.get("content")
            total = response.get("total_lines")
            returned = response.get("returned_lines")
            requested = response.get("requested_tail_lines")
            start = response.get("start_line")
            end = response.get("end_line")
            return (
                isinstance(content, str)
                and len(content) <= 64_000
                and isinstance(total, int)
                and not isinstance(total, bool)
                and total >= 0
                and isinstance(returned, int)
                and not isinstance(returned, bool)
                and returned >= 0
                and returned <= total
                and requested == arguments.get("tail_lines")
                and isinstance(requested, int)
                and not isinstance(requested, bool)
                and 0 <= requested <= 10_000
                and returned <= requested
                and isinstance(response.get("ends_with_newline"), bool)
                and isinstance(response.get("memory_name"), str)
                and isinstance(response.get("resolved_path"), str)
                and Path(response["resolved_path"]).is_absolute()
                and (
                    (returned == 0 and start is None and end is None)
                    or (
                        isinstance(start, int)
                        and not isinstance(start, bool)
                        and isinstance(end, int)
                        and not isinstance(end, bool)
                        and start >= 1
                        and end >= start
                        and end <= total
                        and end - start + 1 == returned
                    )
                )
            )
        if action == "write_check":
            success = response.get("success")
            start = response.get("match_start")
            end = response.get("match_end")
            returned = response.get("returned_lines")
            requested = response.get("requested_tail_lines")
            total = response.get("total_lines")
            if (
                not isinstance(success, bool)
                or response.get("match_scope") != "current_tail_content_only"
                or requested != arguments.get("tail_lines")
                or not isinstance(requested, int)
                or isinstance(requested, bool)
                or not 0 <= requested <= 10_000
                or not isinstance(total, int)
                or isinstance(total, bool)
                or total < 0
                or not isinstance(returned, int)
                or isinstance(returned, bool)
                or not 0 <= returned <= min(total, requested)
                or not isinstance(response.get("memory_name"), str)
            ):
                return False
            if success:
                changed = arguments.get("changed_content")
                return (
                    isinstance(changed, str)
                    and isinstance(start, int)
                    and not isinstance(start, bool)
                    and isinstance(end, int)
                    and not isinstance(end, bool)
                    and start >= 0
                    and end - start == len(changed)
                    and response.get("reason_code") == "memory_tail_match"
                )
            return (
                start is None
                and end is None
                and response.get("reason_code") == "memory_tail_no_match"
            )
        return False

    @staticmethod
    def _terminate(process: subprocess.Popen[bytes]) -> None:
        if process.poll() is None:
            process.kill()
        try:
            process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            pass

    @staticmethod
    def _close_process_pipes(process: subprocess.Popen[bytes]) -> None:
        for stream in (process.stdin, process.stdout):
            if stream is not None and not stream.closed:
                stream.close()

    @staticmethod
    def _unavailable_for(action: str, reason: str) -> dict[str, Any]:
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

    @classmethod
    def _failure(cls, reason: str) -> dict[str, Any]:
        return cls._unavailable_for("capability", reason)

    @classmethod
    def _check_failure(cls, reason: str) -> dict[str, Any]:
        return cls._unavailable_for("write_check", reason)


class _HelperOutputTooLarge(Exception):
    pass

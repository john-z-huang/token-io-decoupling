from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

from token_io_decoupling.serena_memory_runtime import (
    MAX_REQUEST_BYTES,
    MAX_RESPONSE_BYTES,
    IsolatedSerenaMemoryService,
    _HelperOutputTooLarge,
)


def _service(tmp_path: Path) -> IsolatedSerenaMemoryService:
    project = tmp_path / "project"
    project.mkdir()
    python = tmp_path / "serena-env" / "bin" / "python"
    python.parent.mkdir(parents=True)
    python.touch()
    python.chmod(0o755)
    return IsolatedSerenaMemoryService(project, python)


def test_proxy_uses_lexical_interpreter_and_bounded_environment(tmp_path: Path) -> None:
    service = _service(tmp_path)
    assert service._project_root is not None
    process = Mock(returncode=0)
    process.wait.return_value = 0
    process.poll.return_value = None
    process.stdin = None
    process.stdout = None
    captured: dict[str, Any] = {}

    def start_process(command: list[str], **kwargs: Any) -> Mock:
        captured["command"] = command
        captured["kwargs"] = kwargs
        return process

    with (
        patch(
            "token_io_decoupling.serena_memory_runtime.subprocess.Popen", side_effect=start_process
        ),
        patch.dict("os.environ", {"OPENAI_API_KEY": "secret", "OPENAI_BASE_URL": "secret-url"}),
        patch.object(
            service,
            "_exchange",
            return_value=json.dumps(
                {
                    "status": "configured",
                    "reason_code": "ok",
                    "project_root": str(service._project_root.resolve()),
                    "project_memory_root": "/project/memories",
                    "global_memory_root": "/global/memories",
                    "encoding": "utf-8",
                    "max_tail_lines": 10_000,
                    "max_content_chars": 64_000,
                }
            ).encode(),
        ),
    ):
        result = service.capability()

    assert result["status"] == "configured"
    command = captured["command"]
    assert command[0].endswith("serena-env/bin/python")
    assert command[1:3] == ["-B", "-I"]
    assert captured["kwargs"]["shell"] is False
    assert captured["kwargs"]["stderr"] is not None
    environment = captured["kwargs"]["env"]
    assert "OPENAI_API_KEY" not in environment
    assert "OPENAI_BASE_URL" not in environment
    assert set(environment) <= {
        "PATH",
        "HOME",
        "USERPROFILE",
        "SERENA_HOME",
        "LANG",
        "LC_ALL",
        "LC_CTYPE",
        "TMPDIR",
    }


def test_proxy_rejects_oversized_request_before_starting_helper(tmp_path: Path) -> None:
    service = _service(tmp_path)
    with patch("token_io_decoupling.serena_memory_runtime.subprocess.Popen") as popen:
        result = service.write_check("mem:notes", "x" * MAX_REQUEST_BYTES, 1)
    assert result["status"] == "unavailable"
    assert result["reason_code"] == "serena_request_too_large"
    assert result["success"] is False
    popen.assert_not_called()


def test_proxy_maps_helper_output_limit_and_validates_wire_result(tmp_path: Path) -> None:
    service = _service(tmp_path)
    process = Mock(returncode=0)
    process.wait.return_value = 0
    process.stdin = None
    process.stdout = None
    with (
        patch("token_io_decoupling.serena_memory_runtime.subprocess.Popen", return_value=process),
        patch.object(service, "_exchange", side_effect=_HelperOutputTooLarge),
    ):
        result = service.tail_read("mem:notes", 2)
    assert result["status"] == "unavailable"
    assert result["reason_code"] == "serena_helper_output_too_large"
    assert result["content"] == ""

    with (
        patch("token_io_decoupling.serena_memory_runtime.subprocess.Popen", return_value=process),
        patch.object(service, "_exchange", return_value=b'{"status":"available"}'),
    ):
        invalid = service.write_check("mem:notes", "text", 2)
    assert invalid["status"] == "unavailable"
    assert invalid["reason_code"] == "serena_helper_response_invalid"


def test_proxy_maps_timeout_bad_json_and_nonzero_exit(tmp_path: Path) -> None:
    service = _service(tmp_path)
    process = Mock(returncode=0)
    process.wait.return_value = 0
    process.poll.return_value = None
    with (
        patch("token_io_decoupling.serena_memory_runtime.subprocess.Popen", return_value=process),
        patch.object(service, "_exchange", side_effect=TimeoutError),
    ):
        timeout = service.tail_read("mem:notes", 2)
    assert timeout["reason_code"] == "serena_helper_timeout"
    process.kill.assert_called_once()

    process = Mock(returncode=0)
    process.wait.return_value = 0
    with (
        patch("token_io_decoupling.serena_memory_runtime.subprocess.Popen", return_value=process),
        patch.object(service, "_exchange", return_value=b"not-json"),
    ):
        bad_json = service.tail_read("mem:notes", 2)
    assert bad_json["reason_code"] == "serena_helper_response_invalid"

    process = Mock(returncode=9)
    process.wait.return_value = 9
    with (
        patch("token_io_decoupling.serena_memory_runtime.subprocess.Popen", return_value=process),
        patch.object(
            service,
            "_exchange",
            return_value=b'{"status":"configured","reason_code":"ok"}',
        ),
    ):
        failed = service.capability()
    assert failed["reason_code"] == "serena_helper_failed"


def test_proxy_requires_capability_binding_and_tail_evidence(tmp_path: Path) -> None:
    service = _service(tmp_path)
    process = Mock(returncode=0)
    process.wait.return_value = 0
    invalid_capability = {
        "status": "configured",
        "reason_code": "ok",
        "project_root": "/wrong",
        "project_memory_root": "/project/memories",
        "global_memory_root": "/global/memories",
        "encoding": "utf-8",
        "max_tail_lines": 10_000,
        "max_content_chars": 64_000,
    }
    with (
        patch("token_io_decoupling.serena_memory_runtime.subprocess.Popen", return_value=process),
        patch.object(service, "_exchange", return_value=json.dumps(invalid_capability).encode()),
    ):
        assert service.capability()["reason_code"] == "serena_helper_response_invalid"

    tail = {
        "status": "available",
        "reason_code": "memory_tail_read",
        "content": "one\n",
        "total_lines": 1,
        "returned_lines": 1,
        "requested_tail_lines": 1,
        "start_line": 1,
        "end_line": 1,
        "ends_with_newline": True,
        "memory_name": "notes",
        "resolved_path": "/project/memories/notes.md",
    }
    with (
        patch("token_io_decoupling.serena_memory_runtime.subprocess.Popen", return_value=process),
        patch.object(service, "_exchange", return_value=json.dumps(tail).encode()),
    ):
        assert service.tail_read("mem:notes", 1)["status"] == "available"
    tail.pop("end_line")
    with (
        patch("token_io_decoupling.serena_memory_runtime.subprocess.Popen", return_value=process),
        patch.object(service, "_exchange", return_value=json.dumps(tail).encode()),
    ):
        assert service.tail_read("mem:notes", 1)["reason_code"] == "serena_helper_response_invalid"

    check = {
        "status": "available",
        "reason_code": "memory_tail_match",
        "success": True,
        "memory_name": "notes",
        "requested_tail_lines": 1,
        "total_lines": 1,
        "returned_lines": 1,
        "match_start": 0,
        "match_end": 3,
        "match_scope": "current_tail_content_only",
    }
    with (
        patch("token_io_decoupling.serena_memory_runtime.subprocess.Popen", return_value=process),
        patch.object(service, "_exchange", return_value=json.dumps(check).encode()),
    ):
        assert service.write_check("mem:notes", "one", 1)["success"] is True
    check["match_end"] = 2
    with (
        patch("token_io_decoupling.serena_memory_runtime.subprocess.Popen", return_value=process),
        patch.object(service, "_exchange", return_value=json.dumps(check).encode()),
    ):
        assert service.write_check("mem:notes", "one", 1)["reason_code"] == (
            "serena_helper_response_invalid"
        )


def test_exchange_enforces_real_process_timeout_and_stdout_limit(tmp_path: Path) -> None:
    service = _service(tmp_path)
    output_script = (
        "import sys; sys.stdin.buffer.read(1); "
        f"sys.stdout.buffer.write(b'x' * {MAX_RESPONSE_BYTES + 1})"
    )
    large = subprocess.Popen(
        [sys.executable, "-c", output_script],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    try:
        try:
            service._exchange(large, b"x", time.monotonic() + 5)
        except _HelperOutputTooLarge:
            pass
        else:
            raise AssertionError("oversized output was accepted")
    finally:
        service._terminate(large)
        service._close_process_pipes(large)

    hanging = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(10)"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    try:
        try:
            service._exchange(hanging, b"x", time.monotonic() + 0.1)
        except TimeoutError:
            pass
        else:
            raise AssertionError("helper timeout was not enforced")
    finally:
        service._terminate(hanging)
        service._close_process_pipes(hanging)

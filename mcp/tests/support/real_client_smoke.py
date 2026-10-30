"""Exercise installed Codex client runtimes through their real app-server MCP API."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import queue
import re
import signal
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

WORKSPACE = Path(__file__).resolve().parents[2]
SERVER = "token-io-real-client-smoke"


class AppServer:
    """Own one subprocess group and an ephemeral, model-free test fixture."""

    def __init__(self, executable: Path) -> None:
        listing = subprocess.run(
            [str(executable), "mcp", "list", "--json"],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
        disabled = []
        self.disabled_names: set[str] = set()
        for entry in json.loads(listing.stdout):
            # Keep only names/types; never copy transport URLs, arguments, env, or credentials.
            name = json.dumps(entry["name"])
            if entry["name"] != SERVER:
                self.disabled_names.add(entry["name"])
            transport_type = entry["transport"]["type"]
            if transport_type == "stdio":
                transport = 'command="/usr/bin/false"'
            elif transport_type == "streamable_http":
                transport = 'url="http://127.0.0.1:9"'
            else:
                raise RuntimeError("unsupported_mcp_transport_for_isolation")
            disabled.append(name + "={enabled=false," + transport + "}")
        config = {
            "command": sys.executable,
            "args": ["-m", "token_io_decoupling.cli", "start-mcp-server", "--profile", "workflow"],
            "cwd": str(WORKSPACE),
            "enabled": True,
            "env": {"PYTHONPATH": ""},
            "env_vars": [],
            "startup_timeout_sec": 30,
        }
        fields = ", ".join(
            f"{key}=" + ('{PYTHONPATH=""}' if key == "env" else json.dumps(value))
            for key, value in config.items()
        )
        # Replace the entire table for this process; never read/copy credential-bearing config.
        entries = disabled + [SERVER + "={" + fields + "}"]
        override = "mcp_servers={" + ",".join(entries) + "}"
        environment = os.environ.copy()
        environment.pop("PYTHONPATH", None)
        self.process = subprocess.Popen(
            [str(executable), "-c", override, "app-server", "--stdio"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            env=environment,
            start_new_session=True,
        )
        self.messages: queue.Queue[dict[str, Any] | None] = queue.Queue()
        self.request_id = 0
        self.requested_methods: list[str] = []
        self.reader = threading.Thread(target=self._read, daemon=True)
        self.reader.start()

    def _read(self) -> None:
        assert self.process.stdout is not None
        try:
            for line in self.process.stdout:
                try:
                    self.messages.put(json.loads(line))
                except ValueError:
                    self.messages.put({"invalid_json": True})
        finally:
            self.messages.put(None)

    def send(self, message: dict[str, Any]) -> None:
        assert self.process.stdin is not None
        self.process.stdin.write(json.dumps(message) + "\n")
        self.process.stdin.flush()

    def request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        self.requested_methods.append(method)
        self.request_id += 1
        self.send({"id": self.request_id, "method": method, "params": params})
        deadline = time.monotonic() + 45
        while True:
            try:
                message = self.messages.get(timeout=max(0.01, deadline - time.monotonic()))
            except queue.Empty:
                raise RuntimeError(f"app_server_timeout:{method}") from None
            if message is None:
                raise RuntimeError(f"app_server_closed:{method}")
            if message.get("invalid_json"):
                raise RuntimeError("app_server_invalid_json")
            if message.get("id") == self.request_id:
                if "error" in message:
                    raise RuntimeError(f"app_server_rpc_rejected:{method}")
                return message["result"]
            if "id" in message:
                # Do not approve elicitation, start model turns, or handle unexpected host actions.
                raise RuntimeError("unexpected_app_server_request")
            if time.monotonic() >= deadline:
                raise RuntimeError(f"app_server_timeout:{method}")

    def close(self) -> None:
        # Ephemeral threads are memory-only and cannot be archived. Reap the owned process group.
        try:
            os.killpg(self.process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(self.process.pid, signal.SIGKILL)
            self.process.wait(timeout=5)
        finally:
            for stream in (self.process.stdin, self.process.stdout):
                if stream is not None:
                    stream.close()
            self.reader.join(timeout=2)


def exercise_client(executable: Path, client: str) -> dict[str, Any]:
    if os.name != "posix":
        raise RuntimeError("real_client_smoke_requires_posix_process_groups")
    executable = executable.resolve(strict=True)
    version = subprocess.run(
        [str(executable), "--version"], capture_output=True, text=True, check=True, timeout=15
    ).stdout.strip()
    if not re.fullmatch(r"codex-cli [0-9A-Za-z.+-]+", version):
        raise RuntimeError("unexpected_client_version_format")
    source_paths = [
        "packages/token_io_decoupling_transport/src/token_io_decoupling_transport/identity.py",
        "packages/token_io_decoupling_transport/src/token_io_decoupling_transport/tool_metadata.py",
        "packages/token_io_decoupling_workflow/src/token_io_decoupling_workflow/capabilities.py",
        "packages/token_io_decoupling_workflow/src/token_io_decoupling_workflow/tools.py",
        "src/token_io_decoupling/server.py",
    ]
    app = AppServer(executable)
    try:
        app.request(
            "initialize",
            {
                "clientInfo": {"name": "token_io_real_client_smoke", "version": "1"},
                "capabilities": {"experimentalApi": True},
            },
        )
        app.send({"method": "initialized", "params": {}})
        with tempfile.TemporaryDirectory(prefix="token-io-client-smoke-") as directory:
            thread = app.request("thread/start", {"cwd": directory, "ephemeral": True})["thread"]
            assert thread["ephemeral"] is True
            assert thread["turns"] == []
            thread_id = thread["id"]
            status = app.request(
                "mcpServerStatus/list",
                {
                    "threadId": thread_id,
                    "detail": "toolsAndAuthOnly",
                },
            )
            assert status["nextCursor"] is None
            for entry in status["data"]:
                if entry["name"] in app.disabled_names:
                    assert not entry["tools"]
            # Clients can retain built-in platform services outside mcp_servers configuration.
            targets = [entry for entry in status["data"] if entry["name"] == SERVER]
            assert len(targets) == 1
            tools = targets[0]["tools"]
            tool = tools["workflow_capabilities"]
            assert tool["inputSchema"]["properties"] == {}
            assert "capability_details" in tool["description"]
            assert "reason_code" in tool["description"]
            params = {"threadId": thread_id, "server": SERVER}
            result = app.request(
                "mcpServer/tool/call",
                {
                    **params,
                    "tool": "workflow_capabilities",
                    "arguments": {},
                },
            )
            assert result.get("isError") is False
            report = json.loads(result["content"][0]["text"])
            details = report["capability_details"]
            assert report["agent_runtime"] == "codex_cli"
            assert details["schema_version"] == 2
            assert details["support"]["agent_runtime"]["reason_code"] == "fixed_codex_cli"
            configuration = details["configuration"]
            for name in ("caller_match", "api_decisions"):
                entry = configuration[name]
                assert (entry["status"], entry["reason_code"]) == (
                    "disabled",
                    "configured_disabled",
                )
            task_plan_tools = configuration["task_plan_tools"]
            assert (task_plan_tools["status"], task_plan_tools["reason_code"]) == (
                "unavailable",
                "task_plan_backend_not_configured",
            )
            runtime = details["runtime"]
            assert runtime["binding"]["status"] == "unverified"
            assert runtime["binding"]["reason_code"] == "provider_not_configured"
            assert runtime["server_mode"]["status"] == "public_only"
            assert report["enhanced_binding"] == "unverified"
            assert report["binding_transport"] == "unavailable"
            assert all(runtime["binding"][key] for key in ("message", "source", "next_step"))
            denied = app.request(
                "mcpServer/tool/call",
                {
                    **params,
                    "tool": "workflow_evaluate",
                    "arguments": {"payload": {}},
                },
            )
            assert denied["isError"] is True
            assert (
                "trusted host binding or required guard is unavailable"
                in (denied["content"][0]["text"])
            )
            assert not any(method.startswith("turn/") for method in app.requested_methods)
    finally:
        app.close()
    return {
        "client": client,
        "executable": str(executable),
        "version": version,
        "executable_sha256": hashlib.sha256(executable.read_bytes()).hexdigest(),
        "source_sha256": {
            path: hashlib.sha256((WORKSPACE / path).read_bytes()).hexdigest()
            for path in source_paths
        },
        "checks": [
            "configured_servers_disabled",
            "tool_schema_and_description",
            "capability_details",
            "protected_call_denied",
        ],
        "model_turns": 0,
        "ephemeral_thread": True,
        "scope": "installed Codex MCP host-runtime API; no GUI or existing-daemon validation",
        "status": "passed",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--executable", type=Path, required=True)
    parser.add_argument("--client", choices=("codex-cli", "chatgpt-desktop-codex"), required=True)
    args = parser.parse_args()
    try:
        result = exercise_client(args.executable, args.client)
    except Exception as exc:
        # Never expose raw CLI/config/host errors.
        reason = "real_client_smoke_failed"
        if isinstance(exc, RuntimeError) and re.fullmatch(
            r"app_server_[a-z_]+:[a-zA-Z/]+", str(exc)
        ):
            reason = str(exc)
        print(
            json.dumps({"status": "failed", "reason": reason, "failure_type": type(exc).__name__})
        )
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

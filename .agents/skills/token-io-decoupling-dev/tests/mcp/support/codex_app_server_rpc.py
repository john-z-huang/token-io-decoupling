"""仅测试使用的同步 App Server stdio JSON-RPC 传输。"""

from __future__ import annotations

import json
import os
import queue
import signal
import subprocess
import threading
import time
from pathlib import Path
from typing import Any


class AppServerClient:
    """拥有独立进程组；禁止模型轮次及未列出的 RPC，丢弃原始诊断。"""

    METHODS = frozenset(
        {
            "initialize",
            "config/read",
            "thread/start",
            "command/exec",
            "mcpServerStatus/list",
            "mcpServer/tool/call",
        }
    )

    def __init__(self, executable: Path, overrides, environment, directory: Path):
        if os.name != "posix":
            raise RuntimeError("app_server_requires_posix_process_groups")
        command = [str(executable)]
        for override in overrides:
            command.extend(["-c", override])
        command.extend(["app-server", "--listen", "stdio://"])
        self.messages: queue.Queue[Any] = queue.Queue()
        self.request_id = 0
        self.process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            env={**os.environ, **environment},
            cwd=directory,
            start_new_session=True,
        )
        self.reader = threading.Thread(target=self._read, daemon=True)
        try:
            self.reader.start()
        except Exception:
            self.close()
            raise

    def _read(self):
        assert self.process.stdout is not None
        try:
            for line in self.process.stdout:
                try:
                    message = json.loads(line)
                except ValueError:
                    message = False
                self.messages.put(message)
        except (OSError, UnicodeError):
            self.messages.put(False)
        finally:
            self.messages.put(None)

    def _send(self, message):
        assert self.process.stdin is not None
        self.process.stdin.write(json.dumps(message) + "\n")
        self.process.stdin.flush()

    def initialize(self):
        self.request(
            "initialize",
            {
                "clientInfo": {
                    "name": "token_io_final_inspection",
                    "title": "Token I/O test",
                    "version": "1",
                },
                "capabilities": {"experimentalApi": True},
            },
        )
        self._send({"method": "initialized", "params": {}})

    def request(self, method, params, *, timeout=45):
        if method not in self.METHODS:
            raise RuntimeError("app_server_method_not_allowed")
        self.request_id += 1
        self._send({"id": self.request_id, "method": method, "params": params})
        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise RuntimeError("app_server_timeout")
            try:
                message = self.messages.get(timeout=remaining)
            except queue.Empty:
                raise RuntimeError("app_server_timeout") from None
            if message is None:
                raise RuntimeError("app_server_closed")
            if not isinstance(message, dict):
                raise RuntimeError("app_server_invalid_message")
            if "id" not in message and isinstance(message.get("method"), str):
                continue
            if "method" in message or message.get("id") != self.request_id:
                raise RuntimeError("app_server_unexpected_request_or_response")
            if "error" in message:
                raise RuntimeError("app_server_rpc_rejected")
            if not isinstance(message.get("result"), dict):
                raise RuntimeError("app_server_invalid_result")
            return message["result"]

    def close(self):
        # 连同 MCP 子进程一起终止；超时后强制回收，不依赖服务端主动退出。
        try:
            os.killpg(self.process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        except PermissionError:
            if self.process.poll() is None:
                raise
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(self.process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            self.process.wait(timeout=5)
        finally:
            if self.reader.ident is not None:
                self.reader.join(timeout=2)
            for stream in (self.process.stdin, self.process.stdout):
                if stream is not None:
                    stream.close()

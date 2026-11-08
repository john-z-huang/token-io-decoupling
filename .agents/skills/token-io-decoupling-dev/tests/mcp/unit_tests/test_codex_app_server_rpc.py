"""使用本地协议替身验证 App Server 传输，不启动 Codex 或模型。"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from support.codex_app_server_rpc import AppServerClient

SERVER = """
import json
import sys
import time
mode = sys.argv[1]
initialized = False
for line in sys.stdin:
    message = json.loads(line)
    method = message['method']
    if method == 'initialized':
        initialized = True
        continue
    if method == 'initialize':
        result = {'experimental': message['params']['capabilities']['experimentalApi']}
    elif method == 'config/read':
        result = {'initialized': initialized}
        if mode == 'error':
            response = {'id': message['id'], 'error': {'message': 'synthetic-secret'}}
            print(json.dumps(response), flush=True)
            continue
        if mode == 'eof':
            break
        if mode == 'timeout':
            time.sleep(10)
            continue
        if mode == 'invalid':
            print('not-json synthetic-secret', flush=True)
            continue
        if mode == 'request':
            print(json.dumps({'id': 99, 'method': 'approval/request'}), flush=True)
            continue
        if mode == 'mismatch':
            print(json.dumps({'id': 999, 'result': {}}), flush=True)
            continue
        if mode == 'bad_result':
            result = []
    else:
        raise AssertionError(method)
    print(json.dumps({'method': 'notification/test', 'params': {}}), flush=True)
    print(json.dumps({'id': message['id'], 'result': result}), flush=True)
"""


@pytest.fixture
def launch(tmp_path, monkeypatch):
    script = tmp_path / "fake_server.py"
    script.write_text(SERVER)
    popen = subprocess.Popen
    captured = {}

    def start(executable, **kwargs):
        captured.update(command=executable, **kwargs)
        captured["env"] = {"CODEX_HOME": kwargs["env"]["CODEX_HOME"]}
        return popen([sys.executable, str(script), captured.pop("mode")], **kwargs)

    monkeypatch.setattr(subprocess, "Popen", start)

    def client(mode="ok"):
        captured["mode"] = mode
        return AppServerClient(
            Path("/installed/codex"),
            ['model="gpt-6-luna"'],
            {"CODEX_HOME": str(tmp_path)},
            tmp_path,
        )

    return client, captured


def test_handshake_notifications_launch_settings_and_cleanup(launch):
    start, captured = launch
    client = start()
    try:
        client.initialize()
        assert client.request("config/read", {}) == {"initialized": True}
        assert captured["command"] == [
            "/installed/codex",
            "-c",
            'model="gpt-6-luna"',
            "app-server",
            "--listen",
            "stdio://",
        ]
        assert captured["env"]["CODEX_HOME"] == str(captured["cwd"])
        assert captured["stderr"] == subprocess.DEVNULL
        assert captured["start_new_session"] is True
    finally:
        client.close()
    assert client.process.poll() is not None
    assert not client.reader.is_alive()
    assert client.process.stdin.closed
    assert client.process.stdout.closed


@pytest.mark.parametrize(
    "mode,reason",
    [
        ("error", "rpc_rejected"),
        ("invalid", "invalid_message"),
        ("eof", "closed"),
        ("timeout", "timeout"),
        ("request", "unexpected_request_or_response"),
        ("mismatch", "unexpected_request_or_response"),
        ("bad_result", "invalid_result"),
    ],
)
def test_protocol_failures_are_bounded_and_cleanup_process(launch, mode, reason):
    start, _ = launch
    client = start(mode)
    try:
        client.initialize()
        with pytest.raises(RuntimeError, match=reason) as error:
            client.request("config/read", {}, timeout=0.1)
        assert "synthetic-secret" not in str(error.value)
    finally:
        client.close()
    assert client.process.poll() is not None
    assert not client.reader.is_alive()


def test_turn_and_unknown_methods_are_rejected_before_sending(launch):
    start, _ = launch
    client = start()
    try:
        for method in ("turn/start", "config/value/write", "unknown"):
            with pytest.raises(RuntimeError, match="method_not_allowed"):
                client.request(method, {})
        assert client.request_id == 0
    finally:
        client.close()

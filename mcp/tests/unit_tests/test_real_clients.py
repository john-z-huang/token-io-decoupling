"""Opt-in integration checks against the installed client runtimes, without mocked hosts."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[2]
DESKTOP_CODEX = (
    "/Applications/ChatGPT.app/Contents/Resources/codex-cli/CodexCLI.app/Contents/MacOS/codex"
)
pytestmark = [
    pytest.mark.real_client,
    pytest.mark.skipif(
        os.environ.get("TOKEN_IO_RUN_REAL_CLIENTS") != "1",
        reason="set TOKEN_IO_RUN_REAL_CLIENTS=1 to test installed client runtimes",
    ),
]


@pytest.mark.parametrize("client", ["codex-cli", "chatgpt-desktop-codex"])
def test_installed_client_runtime(client: str) -> None:
    if client == "codex-cli":
        executable = os.environ.get("TOKEN_IO_CODEX_CLI_PATH") or shutil.which("codex")
    else:
        executable = os.environ.get("TOKEN_IO_DESKTOP_CODEX_PATH", DESKTOP_CODEX)
    assert executable and Path(executable).is_file(), f"required real client is missing: {client}"
    result = subprocess.run(
        [
            sys.executable,
            str(WORKSPACE / "tests/support/real_client_smoke.py"),
            "--client",
            client,
            "--executable",
            executable,
        ],
        capture_output=True,
        text=True,
        timeout=300,
    )
    # Never expose raw startup stderr or exception details from configured clients.
    assert result.returncode == 0, f"real client smoke failed: {client}"
    evidence = json.loads(result.stdout)
    assert evidence["status"] == "passed"
    assert evidence["client"] == client
    assert evidence["ephemeral_thread"] is True
    assert evidence["model_turns"] == 0
    assert len(evidence["source_sha256"]) == 5
    assert len(evidence["executable_sha256"]) == 64
    print(json.dumps(evidence, sort_keys=True))

"""验证独立 Hooks 安装入口、配置保护与重复注册。"""

import json
import stat
import subprocess
import sysconfig
from pathlib import Path

import pytest

from token_io_decoupling_hooks.registration import EVENTS, register_hooks


def test_registration_preserves_existing_hooks_and_keeps_exact_backup(tmp_path):
    path = tmp_path / "hooks.json"
    existing = {
        "custom": True,
        "hooks": {
            "Stop": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": "/other/hook",
                            "enabled": False,
                        }
                    ]
                }
            ]
        },
    }
    original = json.dumps(existing).encode()
    path.write_bytes(original)
    path.chmod(0o640)
    result = register_hooks(path, Path("/tools/token-io-decoupling-hooks"))
    config = json.loads(path.read_bytes())
    assert config["custom"] is True
    assert config["hooks"]["Stop"][0] == existing["hooks"]["Stop"][0]
    assert set(config["hooks"]) == set(EVENTS)
    assert Path(result["backup"]).read_bytes() == original
    assert stat.S_IMODE(path.stat().st_mode) == 0o640
    assert register_hooks(path, Path("/tools/token-io-decoupling-hooks"))["changed"] is False
    assert len(list(tmp_path.glob("*.bak"))) == 1


def test_dry_run_does_not_create_destination(tmp_path):
    path = tmp_path / "absent" / "hooks.json"
    result = register_hooks(path, Path("/tools/token-io-decoupling-hooks"), dry_run=True)
    assert result["changed"] is True
    assert not path.parent.exists()


@pytest.mark.parametrize("content", ["{", "[]", '{"hooks":[]}', '{"hooks":{"Stop":{}}}'])
def test_invalid_configuration_is_preserved(tmp_path, content):
    path = tmp_path / "hooks.json"
    path.write_text(content)
    with pytest.raises(ValueError):
        register_hooks(path, Path("/tools/token-io-decoupling-hooks"))
    assert path.read_text() == content
    assert not list(tmp_path.glob("*.bak"))


def test_symbolic_link_is_not_replaced(tmp_path):
    target = tmp_path / "original.json"
    target.write_text("{}")
    path = tmp_path / "hooks.json"
    path.symlink_to(target)
    with pytest.raises(ValueError, match="symbolic link"):
        register_hooks(path, Path("/tools/token-io-decoupling-hooks"))
    assert path.is_symlink()
    assert target.read_text() == "{}"


@pytest.mark.parametrize("event", EVENTS)
def test_registered_static_events_produce_native_responses(tmp_path, event):
    path = tmp_path / "hooks.json"
    register_hooks(path, Path("/tools with spaces/token-io-decoupling-hooks"))
    command = json.loads(path.read_text())["hooks"][event][0]["hooks"][0]["command"]
    assert command == "'/tools with spaces/token-io-decoupling-hooks'"
    executable = Path(sysconfig.get_path("scripts")) / "token-io-decoupling-hooks"
    result = subprocess.run(
        [str(executable)],
        input=json.dumps({"hook_event_name": event}),
        capture_output=True,
        text=True,
        timeout=10,
        cwd=tmp_path,
    )
    assert result.returncode == 0
    assert isinstance(json.loads(result.stdout), dict)
    assert result.stderr == ""


def test_setup_cli_is_idempotent_and_dry_run_preserves_file(tmp_path):
    executable = Path(sysconfig.get_path("scripts")) / "token-io-decoupling-hooks"
    path = tmp_path / "hooks.json"
    arguments = [str(executable), "setup", "codex", "--hooks-file", str(path)]
    preview = subprocess.run(arguments + ["--dry-run"], capture_output=True, text=True, timeout=10)
    assert preview.returncode == 0
    assert not path.exists()
    applied = subprocess.run(arguments, capture_output=True, text=True, timeout=10)
    assert applied.returncode == 0
    assert json.loads(applied.stdout)["changed"] is True
    repeated = subprocess.run(arguments, capture_output=True, text=True, timeout=10)
    assert repeated.returncode == 0
    assert json.loads(repeated.stdout)["changed"] is False

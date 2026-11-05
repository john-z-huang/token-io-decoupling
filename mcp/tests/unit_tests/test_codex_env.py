from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest
import tomlkit

from token_io_decoupling.codex_env import (
    DEFAULT_ENV_VARS,
    CodexEnvError,
    merge_env_vars,
)


def _config(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "config.toml"
    path.write_text(body, encoding="utf-8")
    return path


def test_merge_preserves_comments_unrelated_data_and_mode(tmp_path: Path) -> None:
    path = _config(
        tmp_path,
        '# keep me\n[unrelated]\nvalue = "untouched"\n\n'
        '[mcp_servers."quoted-name"]\ncommand = "/installed/server"\n'
        'args = ["start-mcp-server", "--profile", "workflow"]\n'
        'approval_mode = "approve"\nenv = { EXISTING = "kept" }\n',
    )
    path.chmod(0o640)
    original = path.read_text(encoding="utf-8")
    assert merge_env_vars(path, ("quoted-name",)) == ("quoted-name",)
    updated = path.read_text(encoding="utf-8")
    assert "# keep me" in updated
    assert 'command = "/installed/server"' in updated
    assert 'approval_mode = "approve"' in updated
    assert 'env = { EXISTING = "kept" }' in updated
    assert 'EXISTING = "kept"' in updated
    assert tomlkit.parse(updated)["mcp_servers"]["quoted-name"]["env_vars"] == list(
        DEFAULT_ENV_VARS
    )
    assert path.stat().st_mode & 0o777 == 0o640
    assert original != updated


def test_existing_names_and_local_objects_are_idempotent(tmp_path: Path) -> None:
    names = ", ".join(f'"{name}"' for name in DEFAULT_ENV_VARS if name != "OPENAI_BASE_URL")
    path = _config(
        tmp_path,
        '[mcp_servers.server]\ncommand = "runner"\n'
        f'env_vars = [{names}, {{ name = "OPENAI_BASE_URL", source = "local" }}]\n',
    )
    before = path.read_bytes()
    mtime = path.stat().st_mtime_ns
    assert merge_env_vars(path, ("server",)) == ()
    assert path.read_bytes() == before
    assert path.stat().st_mtime_ns == mtime


def test_default_proxy_names_are_added_and_idempotent(tmp_path: Path) -> None:
    path = _config(
        tmp_path,
        '[mcp_servers.server]\ncommand = "runner"\nenv_vars = ["KEEP", "OPENAI_API_KEY"]\n',
    )
    expected = [
        "KEEP",
        "OPENAI_API_KEY",
        "OPENAI_BASE_URL",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "NO_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
        "no_proxy",
    ]
    assert merge_env_vars(path, ("server",)) == ("server",)
    config = tomlkit.parse(path.read_text(encoding="utf-8"))
    assert config["mcp_servers"]["server"]["env_vars"] == expected
    before = path.read_bytes()
    assert merge_env_vars(path, ("server",)) == ()
    assert path.read_bytes() == before


def test_non_roundtripping_layout_blocks_repair_but_allows_complete_noop(
    tmp_path: Path,
) -> None:
    prefix = (
        '[[fruit]]\nname = "apple"\n\n[unrelated]\nflag = true\n\n'
        '[fruit.texture]\nsmooth = true\n\n[mcp_servers.demo]\ncommand = "echo"\n'
    )
    path = _config(tmp_path, prefix)
    before = path.read_bytes()
    assert tomlkit.dumps(tomlkit.parse(prefix)) != prefix
    with pytest.raises(CodexEnvError, match="cannot be safely rewritten"):
        merge_env_vars(path, ("demo",))
    assert path.read_bytes() == before

    encoded_names = ", ".join(f'"{name}"' for name in DEFAULT_ENV_VARS)
    complete = prefix + f"env_vars = [{encoded_names}]\n"
    path.write_text(complete, encoding="utf-8")
    before = path.read_bytes()
    mtime = path.stat().st_mtime_ns
    assert merge_env_vars(path, ("demo",)) == ()
    assert path.read_bytes() == before
    assert path.stat().st_mtime_ns == mtime


def test_remote_conflict_rejected_without_write(tmp_path: Path) -> None:
    path = _config(
        tmp_path,
        '[mcp_servers.server]\ncommand = "runner"\n'
        'env_vars = [{ name = "OPENAI_API_KEY", source = "remote" }]\n',
    )
    before = path.read_bytes()
    with pytest.raises(CodexEnvError, match="remote"):
        merge_env_vars(path, ("server",))
    assert path.read_bytes() == before


def test_remote_duplicate_conflict_is_not_hidden_by_local_entry(tmp_path: Path) -> None:
    path = _config(
        tmp_path,
        '[mcp_servers.server]\ncommand = "runner"\n'
        'env_vars = ["OPENAI_API_KEY", { name = "OPENAI_API_KEY", source = "remote" }]\n',
    )
    before = path.read_bytes()
    with pytest.raises(CodexEnvError, match="remote"):
        merge_env_vars(path, ("server",))
    assert path.read_bytes() == before


def test_http_only_environment_headers_rejected_before_write(tmp_path: Path) -> None:
    path = _config(
        tmp_path,
        '[mcp_servers.server]\ncommand = "runner"\nenv_http_headers = { "X-Test" = "test" }\n',
    )
    before = path.read_bytes()
    with pytest.raises(CodexEnvError, match="not stdio"):
        merge_env_vars(path, ("server",))
    assert path.read_bytes() == before


@pytest.mark.parametrize("name", ["HAS=EQUALS", "BAD\nNAME", "HAS SPACE"])
def test_invalid_environment_names_rejected(tmp_path: Path, name: str) -> None:
    path = _config(tmp_path, '[mcp_servers.server]\ncommand = "runner"\n')
    before = path.read_bytes()
    with pytest.raises(CodexEnvError, match="variable names"):
        merge_env_vars(path, ("server",), (name,))
    assert path.read_bytes() == before


@pytest.mark.parametrize(
    "body",
    [
        "not = [valid\n",
        '[mcp_servers.server]\nurl = "https://example.invalid"\n',
        "[mcp_servers.server]\ncommand = 3\n",
        '[mcp_servers.server]\ncommand = "runner"\nenv_vars = "bad"\n',
    ],
)
def test_invalid_config_rejected_without_write(tmp_path: Path, body: str) -> None:
    path = _config(tmp_path, body)
    before = path.read_bytes()
    with pytest.raises(CodexEnvError):
        merge_env_vars(path, ("server",))
    assert path.read_bytes() == before


def test_missing_server_rejected(tmp_path: Path) -> None:
    path = _config(tmp_path, '[mcp_servers.other]\ncommand = "runner"\n')
    before = path.read_bytes()
    with pytest.raises(CodexEnvError, match="missing"):
        merge_env_vars(path, ("new-server",))
    assert path.read_bytes() == before


def test_symlink_is_rejected_without_mutating_target(tmp_path: Path) -> None:
    target = _config(tmp_path, '[mcp_servers.server]\ncommand = "runner"\n')
    link = tmp_path / "linked.toml"
    link.symlink_to(target)
    before = target.read_bytes()
    with pytest.raises(CodexEnvError, match="symlink"):
        merge_env_vars(link, ("server",))
    assert target.read_bytes() == before


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="FIFO creation is unavailable")
def test_fifo_target_is_rejected_without_blocking(tmp_path: Path) -> None:
    fifo = tmp_path / "config.toml"
    os.mkfifo(fifo)
    with pytest.raises(CodexEnvError, match="regular, non-symlink"):
        merge_env_vars(fifo, ("server",))


def test_dry_run_is_read_only_and_lists_only_names(tmp_path: Path) -> None:
    path = _config(tmp_path, '[mcp_servers.server]\ncommand = "runner"\n')
    before = path.read_bytes()
    mtime = path.stat().st_mtime_ns
    assert merge_env_vars(path, ("server",), dry_run=True) == ("server",)
    assert path.read_bytes() == before
    assert path.stat().st_mtime_ns == mtime


def test_no_credentials_or_config_values_are_printed_by_wrapper(tmp_path: Path) -> None:
    marker = "SYNTHETIC_SECRET_SENTINEL"
    path = _config(
        tmp_path,
        f'[mcp_servers.server]\ncommand = "runner"\nenv = {{ OPENAI_API_KEY = "{marker}" }}\n',
    )
    script = Path(__file__).parents[3] / "scripts" / "configure-codex-mcp-env.py"
    result = subprocess.run(
        [
            "uv",
            "--offline",
            "run",
            "--script",
            str(script),
            "--config",
            str(path),
            "--server",
            "server",
            "--dry-run",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert marker not in result.stdout + result.stderr

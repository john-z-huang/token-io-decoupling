from __future__ import annotations

from pathlib import Path

import pytest

import token_io_decoupling.codex_env as codex_env
from token_io_decoupling.codex_env import (
    CodexEnvError,
    config_path,
    merge_env_vars,
)


def _config(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "config.toml"
    path.write_text(body, encoding="utf-8")
    return path


def test_environment_path_resolution(monkeypatch, tmp_path: Path) -> None:
    home = tmp_path / "custom"
    monkeypatch.setenv("CODEX_HOME", str(home))
    assert config_path() == home / "config.toml"
    assert config_path(Path("~/explicit.toml")) == Path.home() / "explicit.toml"


def test_detected_concurrent_change_aborts_and_cleans_temp(tmp_path: Path, monkeypatch) -> None:
    path = _config(tmp_path, '[mcp_servers.server]\ncommand = "runner"\n')
    original_read_target = codex_env._read_target
    reads = 0

    def read_target(candidate: Path, *, allow_missing: bool):
        nonlocal reads
        if candidate == path:
            reads += 1
            if reads == 3:
                path.write_text('[mcp_servers.server]\ncommand = "changed"\n')
        return original_read_target(candidate, allow_missing=allow_missing)

    monkeypatch.setattr(codex_env, "_read_target", read_target)
    with pytest.raises(CodexEnvError, match="changed during update"):
        merge_env_vars(path, ("server",))
    assert path.read_text(encoding="utf-8").endswith('command = "changed"\n')
    assert not list(tmp_path.glob(".config.toml.*"))


def test_replace_failure_preserves_config_and_cleans_temp(tmp_path: Path, monkeypatch) -> None:
    path = _config(tmp_path, '[mcp_servers.server]\ncommand = "runner"\n')
    before = path.read_bytes()

    def fail_replace(_source, _destination):
        raise OSError("synthetic replace failure")

    monkeypatch.setattr(codex_env.os, "replace", fail_replace)
    with pytest.raises(CodexEnvError, match="could not be updated"):
        merge_env_vars(path, ("server",))
    assert path.read_bytes() == before
    assert not list(tmp_path.glob(".config.toml.*"))

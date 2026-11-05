from __future__ import annotations

import io
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

from token_io_decoupling import serena_memory_helper as helper


def _fake_safe_yaml(monkeypatch: pytest.MonkeyPatch) -> None:
    ruamel = ModuleType("ruamel")
    yaml_module = ModuleType("ruamel.yaml")

    class YAML:
        def __init__(self, *, typ: str) -> None:
            assert typ == "safe"
            self.allow_duplicate_keys = True

        def load(self, text: str) -> object:
            if not text.strip():
                return None

            def mapping(pairs: list[tuple[str, object]]) -> dict[str, object]:
                result: dict[str, object] = {}
                for key, value in pairs:
                    if key in result and not self.allow_duplicate_keys:
                        raise ValueError("duplicate key")
                    result[key] = value
                return result

            return json.loads(text, object_pairs_hook=mapping)

    monkeypatch.setattr(yaml_module, "YAML", YAML, raising=False)
    monkeypatch.setitem(sys.modules, "ruamel", ruamel)
    monkeypatch.setitem(sys.modules, "ruamel.yaml", yaml_module)


def _write(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def _configuration_tree(tmp_path: Path, global_config: dict[str, object]) -> tuple[Path, Path]:
    project = tmp_path / "project"
    project.mkdir()
    home = tmp_path / "serena-home"
    (home / "memories" / "global").mkdir(parents=True)
    _write(home / "serena_config.yml", json.dumps(global_config))
    return project, home


def test_helper_configuration_merges_patterns_and_prefers_custom_placeholder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fake_safe_yaml(monkeypatch)
    project, home = _configuration_tree(
        tmp_path,
        {
            "project_serena_folder_location": "$projectDir/custom-$projectFolderName",
            "ignored_memory_patterns": ["global-ignore"],
            "read_only_memory_patterns": ["global-readonly"],
            "edit_global_memories": False,
        },
    )
    data = project / f"custom-{project.name}"
    (data / "memories").mkdir(parents=True)
    _write(data / "project.yml", json.dumps({"ignored_memory_patterns": ["project-old"]}))
    _write(
        data / "project.local.yml",
        json.dumps(
            {
                "ignored_memory_patterns": ["local-ignore"],
                "read_only_memory_patterns": ["local-readonly"],
            }
        ),
    )

    resolved, global_root, read_only, ignored = helper._load_configuration(
        project, {"SERENA_HOME": str(home)}
    )
    assert resolved == data
    assert global_root == home / "memories" / "global"
    assert ignored == ["global-ignore", "local-ignore"]
    assert read_only == ["global-readonly", "local-readonly", "global/.*"]


def test_helper_falls_back_to_default_project_directory_and_rejects_unknown_placeholder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fake_safe_yaml(monkeypatch)
    project, _ = _configuration_tree(
        tmp_path, {"project_serena_folder_location": "$projectDir/custom"}
    )
    default = project / ".serena"
    default.mkdir()
    assert (
        helper._project_data_directory(
            project, {"project_serena_folder_location": "$projectDir/custom"}
        )
        == default
    )
    with pytest.raises(helper._HelperUnavailable, match="placeholder_invalid"):
        helper._project_data_directory(project, {"project_serena_folder_location": "$unknown/x"})


@pytest.mark.parametrize(
    ("contents", "reason"),
    [
        ("", "serena_config_shape_invalid"),
        ('{"x":1,"x":2}', "serena_config_read_failed"),
        ('{"x":"not-json-yaml-tag"}', None),
        ("!!python/object/apply:os.system ['false']", "serena_config_read_failed"),
    ],
)
def test_helper_config_parser_is_safe_and_rejects_duplicate_or_invalid_yaml(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, contents: str, reason: str | None
) -> None:
    _fake_safe_yaml(monkeypatch)
    config = tmp_path / "config.yml"
    _write(config, contents)
    if reason is None:
        assert helper._read_yaml_mapping(config) == {"x": "not-json-yaml-tag"}
    else:
        with pytest.raises(helper._HelperUnavailable, match=reason):
            helper._read_yaml_mapping(config)


def test_helper_missing_roots_and_yaml_do_not_create_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fake_safe_yaml(monkeypatch)
    project = tmp_path / "project"
    project.mkdir()
    home = tmp_path / "serena-home"
    home.mkdir()
    _write(home / "serena_config.yml", "{}")
    with pytest.raises(
        helper._HelperUnavailable, match="project_serena_data_directory_unavailable"
    ):
        helper._load_configuration(project, {"SERENA_HOME": str(home)})
    assert not (home / "memories").exists()
    assert not (project / ".serena").exists()

    data = project / ".serena"
    data.mkdir()
    _write(data / "project.yml", "{}")
    (data / "memories").mkdir()
    with pytest.raises(
        helper._HelperUnavailable, match="serena_global_memory_directory_unavailable"
    ):
        helper._load_configuration(project, {"SERENA_HOME": str(home)})
    assert not (home / "memories").exists()


def test_python_audit_hook_blocks_writes_execution_and_network_but_allows_noop_mkdir(
    tmp_path: Path,
) -> None:
    existing = tmp_path / "existing"
    existing.mkdir()
    missing = tmp_path / "missing"
    code = """
import os, socket, subprocess, sys
from pathlib import Path
from token_io_decoupling.serena_memory_helper import _install_read_only_audit_hook
existing, missing = Path(sys.argv[1]), Path(sys.argv[2])
_install_read_only_audit_hook()
existing.mkdir(exist_ok=True)
assert existing.is_dir()
try:
    missing.mkdir(exist_ok=True)
except OSError:
    pass
else:
    raise AssertionError('missing directory was created')
assert not missing.exists()
for operation in (
    lambda: open(existing / 'new', 'w'),
    lambda: open(existing / 'new', 'a'),
    lambda: open(existing / 'new', 'x'),
    lambda: open(existing / 'new', 'r+'),
    lambda: os.open(existing / 'new', os.O_WRONLY | os.O_CREAT, 0o600),
    lambda: os.chmod(existing, 0o700),
    lambda: os.rename(existing, existing.with_name('renamed')),
    lambda: subprocess.Popen([sys.executable, '-V']),
    lambda: socket.socket().connect(('127.0.0.1', 9)),
):
    try:
        operation()
    except PermissionError:
        pass
    else:
        raise AssertionError('blocked operation succeeded')
"""
    result = subprocess.run(
        [sys.executable, "-c", code, str(existing), str(missing)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert not missing.exists()


def test_helper_stdin_limit_returns_bounded_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stdout = io.BytesIO()
    monkeypatch.setattr(
        helper.sys,
        "stdin",
        SimpleNamespace(buffer=io.BytesIO(b"x" * (helper._MAX_INPUT_BYTES + 1))),
    )
    monkeypatch.setattr(helper.sys, "stdout", SimpleNamespace(buffer=stdout))
    assert helper._run(Path("/fixed/serena_memory.py"), Path("/project")) == 0
    result = json.loads(stdout.getvalue())
    assert result["status"] == "unavailable"
    assert result["reason_code"] == "serena_request_too_large"
    assert len(stdout.getvalue()) < 256

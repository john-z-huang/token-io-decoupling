from __future__ import annotations

import hashlib
import io
import json
import runpy
import shutil
import stat
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest

from token_io_decoupling.skills import DEFAULT_NAME, LEGACY_NAME, install_skill

BUILD_ID = "a" * 64


def _archive(entries):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        for name, data in entries:
            archive.writestr(name, data)
    return stream.getvalue()


def _entries():
    contents = {
        "SKILL.md": b"---\nname: token-io-decoupling\n---\nInstructions.\n",
        "SKILL_zh_cn.md": b"---\nname: token-io-decoupling\n---\nInstructions.\n",
        "agents/openai.yaml": b"interface:\n  short_description: Test instructions\n",
        "references/example.md": b"version one",
    }
    manifest = {
        "schema_version": 2,
        "build_id": BUILD_ID,
        "files": {name: hashlib.sha256(data).hexdigest() for name, data in contents.items()},
    }
    return [*contents.items(), ("manifest.json", json.dumps(manifest).encode())]


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    root = tmp_path / "packages/token_io_decoupling/_resources"
    core = tmp_path / "packages/token_io_decoupling_core/_resources"
    root.mkdir(parents=True)
    core.mkdir(parents=True)
    (root / "skill_bundle.zip").write_bytes(_archive(_entries()))
    instructions = json.dumps(
        {
            "schema_version": 2,
            "build_id": BUILD_ID,
            "skill_files": json.loads(_entries()[-1][1])["files"],
        }
    ).encode()
    (core / "instructions.json").write_bytes(instructions)
    (core / "manifest.json").write_text(
        json.dumps(
            {
                "schema_version": 2,
                "build_id": BUILD_ID,
                "files": {"instructions.json": hashlib.sha256(instructions).hexdigest()},
            }
        )
    )
    packages = {
        "token_io_decoupling": root.parent,
        "token_io_decoupling_core": core.parent,
    }
    with patch("token_io_decoupling.skills.files", side_effect=packages.__getitem__):
        yield tmp_path


def test_snapshot_name_update_and_local_edits(home):
    installed = install_skill()
    assert installed == home / ".agents/skills" / DEFAULT_NAME
    assert f"name: {DEFAULT_NAME}" in (installed / "SKILL.md").read_text()
    manifest = json.loads((installed / "manifest.json").read_text())
    assert manifest["build_id"] == BUILD_ID
    for name, digest in manifest["files"].items():
        assert hashlib.sha256((installed / name).read_bytes()).hexdigest() == digest
    install_skill(update=True)
    (installed / "SKILL.md").write_text("user edits")
    with pytest.raises(ValueError, match="local changes"):
        install_skill(update=True)
    assert (installed / "SKILL.md").read_text() == "user edits"


@pytest.mark.parametrize("name", [LEGACY_NAME, "../escape", "/tmp/escape", "a/b", ""])
def test_invalid_or_legacy_name_never_writes(home, name):
    with pytest.raises(ValueError):
        install_skill(name=name)
    assert not (home / ".agents").exists()


@pytest.mark.parametrize(
    "damage",
    [
        "corrupt",
        "missing-manifest",
        "schema",
        "mismatch",
        "undeclared",
        "unsafe",
        "private",
        "symlink",
        "duplicate",
        "empty",
    ],
)
def test_invalid_compiled_bundle_is_rejected_before_any_write(home, damage):
    entries = _entries()
    if damage in {"schema", "mismatch"}:
        manifest = json.loads(entries[-1][1])
        manifest["schema_version" if damage == "schema" else "build_id"] = (
            1 if damage == "schema" else "another-batch"
        )
        entries[-1] = ("manifest.json", json.dumps(manifest).encode())
    elif damage == "missing-manifest":
        entries.pop()
    elif damage == "corrupt":
        entries[0] = ("SKILL.md", b"changed without recompilation")
    elif damage in {"undeclared", "unsafe", "private"}:
        name = {
            "undeclared": "extra.md",
            "unsafe": "../escape.md",
            "private": "_project/DEVELOPMENT.md",
        }[damage]
        entries.append((name, b"unapproved"))
    elif damage == "symlink":
        link = zipfile.ZipInfo("link.md")
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        entries.append((link, b"SKILL.md"))
    elif damage == "duplicate":
        entries.append(entries[0])
    elif damage == "empty":
        entries[0] = ("SKILL.md", b" \n")
        manifest = json.loads(entries[-1][1])
        manifest["files"]["SKILL.md"] = hashlib.sha256(b" \n").hexdigest()
        entries[-1] = ("manifest.json", json.dumps(manifest).encode())
    bundle = home / "packages/token_io_decoupling/_resources/skill_bundle.zip"
    if damage == "duplicate":
        with pytest.warns(UserWarning, match="Duplicate"):
            bundle.write_bytes(_archive(entries))
    else:
        bundle.write_bytes(_archive(entries))
    with pytest.raises(ValueError):
        install_skill()
    assert not (home / ".agents").exists()


def _same_id_document_profile_drift():
    entries = _entries()
    contents = dict(entries)
    contents["references/example.md"] = b"another document-only instruction profile"
    manifest = json.loads(contents["manifest.json"])
    manifest["files"]["references/example.md"] = hashlib.sha256(
        contents["references/example.md"]
    ).hexdigest()
    contents["manifest.json"] = json.dumps(manifest).encode()
    payload = _archive(contents.items())
    from token_io_decoupling.skills import validate_skill_bundle

    # This is an internally valid generated profile with the same pre-Skill build ID.
    validated, _ = validate_skill_bundle(payload, expected_build_id=BUILD_ID)
    assert validated["build_id"] == BUILD_ID
    return payload


def test_same_id_document_profile_drift_is_rejected_before_any_write(home):
    bundle = home / "packages/token_io_decoupling/_resources/skill_bundle.zip"
    bundle.write_bytes(_same_id_document_profile_drift())
    with pytest.raises(ValueError, match="core instruction map"):
        install_skill()
    assert not (home / ".agents").exists()


def test_root_build_hook_rejects_same_id_document_profile_drift(home):
    repository = next(
        parent
        for parent in Path(__file__).resolve().parents
        if (parent / "mcp/pyproject.toml").is_file()
    )
    project = home / "source-project"
    resources = project / "src/token_io_decoupling/_resources"
    resources.mkdir(parents=True)
    (resources / "skill_bundle.zip").write_bytes(_same_id_document_profile_drift())
    shutil.copy2(repository / "mcp/src/token_io_decoupling/skills.py", resources.parent)
    shutil.copytree(
        home / "packages/token_io_decoupling_core",
        project / "packages/token_io_decoupling_core/src/token_io_decoupling_core",
    )
    validate = runpy.run_path(str(repository / "mcp/hatch_build.py"))["validate_compiled_skill"]
    with pytest.raises(RuntimeError, match="core instruction map"):
        validate(project)


def test_corrupt_core_resource_is_rejected_before_any_write(home):
    core = home / "packages/token_io_decoupling_core/_resources/instructions.json"
    core.write_text('{"schema_version": 2, "build_id": "wrong"}')
    with pytest.raises(ValueError, match="core resources"):
        install_skill()
    assert not (home / ".agents").exists()


def test_legacy_checkout_unchanged_and_unknown_destination_refused(home):
    root = home / ".agents/skills"
    legacy = root / LEGACY_NAME
    (legacy / ".git").mkdir(parents=True)
    (legacy / "uncommitted").write_text("keep")
    install_skill()
    assert (legacy / "uncommitted").read_text() == "keep"
    assert (legacy / ".git").is_dir()
    for update in (False, True):
        unknown = root / "unknown"
        unknown.mkdir(exist_ok=True)
        (unknown / "keep.txt").write_text("unknown contents")
        with pytest.raises(ValueError):
            install_skill(name="unknown", update=update)
        assert (unknown / "keep.txt").read_text() == "unknown contents"


def test_symlink_target_and_root_refused(home):
    root = home / ".agents/skills"
    root.mkdir(parents=True)
    legacy = root / LEGACY_NAME
    legacy.mkdir()
    (root / DEFAULT_NAME).symlink_to(legacy)
    for update in (False, True):
        with pytest.raises(ValueError, match="symbolic"):
            install_skill(update=update)
    (root / DEFAULT_NAME).unlink()


def test_redirected_skills_root_refused(home):
    old_project = home / "old-project"
    old_project.mkdir()
    (home / ".agents").mkdir()
    (home / ".agents/skills").symlink_to(old_project)
    with pytest.raises(ValueError, match="symbolic"):
        install_skill()
    assert list(old_project.iterdir()) == []


def test_custom_name_and_unknown_git_checkout(home):
    target = install_skill(name="custom-coding")
    assert "name: custom-coding" in (target / "SKILL.md").read_text()
    (target / ".git").write_text("gitdir: elsewhere")
    with pytest.raises(ValueError, match="repository"):
        install_skill(name="custom-coding", update=True)


def test_publish_failure_rolls_back(home):
    installed = install_skill()
    before = (installed / "SKILL.md").read_bytes()
    original = Path.rename

    def fail_new(self, target):
        if self.name == "new":
            raise OSError("injected publish failure")
        return original(self, target)

    with patch.object(Path, "rename", fail_new), pytest.raises(OSError):
        install_skill(update=True)
    assert (installed / "SKILL.md").read_bytes() == before

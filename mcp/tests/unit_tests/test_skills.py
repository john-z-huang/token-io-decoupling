from __future__ import annotations

import io
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest

from token_io_decoupling.skills import DEFAULT_NAME, LEGACY_NAME, install_skill


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    data = io.BytesIO()
    with zipfile.ZipFile(data, "w") as archive:
        archive.writestr("SKILL.md", "---\nname: token-io-decoupling\n---\n")
        archive.writestr("references/example.md", "version one")
    bundle = tmp_path / "bundle.zip"
    bundle.write_bytes(data.getvalue())
    with patch("token_io_decoupling.skills.files") as files:
        files.return_value.joinpath.return_value = bundle
        yield tmp_path


def test_snapshot_name_update_and_local_edits(home):
    installed = install_skill()
    assert installed == home / ".agents/skills" / DEFAULT_NAME
    assert f"name: {DEFAULT_NAME}" in (installed / "SKILL.md").read_text()
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

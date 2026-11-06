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
    """生成内部一致的最小schema3中文Skill归档，负例只破坏目标契约。"""
    contents = {
        "SKILL.md": "---\nname: token-io-decoupling\n---\n中文指令。\n".encode(),
        "agents/openai.yaml": "interface:\n  short_description: 中文测试指令\n".encode(),
        "references/example.md": "首版指令".encode(),
        "instruction-index.json": json.dumps(
            {
                "schema_version": 3,
                "language": "zh_cn",
                "events": {"task_received": "references/example.md"},
                "workflows": {"single-agent": "references/example.md"},
                "checkpoints": {"contract": {"document": "references/example.md"}},
                "fragments": {"shared": ["references/example.md"]},
            }
        ).encode(),
    }
    manifest = {
        "schema_version": 3,
        "language": "zh_cn",
        "build_id": BUILD_ID,
        "files": {name: hashlib.sha256(data).hexdigest() for name, data in contents.items()},
    }
    return [*contents.items(), ("manifest.json", json.dumps(manifest).encode())]


@pytest.fixture
def home(tmp_path, monkeypatch):
    """隔离用户目录与包资源，禁止安装测试触及真实Skill或配置。"""
    monkeypatch.setenv("HOME", str(tmp_path))
    root = tmp_path / "packages/token_io_decoupling/_resources"
    core = tmp_path / "packages/token_io_decoupling_workflow/_resources"
    root.mkdir(parents=True)
    core.mkdir(parents=True)
    (root / "skill_bundle.zip").write_bytes(_archive(_entries()))
    instructions = json.dumps(
        {
            "schema_version": 3,
            "language": "zh_cn",
            "build_id": BUILD_ID,
            "skill_files": json.loads(_entries()[-1][1])["files"],
        }
    ).encode()
    (core / "instructions.json").write_bytes(instructions)
    (core / "manifest.json").write_text(
        json.dumps(
            {
                "schema_version": 3,
                "language": "zh_cn",
                "build_id": BUILD_ID,
                "files": {"instructions.json": hashlib.sha256(instructions).hexdigest()},
            }
        )
    )
    packages = {
        "token_io_decoupling": root.parent,
        "token_io_decoupling_workflow": core.parent,
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
    """无效名称和受保护旧名称在创建任何安装目录前就必须拒绝。"""
    with pytest.raises(ValueError, match="choose a new lower-case Skill name"):
        install_skill(name=name)
    assert not (home / ".agents").exists()


def _damage_manifest(entries, damage):
    """有意破坏清单版本、批次或正文完整性，保持其他归档内容固定。"""
    manifest = json.loads(entries[-1][1])
    if damage == "empty":
        entries[0] = ("SKILL.md", b" \n")
        manifest["files"]["SKILL.md"] = hashlib.sha256(b" \n").hexdigest()
    else:
        field = "build_id" if damage == "mismatch" else "schema_version"
        manifest[field] = {"schema": 1, "retired-schema": 2, "mismatch": "another-batch"}[damage]
    entries[-1] = ("manifest.json", json.dumps(manifest).encode())


def _damaged_entries(damage):
    """按安全场景构造一个损坏归档，分别覆盖路径、私有文件、镜像、链接和重复项。"""
    entries = _entries()
    if damage in {"schema", "retired-schema", "mismatch", "empty"}:
        _damage_manifest(entries, damage)
    elif damage == "missing-manifest":
        entries.pop()
    elif damage == "corrupt":
        entries[0] = ("SKILL.md", b"changed without recompilation")
    elif damage in {"undeclared", "unsafe", "private", "mirror"}:
        name = {
            "undeclared": "extra.md",
            "unsafe": "../escape.md",
            "private": "_project/DEVELOPMENT.md",
            "mirror": "SKILL_zh_cn.md",
        }[damage]
        entries.append((name, b"unapproved"))
    elif damage == "symlink":
        link = zipfile.ZipInfo("link.md")
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        entries.append((link, b"SKILL.md"))
    elif damage == "duplicate":
        entries.append(entries[0])
    return entries


@pytest.mark.parametrize(
    "damage",
    [
        "corrupt",
        "missing-manifest",
        "schema",
        "retired-schema",
        "mismatch",
        "undeclared",
        "unsafe",
        "private",
        "mirror",
        "symlink",
        "duplicate",
        "empty",
    ],
)
def test_invalid_compiled_bundle_is_rejected_before_any_write(home, damage):
    """每类损坏归档都须在安装写入前失败，拒绝不能以未处理异常代替。"""
    entries = _damaged_entries(damage)
    bundle = home / "packages/token_io_decoupling/_resources/skill_bundle.zip"
    if damage == "duplicate":
        with pytest.warns(UserWarning, match="Duplicate"):
            bundle.write_bytes(_archive(entries))
    else:
        bundle.write_bytes(_archive(entries))
    with pytest.raises(ValueError, match="compiled Skill|packaged Skill|Expecting value"):
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
    """即使build相同，文档档案与core清单不一致也必须在构建阶段拒绝。"""
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
    shutil.copy2(repository / "mcp/src/token_io_decoupling/skill_bundle.py", resources.parent)
    shutil.copytree(
        home / "packages/token_io_decoupling_workflow",
        project / "packages/token_io_decoupling_workflow/src/token_io_decoupling_workflow",
    )
    validate = runpy.run_path(str(repository / "mcp/hatch_build.py"))["validate_compiled_skill"]
    with pytest.raises(RuntimeError, match="core instruction map"):
        validate(project)


def test_corrupt_core_resource_is_rejected_before_any_write(home):
    core = home / "packages/token_io_decoupling_workflow/_resources/instructions.json"
    core.write_text('{"schema_version": 2, "build_id": "wrong"}')
    with pytest.raises(ValueError, match="core resources"):
        install_skill()
    assert not (home / ".agents").exists()


def test_legacy_checkout_unchanged_and_unknown_destination_refused(home):
    """旧Git检出保留原内容，未知安装目标在install或update下都不能被覆盖。"""
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
        with pytest.raises(
            ValueError, match="destination already exists|not a managed installation"
        ):
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
    """发布新目录失败时，旧受管安装须恢复到原字节。"""
    installed = install_skill()
    before = (installed / "SKILL.md").read_bytes()
    original = Path.rename

    def fail_new(self, target):
        if self.name == "new":
            raise OSError("injected publish failure")
        return original(self, target)

    with (
        patch.object(Path, "rename", fail_new),
        pytest.raises(OSError, match="injected publish failure"),
    ):
        install_skill(update=True)
    assert (installed / "SKILL.md").read_bytes() == before


def _previous_managed_installation(home):
    """保留 V2 双语安装的完整指纹，不把旧指令加载进当前运行时。"""
    installed = home / ".agents/skills" / DEFAULT_NAME
    installed.mkdir(parents=True)
    contents = {
        "SKILL.md": b"---\nname: token-io-decoupling-skill\n---\nOld English rules.\n",
        "SKILL_zh_cn.md": "# 旧中文指令\n".encode(),
        "instruction-index.json": json.dumps(
            {
                "schema_version": 2,
                "checkpoints": {
                    "contract": {"documents": {"en": "SKILL.md", "zh_cn": "SKILL_zh_cn.md"}}
                },
            }
        ).encode(),
    }
    previous_manifest = {
        "schema_version": 2,
        "build_id": "b" * 64,
        "files": {name: hashlib.sha256(data).hexdigest() for name, data in contents.items()},
    }
    contents["manifest.json"] = json.dumps(previous_manifest).encode()
    for name, data in contents.items():
        (installed / name).write_bytes(data)
    marker = {
        "format": 1,
        "name": DEFAULT_NAME,
        "version": "0.1.0",
        "build_id": "b" * 64,
        "files": {name: hashlib.sha256(data).hexdigest() for name, data in contents.items()},
    }
    (installed / ".token-io-skill.json").write_text(json.dumps(marker))
    return installed


def test_previous_managed_bilingual_snapshot_upgrades_to_one_chinese_entry(home):
    """完整受管V2快照可整树更新为中文V3，删除旧镜像且重复更新保持幂等。"""
    installed = _previous_managed_installation(home)
    updated = install_skill(update=True)
    assert updated == installed
    assert not (installed / "SKILL_zh_cn.md").exists()
    assert "中文指令" in (installed / "SKILL.md").read_text()
    index = json.loads((installed / "instruction-index.json").read_bytes())
    assert index["schema_version"] == 3
    assert index["language"] == "zh_cn"
    assert index["checkpoints"]["contract"]["document"] == "references/example.md"
    before = {path.name: path.read_bytes() for path in installed.iterdir() if path.is_file()}
    install_skill(update=True)
    assert {
        path.name: path.read_bytes() for path in installed.iterdir() if path.is_file()
    } == before


def test_previous_snapshot_with_local_edits_is_not_replaced(home):
    """旧快照已有用户修改时不得升级覆盖，拒绝后全部原字节保持。"""
    installed = _previous_managed_installation(home)
    (installed / "SKILL_zh_cn.md").write_text("用户保留的旧版修改")
    before = {path.name: path.read_bytes() for path in installed.iterdir()}
    with pytest.raises(ValueError, match="local changes"):
        install_skill(update=True)
    assert {path.name: path.read_bytes() for path in installed.iterdir()} == before

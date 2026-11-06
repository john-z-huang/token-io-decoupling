"""使用真实发行文件验证独立安装、单中文更新和原有目录保护。"""

from __future__ import annotations

import hashlib
import io
import json
import re
import subprocess
import sys
import tarfile
import unicodedata
import zipfile
from pathlib import Path
from urllib.parse import unquote

import pytest
from support.skill_installation import (
    IsolatedSkillCli,
    SkillArtifacts,
    build_skill_artifacts,
    file_snapshot,
    prepare_skill_cli,
    write_legacy_skill_snapshot,
)

from token_io_decoupling import skills
from token_io_decoupling.skills import validate_skill_bundle

REPOSITORY = next(
    parent
    for parent in Path(__file__).resolve().parents
    if (parent / "mcp/pyproject.toml").is_file()
)


def _markdown_prose(path: Path) -> str:
    """排除围栏代码示例，避免将示例链接误当成交付文档引用。"""
    return re.sub(r"\x60{3}.*?\x60{3}|~~~.*?~~~", "", path.read_text(), flags=re.S)


def _markdown_anchors(path: Path) -> set[str]:
    """按真实标题计算 Unicode 锚点及重复标题后缀，中文改名仍须正确定位。"""
    counts: dict[str, int] = {}
    result: set[str] = set()
    for line in _markdown_prose(path).splitlines():
        heading = re.match(r"^#{1,6}\s+(.+?)\s*#*$", line)
        if heading is None:
            continue
        text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", heading[1]).lower()
        slug = "".join(
            character
            for character in text
            if unicodedata.category(character)[0] in "LN" or character in "_- "
        ).replace(" ", "-")
        count = counts.get(slug, 0)
        counts[slug] = count + 1
        result.add(slug + (f"-{count}" if count else ""))
    return result


def _assert_local_links(documents: Path, boundary: Path) -> None:
    """核对安装快照内的链接、目录边界与实际章节，不能靠删检查掩盖迁移断链。"""
    for document in documents.rglob("*.md"):
        text = re.sub(r"(\x60+).*?\1", "", _markdown_prose(document))
        for raw in re.findall(r"\]\(([^)]+)\)", text):
            if "://" in raw or raw.startswith(("mailto:", "{{")):
                continue
            target, _, fragment = raw.partition("#")
            resolved = (
                (document.parent / unquote(target.split("?")[0])).resolve() if target else document
            )
            assert resolved.is_relative_to(boundary), (document, raw)
            assert resolved.exists(), (document, raw)
            if fragment and resolved.suffix == ".md":
                assert unquote(fragment) in _markdown_anchors(resolved), (document, raw)


def test_generated_skill_links_stay_inside_delivered_tree(tmp_path):
    """从真实批准 ZIP 展开后检查全部本地链接，保证脱离作者树仍可阅读。"""
    bundle = REPOSITORY / "mcp/src/token_io_decoupling/_resources/skill_bundle.zip"
    _, contents = validate_skill_bundle(bundle.read_bytes())
    skill = tmp_path / "skill"
    for relative, data in contents.items():
        destination = skill / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
    _assert_local_links(skill, skill)


@pytest.mark.parametrize("rewrite_manifest", [False, True])
def test_instruction_index_tampering_is_rejected_by_bundle_integrity(rewrite_manifest):
    """篡改索引后，即使重算其清单 Hash，也不能绕过同批 core 文件清单约束。"""
    bundle = REPOSITORY / "mcp/src/token_io_decoupling/_resources/skill_bundle.zip"
    manifest, contents = validate_skill_bundle(bundle.read_bytes())
    assert "instruction-index.json" in manifest["files"]
    contents["instruction-index.json"] = b"{}\n"
    if rewrite_manifest:
        changed = json.loads(contents["manifest.json"])
        changed["files"]["instruction-index.json"] = hashlib.sha256(
            contents["instruction-index.json"]
        ).hexdigest()
        contents["manifest.json"] = json.dumps(changed).encode()
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        for name, data in contents.items():
            archive.writestr(name, data)
    message = "core instruction map" if rewrite_manifest else "integrity check failed"
    with pytest.raises(ValueError, match=message):
        validate_skill_bundle(
            output.getvalue(),
            expected_build_id=manifest["build_id"],
            expected_files=manifest["files"],
        )


@pytest.fixture(scope="module")
def skill_artifacts(tmp_path_factory: pytest.TempPathFactory) -> SkillArtifacts:
    """整组只构建一次真实 wheel 与分离 sdist，不把源码 checkout 交给安装子进程。"""
    return build_skill_artifacts(REPOSITORY, tmp_path_factory.mktemp("skill-artifacts"))


@pytest.fixture
def isolated_cli(skill_artifacts: SkillArtifacts, tmp_path: Path) -> IsolatedSkillCli:
    """每个安装场景使用独立虚拟环境与 HOME，避免读写用户真实安装。"""
    return prepare_skill_cli(skill_artifacts, tmp_path)


def test_detached_sdist_builds_without_author_tree(skill_artifacts: SkillArtifacts) -> None:
    """分离 sdist 应只靠批准 ZIP 重建，且安装前删除临时作者 checkout。"""
    with tarfile.open(skill_artifacts.sdist) as archive:
        names = {"/".join(Path(name).parts[1:]) for name in archive.getnames()}
    assert "src/token_io_decoupling/_resources/skill_bundle.zip" in names
    assert not any(name.startswith(("rule_sources/", "instruction-compiler/")) for name in names)
    assert not skill_artifacts.detached_source.exists()
    assert len(list(skill_artifacts.wheels.glob("*.whl"))) == 5


def test_detached_cli_installs_single_chinese_skill(isolated_cli: IsolatedSkillCli) -> None:
    """真实独立 CLI 只安装中文单源与扁平索引，所有规范链接必须在交付树内成立。"""
    installed = isolated_cli.invoke("skills", "install")
    assert installed.returncode == 0, installed.stderr
    skill = isolated_cli.skill
    assert b"name: token-io-decoupling-skill" in (skill / "SKILL.md").read_bytes()
    assert not list(skill.rglob("*_zh_cn.md"))
    manifest = json.loads((skill / "manifest.json").read_bytes())
    index = json.loads((skill / "instruction-index.json").read_bytes())
    assert manifest["schema_version"] == index["schema_version"] == 3
    assert manifest["language"] == index["language"] == "zh_cn"
    contract = index["checkpoints"]["contract"]
    change = index["checkpoints"]["contract_change"]
    assert contract["document"].endswith("task-received.md#判断")
    assert change["document"].endswith("progress-reported.md#判断")
    assert contract["required_facts"] != change["required_facts"]
    assert "documents" not in contract
    for forbidden in ("_project", "instruction-compiler", ".agents", "tests", "benchmarks"):
        assert not (skill / forbidden).exists()
    _assert_local_links(skill, skill)


def test_schema2_update_retires_all_previous_language_files(isolated_cli: IsolatedSkillCli) -> None:
    """旧受管双语言快照整体换成当前中文批次；再次更新须保持字节幂等且无残留备份。"""
    assert isolated_cli.invoke("skills", "install").returncode == 0
    skill = isolated_cli.skill
    current = file_snapshot(skill)
    write_legacy_skill_snapshot(skill)
    assert json.loads((skill / "manifest.json").read_bytes())["schema_version"] == 2
    assert (skill / "SKILL_zh_cn.md").is_file()
    assert b"English entry" in (skill / "SKILL.md").read_bytes()
    updated = isolated_cli.invoke("skills", "update")
    assert updated.returncode == 0, updated.stderr
    assert not (skill / "instructions").exists()
    assert not list(skill.rglob("*_zh_cn.md"))
    assert file_snapshot(skill) == current
    assert isolated_cli.invoke("skills", "update").returncode == 0
    assert file_snapshot(skill) == current
    assert not list(skill.parent.glob(f".{skill.name}-backup-*"))
    _assert_local_links(skill, skill)


def test_update_preserves_locally_modified_instruction_index(
    isolated_cli: IsolatedSkillCli,
) -> None:
    """用户改过索引后更新必须拒绝，整棵受管树保持修改后的原样。"""
    assert isolated_cli.invoke("skills", "install").returncode == 0
    index = isolated_cli.skill / "instruction-index.json"
    index.write_text("{}\n")
    edited = file_snapshot(isolated_cli.skill)
    rejected = isolated_cli.invoke("skills", "update")
    assert rejected.returncode == 2
    assert file_snapshot(isolated_cli.skill) == edited


def test_local_skill_edits_do_not_change_program_or_rules(isolated_cli: IsolatedSkillCli) -> None:
    """修改已安装指令不能改变程序、配置或内置规则，也不能被更新静默覆盖。"""
    assert isolated_cli.invoke("skills", "install").returncode == 0
    rules_before = isolated_cli.rule_manifest()
    program_before = file_snapshot(isolated_cli.venv)
    config_before = isolated_cli.config.read_bytes()
    entry = isolated_cli.skill / "SKILL.md"
    entry.write_text("local Skill edits")
    assert isolated_cli.invoke("skills", "update").returncode == 2
    assert entry.read_text() == "local Skill edits"
    assert isolated_cli.invoke("--version").returncode == 0
    smoke = subprocess.run(
        (
            sys.executable,
            str(
                REPOSITORY
                / ".agents/skills/token-io-decoupling-dev/tests/mcp/support"
                / "installed_stdio_smoke.py"
            ),
            "--cli",
            str(isolated_cli.cli),
        ),
        cwd=isolated_cli.root,
        env=isolated_cli.environment(),
        text=True,
        capture_output=True,
    )
    assert smoke.returncode == 0, smoke.stderr
    assert isolated_cli.rule_manifest() == rules_before
    assert file_snapshot(isolated_cli.venv) == program_before
    assert isolated_cli.config.read_bytes() == config_before


def test_legacy_skill_checkout_is_preserved(isolated_cli: IsolatedSkillCli) -> None:
    """旧名称指向受保护 checkout，安装失败后未提交文件与 Git 目录都须保留。"""
    rejected = isolated_cli.invoke("skills", "install", "--name", "token-io-decoupling")
    assert rejected.returncode == 2
    assert (isolated_cli.legacy / "uncommitted.txt").read_text() == "preserve me"
    assert (isolated_cli.legacy / ".git").is_dir()


def test_failed_publication_restores_the_complete_old_snapshot(tmp_path, monkeypatch):
    """注入新目录发布失败后，真实回滚必须恢复全部旧字节并清理备份和锁。"""
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    target = skills.install_skill()
    before = file_snapshot(target)
    rename = Path.rename

    def fail_publication(source: Path, destination: Path) -> Path:
        if source.name == "new":
            raise OSError("staging publish failed")
        return rename(source, destination)

    monkeypatch.setattr(Path, "rename", fail_publication)
    with pytest.raises(OSError, match="staging publish failed"):
        skills.install_skill(update=True)
    assert file_snapshot(target) == before
    assert not list(target.parent.glob(f".{target.name}-backup-*"))
    assert not (target.parent / f".{target.name}.lock").exists()


def test_failed_publication_and_rollback_preserve_the_recovery_snapshot(tmp_path, monkeypatch):
    """连续破坏发布与恢复 rename，仍须保留自动清理之外的完整旧树及准确恢复路径。"""
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    target = skills.install_skill()
    before = file_snapshot(target)
    rename = Path.rename

    def fail_publication_and_rollback(source: Path, destination: Path) -> Path:
        if source.name in {"new", "previous"}:
            raise OSError("injected rename failure")
        return rename(source, destination)

    monkeypatch.setattr(Path, "rename", fail_publication_and_rollback)
    with pytest.raises(OSError, match="previous snapshot preserved at") as failed:
        skills.install_skill(update=True)
    backups = list(target.parent.glob(f".{target.name}-backup-*/previous"))
    assert len(backups) == 1
    assert file_snapshot(backups[0]) == before
    assert str(backups[0]) in str(failed.value)
    assert not target.exists()
    assert not (target.parent / f".{target.name}.lock").exists()

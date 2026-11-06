"""为安装测试准备真实发行文件与隔离 CLI，不代替测试判断安装结果。"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
from dataclasses import dataclass
from pathlib import Path

_RULE_PROBE = """
import hashlib
import json
from importlib.resources import files
resources = files('token_io_decoupling_workflow').joinpath('_resources')
payload = resources.joinpath('instructions.json').read_bytes()
manifest = json.loads(resources.joinpath('manifest.json').read_bytes())
assert manifest['files']['instructions.json'] == hashlib.sha256(payload).hexdigest()
assert manifest['build_id'] == json.loads(payload)['build_id']
print(json.dumps(manifest, sort_keys=True))
"""


def run_checked(*args: str, cwd: Path, env: dict[str, str] | None = None) -> str:
    """用于必须成功的环境准备；产品拒绝结果由测试自行断言，不隐藏业务验收。"""
    result = subprocess.run(args, cwd=cwd, env=env, text=True, capture_output=True)
    if result.returncode != 0:
        raise AssertionError(
            f"command failed with exit code {result.returncode}: {args[0]}\n{result.stderr}"
        )
    return result.stdout


@dataclass(frozen=True)
class SkillArtifacts:
    """同一次真实构建的 wheel、sdist 与已清理的分离源码位置。"""

    wheels: Path
    sdist: Path
    detached_source: Path


def build_skill_artifacts(repository: Path, root: Path) -> SkillArtifacts:
    """构建当前 wheel，再从分离 sdist 重建根包，最后删除临时源码。"""
    workspace = repository / "mcp"
    wheels = root / "wheels"
    sdists = root / "sdists"
    build_options = ("--no-build-isolation", "--python", sys.executable)
    run_checked(
        "uv",
        "build",
        "--all-packages",
        "--wheel",
        *build_options,
        "--out-dir",
        str(wheels),
        cwd=workspace,
    )
    run_checked(
        "uv",
        "build",
        "--package",
        "token-io-decoupling",
        "--sdist",
        *build_options,
        "--out-dir",
        str(sdists),
        cwd=workspace,
    )
    sdist = next(sdists.glob("*.tar.gz"))
    detached = root / "detached"
    detached.mkdir()
    try:
        with tarfile.open(sdist) as archive:
            archive.extractall(detached, filter="data")
        project = next(detached.iterdir())
        run_checked(
            "uv",
            "build",
            "--wheel",
            *build_options,
            "--out-dir",
            str(wheels),
            cwd=project,
        )
    finally:
        shutil.rmtree(detached)
    return SkillArtifacts(wheels, sdist, detached)


@dataclass(frozen=True)
class IsolatedSkillCli:
    """一个场景独占的真实 CLI、虚拟环境与临时 HOME。"""

    root: Path
    venv: Path
    home: Path

    @property
    def cli(self) -> Path:
        """使用隔离环境中的入口，避免调用用户已安装的管理程序。"""
        return self.venv / "bin/token-io-decoupling"

    @property
    def skill(self) -> Path:
        """当前场景默认受管目录，不接触真实 Skill 根目录。"""
        return self.home / ".agents/skills/token-io-decoupling-skill"

    @property
    def legacy(self) -> Path:
        """当前场景模拟的受保护旧 checkout。"""
        return self.home / ".agents/skills/token-io-decoupling"

    @property
    def config(self) -> Path:
        """当前场景用于核对配置未变化的临时 Codex 文件。"""
        return self.home / ".codex/config.toml"

    def environment(self) -> dict[str, str]:
        """为 CLI 子进程构造隔离 HOME，移除可能把导入引回源码的 PYTHONPATH。"""
        env = {**os.environ, "HOME": str(self.home)}
        env.pop("PYTHONPATH", None)
        return env

    def invoke(self, *args: str) -> subprocess.CompletedProcess[str]:
        """返回真实退出码与输出，允许测试明确区分成功和预期拒绝。"""
        return subprocess.run(
            (str(self.cli), *args),
            cwd=self.root,
            env=self.environment(),
            text=True,
            capture_output=True,
        )

    def rule_manifest(self) -> str:
        """从隔离解释器读取已安装规则身份，不能误用 checkout 中的模块。"""
        return run_checked(
            str(self.venv / "bin/python"),
            "-I",
            "-c",
            _RULE_PROBE,
            cwd=self.root,
            env=self.environment(),
        )


def prepare_skill_cli(artifacts: SkillArtifacts, root: Path) -> IsolatedSkillCli:
    """离线安装当前 wheel 集合，并准备受保护旧目录和原有配置；不预装 Skill。"""
    venv = root / "standalone"
    run_checked("uv", "venv", "--python", sys.executable, str(venv), cwd=root)
    run_checked(
        "uv",
        "pip",
        "install",
        "--offline",
        "--python",
        str(venv / "bin/python"),
        "--find-links",
        str(artifacts.wheels),
        *map(str, sorted(artifacts.wheels.glob("*.whl"))),
        cwd=root,
    )
    installation = IsolatedSkillCli(root, venv, root / "home")
    (installation.legacy / ".git").mkdir(parents=True)
    (installation.legacy / "uncommitted.txt").write_text("preserve me")
    installation.config.parent.mkdir()
    installation.config.write_text('[mcp_servers.preserved]\ncommand = "existing-mcp"\n')
    return installation


def file_snapshot(root: Path) -> dict[str, bytes]:
    """记录完整文件字节，排除解释器缓存，便于逐字验证保全与幂等。"""
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
    }


def write_legacy_skill_snapshot(skill: Path) -> None:
    """准备旧格式的受管目录；marker 只证明这些旧字节的归属。"""
    marker = json.loads((skill / ".token-io-skill.json").read_bytes())
    shutil.rmtree(skill)
    skill.mkdir()
    contents = {
        "SKILL.md": b"---\nname: token-io-decoupling-skill\n---\nEnglish entry\n",
        "SKILL_zh_cn.md": "旧中文入口\n".encode(),
        "instructions/unit.0123456789abcdef.md": b"retired generated document\n",
        "instruction-index.json": json.dumps(
            {
                "schema_version": 2,
                "checkpoints": {
                    "contract": {
                        "documents": {
                            "en": "SKILL.md",
                            "zh_cn": "SKILL_zh_cn.md",
                        }
                    }
                },
            }
        ).encode(),
    }
    manifest = {
        "schema_version": 2,
        "build_id": "1" * 64,
        "files": {name: hashlib.sha256(data).hexdigest() for name, data in contents.items()},
    }
    contents["manifest.json"] = json.dumps(manifest).encode()
    for name, data in contents.items():
        destination = skill / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
    marker["build_id"] = manifest["build_id"]
    marker["files"] = {name: hashlib.sha256(data).hexdigest() for name, data in contents.items()}
    (skill / ".token-io-skill.json").write_text(json.dumps(marker, sort_keys=True))

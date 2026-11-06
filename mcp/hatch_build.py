"""Validate approved Skill resources without compiling or collecting author sources."""

from __future__ import annotations

import hashlib
import json
import runpy
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


def _workspace_skill_identity(workflow_project: Path) -> tuple[str, dict[str, str]]:
    """核对 checkout 中 workflow 资源的版本与完整字节，绑定同批 Skill 清单。"""
    resources = workflow_project / "src/token_io_decoupling_workflow/_resources"
    try:
        if resources.is_symlink() or any(
            path.is_symlink() or not path.is_file()
            for path in (resources / "manifest.json", resources / "instructions.json")
        ):
            raise ValueError("compiled core resources are unavailable or unsafe")
        manifest = json.loads((resources / "manifest.json").read_bytes())
        payload = (resources / "instructions.json").read_bytes()
        instructions = json.loads(payload)
        if not isinstance(manifest, dict) or not isinstance(instructions, dict):
            raise ValueError("compiled core resources must be objects")
        build_id = manifest.get("build_id")
        files = instructions.get("skill_files")
        if (
            type(manifest.get("schema_version")) is not int
            or manifest["schema_version"] != 3
            or type(instructions.get("schema_version")) is not int
            or instructions["schema_version"] != 3
            or manifest.get("language") != "zh_cn"
            or instructions.get("language") != "zh_cn"
            or not isinstance(build_id, str)
            or not build_id.strip()
            or instructions.get("build_id") != build_id
            or manifest.get("files") != {"instructions.json": hashlib.sha256(payload).hexdigest()}
            or not isinstance(files, dict)
            or not files
        ):
            raise ValueError("compiled core resources are corrupt or incompatible")
        return build_id, files
    except (OSError, UnicodeError, ValueError, TypeError) as exc:
        raise RuntimeError(f"invalid compiled core resources: {exc}") from exc


def validate_compiled_skill(project: Path) -> None:
    """构建前验证批准归档；不编译作者源，也不依赖已安装的产品服务。"""
    bundle = project / "src/token_io_decoupling/_resources/skill_bundle.zip"
    if bundle.parent.is_symlink() or bundle.is_symlink() or not bundle.is_file():
        raise RuntimeError("approved compiled Skill bundle is unavailable")
    if {path.name for path in bundle.parent.iterdir()} != {"skill_bundle.zip"}:
        raise RuntimeError("compiled Skill resource inventory does not match its allowlist")
    workflow_project = project / "packages/token_io_decoupling_workflow"
    expected_build_id = None
    expected_files = None
    if workflow_project.exists():
        expected_build_id, expected_files = _workspace_skill_identity(workflow_project)
    # 构建环境尚无产品包，固定加载无服务导入、仅依赖标准库的归档校验器。
    validator = runpy.run_path(str(project / "src/token_io_decoupling/skill_bundle.py"))[
        "validate_skill_bundle"
    ]
    try:
        validator(
            bundle.read_bytes(), expected_build_id=expected_build_id, expected_files=expected_files
        )
    except ValueError as exc:
        raise RuntimeError(f"invalid compiled Skill bundle: {exc}") from exc


class SkillBuildHook(BuildHookInterface):
    """根分发包的静态资源守卫，不在构建期间生成新政策。"""

    def initialize(self, version, build_data):
        """打包前拒绝缺失、混批或损坏的 Skill 资源。"""
        del version, build_data
        validate_compiled_skill(Path(self.root))

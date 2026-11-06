"""Validate approved compiled resources; packaging never invokes the compiler."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class RuleResourcesBuildHook(BuildHookInterface):
    """只核验批准的 workflow 编译资源，不在产品构建中读取作者源。"""

    def initialize(self, version, build_data):
        """构建前执行版本、清单与内容完整性检查。"""
        del version, build_data
        resources = Path(self.root) / "src/token_io_decoupling_workflow/_resources"
        try:
            if resources.is_symlink() or not resources.is_dir():
                raise ValueError("compiled resources are unavailable")
            expected = {"manifest.json", "instructions.json"}
            if {path.name for path in resources.iterdir()} != expected:
                raise ValueError("compiled resource inventory does not match its allowlist")
            if any(path.is_symlink() or not path.is_file() for path in resources.iterdir()):
                raise ValueError("compiled resources must be regular files")
            manifest = json.loads((resources / "manifest.json").read_text(encoding="utf-8"))
            payload = (resources / "instructions.json").read_bytes()
            instructions = json.loads(payload)
            if not isinstance(manifest, dict) or not isinstance(instructions, dict):
                raise ValueError("compiled resources must be JSON objects")
            build_id = manifest.get("build_id")
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
            ):
                raise ValueError("incompatible or mixed-batch compiled resources")
            if manifest.get("files") != {"instructions.json": hashlib.sha256(payload).hexdigest()}:
                raise ValueError("compiled instruction integrity check failed")
        except (OSError, UnicodeError, ValueError, TypeError) as exc:
            raise RuntimeError(f"invalid approved compiled resources: {exc}") from exc

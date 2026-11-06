"""Validate approved Skill resources without compiling or collecting author sources."""

from __future__ import annotations

import hashlib
import json
import runpy
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


def validate_compiled_skill(project: Path) -> None:
    bundle = project / "src/token_io_decoupling/_resources/skill_bundle.zip"
    if bundle.parent.is_symlink() or bundle.is_symlink() or not bundle.is_file():
        raise RuntimeError("approved compiled Skill bundle is unavailable")
    if {path.name for path in bundle.parent.iterdir()} != {"skill_bundle.zip"}:
        raise RuntimeError("compiled Skill resource inventory does not match its allowlist")
    workflow_project = project / "packages/token_io_decoupling_workflow"
    expected_build_id = None
    expected_files = None
    if workflow_project.exists():
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
            expected_build_id = manifest.get("build_id")
            expected_files = instructions.get("skill_files")
            if (
                manifest.get("schema_version") != 2
                or instructions.get("schema_version") != 2
                or not isinstance(expected_build_id, str)
                or not expected_build_id.strip()
                or instructions.get("build_id") != expected_build_id
                or manifest.get("files")
                != {"instructions.json": hashlib.sha256(payload).hexdigest()}
                or not isinstance(expected_files, dict)
                or not expected_files
            ):
                raise ValueError("compiled core resources are corrupt or incompatible")
        except (OSError, UnicodeError, ValueError, TypeError) as exc:
            raise RuntimeError(f"invalid compiled core resources: {exc}") from exc
    validator = runpy.run_path(str(project / "src/token_io_decoupling/skills.py"))[
        "validate_skill_bundle"
    ]
    try:
        validator(
            bundle.read_bytes(), expected_build_id=expected_build_id, expected_files=expected_files
        )
    except ValueError as exc:
        raise RuntimeError(f"invalid compiled Skill bundle: {exc}") from exc


class SkillBuildHook(BuildHookInterface):
    def initialize(self, version, build_data):
        del version, build_data
        validate_compiled_skill(Path(self.root))

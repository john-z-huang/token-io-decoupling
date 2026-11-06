"""Validate approved compiled resources; packaging never invokes the compiler."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class RuleResourcesBuildHook(BuildHookInterface):
    def initialize(self, version, build_data):
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
                manifest.get("schema_version") != 2
                or instructions.get("schema_version") != 2
                or not isinstance(build_id, str)
                or not build_id.strip()
                or instructions.get("build_id") != build_id
            ):
                raise ValueError("incompatible or mixed-batch compiled resources")
            if manifest.get("files") != {"instructions.json": hashlib.sha256(payload).hexdigest()}:
                raise ValueError("compiled instruction integrity check failed")
        except (OSError, UnicodeError, ValueError, TypeError) as exc:
            raise RuntimeError(f"invalid approved compiled resources: {exc}") from exc

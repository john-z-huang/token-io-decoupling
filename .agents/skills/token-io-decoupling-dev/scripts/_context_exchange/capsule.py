"""按顺序组织胶囊校验，区分错误和新鲜度警告。"""

from __future__ import annotations

import subprocess
from pathlib import Path

from .manifest import (
    _capsule_directory,
    _capsule_required_files,
    _capsule_source_entries,
    _read_capsule_manifest,
    _validate_capsule_manifest,
)
from .snapshot import _capsule_snapshot_mismatches, _check_capsule_sources, _read_capsule_snapshot


def validate_capsule(
    root: Path, errors: list[str], warnings: list[str], strict_freshness: bool
) -> None:
    """依次检查目录、清单、Git 快照与来源，保持错误和警告的累积顺序。"""
    capsule_path = _capsule_directory(root, errors)
    if capsule_path is None:
        return
    required_states = _capsule_required_files(capsule_path, errors)
    manifest = _read_capsule_manifest(root, capsule_path, required_states, errors)
    if manifest is None:
        return
    _validate_capsule_manifest(manifest, errors)
    validated_entries = _capsule_source_entries(root, manifest, errors)
    stale: list[str] = []
    try:
        snapshot = _read_capsule_snapshot(root, errors)
        stale.extend(_capsule_snapshot_mismatches(manifest, snapshot))
        _check_capsule_sources(root, validated_entries, errors, stale)
    except (RuntimeError, subprocess.CalledProcessError) as exc:
        errors.append(f"unable to evaluate capsule freshness: {exc}")

    if stale:
        message = (
            "capsule freshness mismatch; refresh affected sections before relying on it: "
            + ", ".join(stale)
        )
        if strict_freshness:
            errors.append(message)
        else:
            warnings.append(message)

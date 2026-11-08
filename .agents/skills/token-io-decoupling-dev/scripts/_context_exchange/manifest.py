"""有界读取胶囊清单并校验格式、必需字段和来源记录。"""

from __future__ import annotations

import os
import re
import stat
from pathlib import Path

from .filesystem import is_symlink, lstat_existing, safe_source_path
from .models import CAPSULE_DIR, MAX_CONTEXT_BYTES, SOURCE_ROW_RE, SourceEntry


def _capsule_directory(root: Path, errors: list[str]) -> Path | None:
    capsule_path = root / CAPSULE_DIR
    capsule_state = lstat_existing(capsule_path, errors, str(CAPSULE_DIR))
    if capsule_state is None:
        print("Context Bootstrap capsule absent; accepted.")
        return
    if is_symlink(capsule_state.st_mode):
        errors.append(f"capsule hierarchy must not contain a symlink: {CAPSULE_DIR}")
        return
    if not stat.S_ISDIR(capsule_state.st_mode):
        errors.append(f"capsule hierarchy must be a directory: {CAPSULE_DIR}")
        return

    return capsule_path


def _capsule_required_files(capsule_path: Path, errors: list[str]) -> dict[str, os.stat_result]:
    required_files = ("MANIFEST.md", "project-context.md", "policy-context.md")
    required_states: dict[str, os.stat_result] = {}
    for name in required_files:
        path = capsule_path / name
        state = lstat_existing(path, errors, str(CAPSULE_DIR / name))
        if state is None:
            errors.append(f"present capsule is missing {CAPSULE_DIR / name}")
        elif is_symlink(state.st_mode):
            errors.append(f"capsule file must not be a symlink: {CAPSULE_DIR / name}")
        elif not stat.S_ISREG(state.st_mode):
            errors.append(f"capsule file must be regular: {CAPSULE_DIR / name}")
        elif state.st_size > MAX_CONTEXT_BYTES:
            errors.append(
                f"capsule document exceeds {MAX_CONTEXT_BYTES} bytes: {CAPSULE_DIR / name}"
            )
        else:
            required_states[name] = state

    return required_states


def _read_capsule_manifest(
    root: Path, capsule_path: Path, required_states: dict[str, os.stat_result], errors: list[str]
) -> str | None:
    manifest_path = capsule_path / "MANIFEST.md"
    manifest_state = required_states.get("MANIFEST.md")
    if manifest_state is None:
        return
    try:
        with manifest_path.open("rb") as handle:
            manifest_bytes = handle.read(MAX_CONTEXT_BYTES + 1)
    except OSError as exc:
        errors.append(f"unable to read capsule manifest: {exc}")
        return
    if len(manifest_bytes) > MAX_CONTEXT_BYTES:
        errors.append(
            f"manifest exceeds {MAX_CONTEXT_BYTES} bytes: {manifest_path.relative_to(root)}"
        )
        return
    try:
        manifest = manifest_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        errors.append(f"capsule manifest is not valid UTF-8: {exc}")
        return
    return manifest


def _validate_capsule_manifest(manifest: str, errors: list[str]) -> None:
    required_sections = (
        "## Snapshot identity",
        "## Authoritative source fingerprints",
        "## Freshness contract",
    )
    for section in required_sections:
        if section not in manifest:
            errors.append(f"manifest is missing required section: {section}")
    required_fields = {
        "Captured:": r"(?m)^-\s+Captured:\s+\S",
        "Repository:": r"(?m)^-\s+Repository:\s+\S",
        "HEAD:": r"(?m)^-\s+`?HEAD`?(?:\s+and\s+[^:]+)?:\s*`?[0-9a-f]{40}",
        "HEAD^{tree}:": r"(?m)^-\s+`?HEAD\^\{tree\}`?:\s*`?[0-9a-f]{40}",
        "Tracked delta from HEAD:": r"(?m)^-\s+Tracked delta from `?HEAD`?:\s+",
        "SHA-256 tracked-delta fingerprint": (
            r"SHA-256 of `git diff HEAD --binary` is `?[0-9a-f]{64}"
        ),
        "Non-coordination working-tree scope": (
            r"(?m)^-\s+Non-coordination working-tree scope:\s*\d+\s+paths?\b"
        ),
        "SHA-256 filtered porcelain status": (
            r"SHA-256 of filtered porcelain status is `?[0-9a-f]{64}"
        ),
    }
    for label, pattern in required_fields.items():
        if not re.search(pattern, manifest, re.IGNORECASE):
            errors.append(f"manifest is missing required freshness field: {label}")
    if not re.search(r"(?m)^\s*[-\d]+\.\s+", manifest):
        errors.append("manifest freshness contract must contain numbered invalidation rules")


def _capsule_source_entries(root: Path, manifest: str, errors: list[str]) -> list[SourceEntry]:
    source_entries = [
        SourceEntry(name=match.group(1).strip(), recorded_hash=match.group(2), path=None)
        for match in SOURCE_ROW_RE.finditer(manifest)
    ]
    if not source_entries:
        errors.append("manifest must contain at least one 40-hex source fingerprint row")

    validated_entries: list[SourceEntry] = []
    for entry in source_entries:
        validated_entries.append(entry._replace(path=safe_source_path(root, entry.name, errors)))

    return validated_entries

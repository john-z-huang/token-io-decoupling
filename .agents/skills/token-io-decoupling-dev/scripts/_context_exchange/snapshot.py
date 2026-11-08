"""对比清单与当前 Git 状态及来源文件指纹。"""

from __future__ import annotations

import hashlib
import re
import stat
import subprocess
from pathlib import Path

from .filesystem import git_output, is_symlink, lstat_existing
from .models import EXCHANGE_DIR, SourceEntry, _CapsuleWorktreeSnapshot


def _read_capsule_snapshot(root: Path, errors: list[str]) -> _CapsuleWorktreeSnapshot:
    current_head = git_output(root, "rev-parse", "HEAD").strip()
    current_tree = git_output(root, "rev-parse", "HEAD^{tree}").strip()
    diff = subprocess.run(
        ["git", "diff", "HEAD", "--binary"],
        cwd=root,
        check=True,
        capture_output=True,
    ).stdout
    current_diff = hashlib.sha256(diff).hexdigest()
    current_status = git_output(
        root,
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
        "--",
        ".",
        f":(exclude){EXCHANGE_DIR.as_posix()}/",
    )
    if EXCHANGE_DIR.as_posix() in current_status:
        errors.append(
            "filtered porcelain status unexpectedly contains the ignored Context Exchange root"
        )
    return _CapsuleWorktreeSnapshot(current_head, current_tree, current_diff, current_status)


def _capsule_snapshot_mismatches(manifest: str, snapshot: _CapsuleWorktreeSnapshot) -> list[str]:
    stale: list[str] = []
    current_head, current_tree, current_diff, current_status = snapshot
    current_status_hash = hashlib.sha256(current_status.encode("utf-8")).hexdigest()
    head_match = re.search(
        r"(?m)^-\s+`?HEAD`?(?:\s+and\s+[^:]+)?:\s*`?([0-9a-f]{40})", manifest, re.IGNORECASE
    )
    tree_match = re.search(
        r"(?m)^-\s+`?HEAD\^\{tree\}`?:\s*`?([0-9a-f]{40})", manifest, re.IGNORECASE
    )
    diff_match = re.search(
        r"SHA-256 of `git diff HEAD --binary` is `?([0-9a-f]{64})", manifest, re.IGNORECASE
    )
    status_match = re.search(
        r"(?m)^-\s+Non-coordination working-tree scope:\s*(\d+)\s+paths?\b.*?"
        r"SHA-256 of filtered porcelain status is `?([0-9a-f]{64})",
        manifest,
        re.IGNORECASE,
    )
    if not head_match or head_match.group(1).lower() != current_head.lower():
        stale.append("HEAD")
    if not tree_match or tree_match.group(1).lower() != current_tree.lower():
        stale.append("HEAD^{tree}")
    if not diff_match or diff_match.group(1).lower() != current_diff.lower():
        stale.append("tracked-delta fingerprint")
    if not status_match:
        stale.append("non-coordination working-tree scope/fingerprint")
    else:
        if int(status_match.group(1)) != len(current_status.splitlines()):
            stale.append("non-coordination working-tree scope")
        if status_match.group(2).lower() != current_status_hash.lower():
            stale.append("filtered porcelain status fingerprint")

    return stale


def _check_capsule_sources(
    root: Path, validated_entries: list[SourceEntry], errors: list[str], stale: list[str]
) -> None:
    for entry in validated_entries:
        if entry.path is None:
            continue
        source_state = lstat_existing(entry.path, errors, f"source path {entry.name}")
        if source_state is None:
            stale.append(f"missing source {entry.name}")
            continue
        if is_symlink(source_state.st_mode):
            errors.append(f"source path must not contain a symlink: {entry.name}")
            continue
        if not stat.S_ISREG(source_state.st_mode):
            errors.append(f"source path must be a regular file: {entry.name}")
            continue
        source_hash = git_output(root, "hash-object", entry.name).strip()
        if source_hash.lower() != entry.recorded_hash.lower():
            stale.append(f"source hash {entry.name}")

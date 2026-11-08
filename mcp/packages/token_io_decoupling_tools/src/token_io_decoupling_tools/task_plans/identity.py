"""项目 Git 身份与 Serena Memory 根目录的校验。"""

from __future__ import annotations

import hashlib
import os
import stat
import subprocess
from pathlib import Path

from .constants import (
    _GIT_IDENTITY_DOMAIN,
    _GIT_IDENTITY_MAX_OUTPUT_BYTES,
    _GIT_IDENTITY_TIMEOUT_SECONDS,
    _GIT_REDIRECT_ENVIRONMENT,
)
from .types import TaskPlanFailure


def _run_git_identity(checkout_root: Path) -> bytes:
    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(checkout_root),
                "rev-parse",
                "--path-format=absolute",
                "--show-toplevel",
                "--git-common-dir",
            ],
            check=False,
            capture_output=True,
            timeout=_GIT_IDENTITY_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise TaskPlanFailure("git_identity_timeout", "unavailable") from exc
    except OSError as exc:
        raise TaskPlanFailure("git_identity_unavailable", "unavailable") from exc
    if (
        result.returncode != 0
        or len(result.stdout) > _GIT_IDENTITY_MAX_OUTPUT_BYTES
        or len(result.stderr) > _GIT_IDENTITY_MAX_OUTPUT_BYTES
    ):
        raise TaskPlanFailure("git_identity_unavailable", "unavailable")

    return result.stdout


def _parse_git_identity(output: bytes, checkout_root: Path) -> Path:
    try:
        output_lines = output.decode(errors="surrogateescape").splitlines()
        if len(output_lines) != 2:
            raise TaskPlanFailure("git_identity_output_invalid", "unavailable")
        reported_root = Path(output_lines[0])
        common_dir = Path(output_lines[1])
        if not reported_root.is_absolute() or not common_dir.is_absolute():
            raise TaskPlanFailure("git_identity_output_invalid", "unavailable")
        canonical_reported_root = reported_root.resolve(strict=True)
        canonical_common_dir = common_dir.resolve(strict=True)
        if canonical_reported_root != checkout_root or not canonical_common_dir.is_dir():
            raise TaskPlanFailure("git_identity_output_invalid", "unavailable")
    except TaskPlanFailure:
        raise
    except (OSError, ValueError) as exc:
        raise TaskPlanFailure("git_identity_output_invalid", "unavailable") from exc

    return canonical_common_dir


def _repository_id_for_checkout(project_root: str | Path) -> str:
    """Derive a local repository identity from a verified Git common directory."""
    checkout_path = Path(project_root)
    if not checkout_path.is_absolute():
        raise TaskPlanFailure("project_root_must_be_absolute", "unavailable")
    try:
        checkout_root = checkout_path.resolve(strict=True)
    except OSError as exc:
        raise TaskPlanFailure("project_root_unavailable", "unavailable") from exc
    if not checkout_root.is_dir():
        raise TaskPlanFailure("project_root_unavailable", "unavailable")

    if any(os.environ.get(name) for name in _GIT_REDIRECT_ENVIRONMENT):
        raise TaskPlanFailure("git_environment_redirected", "unavailable")

    output = _run_git_identity(checkout_root)
    canonical_common_dir = _parse_git_identity(output, checkout_root)

    digest = hashlib.sha256(
        _GIT_IDENTITY_DOMAIN + os.fsencode(str(canonical_common_dir))
    ).hexdigest()
    return f"git-v1-{digest}"


def _memory_root_for(memory_manager: object, storage_scope: str) -> Path:
    root_attribute = "_project_memory_dir" if storage_scope == "project" else "_global_memory_dir"
    unavailable_reason = (
        "serena_project_memory_unavailable"
        if storage_scope == "project"
        else "serena_global_memory_unavailable"
    )
    invalid_reason = (
        "serena_project_memory_invalid"
        if storage_scope == "project"
        else "serena_global_memory_invalid"
    )
    root_value = getattr(memory_manager, root_attribute, None)
    if not isinstance(root_value, (str, Path)):
        raise TaskPlanFailure(unavailable_reason, "unavailable")
    root_path = Path(root_value)
    try:
        root_stat = root_path.lstat()
        if (
            not root_path.is_absolute()
            or stat.S_ISLNK(root_stat.st_mode)
            or not stat.S_ISDIR(root_stat.st_mode)
        ):
            raise TaskPlanFailure(invalid_reason, "unavailable")
        memory_root = root_path.resolve(strict=True)
    except TaskPlanFailure:
        raise
    except OSError as exc:
        raise TaskPlanFailure(unavailable_reason, "unavailable") from exc

    return memory_root


def _canonical_plan_project_root(project_root: str | Path) -> str:
    project_path = Path(project_root)
    if not project_path.is_absolute():
        raise TaskPlanFailure("project_root_must_be_absolute", "unavailable")
    try:
        canonical_root = str(project_path.resolve(strict=True))
        if not Path(canonical_root).is_dir():
            raise TaskPlanFailure("project_root_unavailable", "unavailable")
    except TaskPlanFailure:
        raise
    except OSError as exc:
        raise TaskPlanFailure("project_root_unavailable", "unavailable") from exc

    return canonical_root

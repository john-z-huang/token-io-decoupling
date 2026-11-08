"""在层级校验通过后检测根忽略规则与探针保留情况。"""

from __future__ import annotations

import stat
import tempfile
from pathlib import Path

from .filesystem import git_output, is_symlink, lstat_existing, run_git
from .models import CAPSULE_DIR, EXCHANGE_DIR, IGNORE_RULE, MAX_CONTEXT_BYTES


def _validate_capsule_hierarchy(context_path: Path, errors: list[str]) -> bool:
    capsule_path = context_path / "context-bootstrap"
    capsule_state = lstat_existing(capsule_path, errors, str(CAPSULE_DIR))
    if capsule_state is None:
        return True
    if is_symlink(capsule_state.st_mode):
        errors.append(f"capsule hierarchy must not contain a symlink: {CAPSULE_DIR}")
        return False
    if not stat.S_ISDIR(capsule_state.st_mode):
        errors.append(f"capsule hierarchy must be a directory: {CAPSULE_DIR}")
        return False

    safe = True
    for name in ("MANIFEST.md", "project-context.md", "policy-context.md"):
        path = capsule_path / name
        state = lstat_existing(path, errors, str(CAPSULE_DIR / name))
        if state is None:
            errors.append(f"present capsule is missing {CAPSULE_DIR / name}")
            safe = False
        elif is_symlink(state.st_mode):
            errors.append(f"capsule file must not be a symlink: {CAPSULE_DIR / name}")
            safe = False
        elif not stat.S_ISREG(state.st_mode):
            errors.append(f"capsule file must be regular: {CAPSULE_DIR / name}")
            safe = False
        elif state.st_size > MAX_CONTEXT_BYTES:
            errors.append(
                f"capsule document exceeds {MAX_CONTEXT_BYTES} bytes: {CAPSULE_DIR / name}"
            )
            safe = False
    return safe


def validate_hierarchy(root: Path, errors: list[str]) -> bool:
    """Validate every coordination path before check_ignore_policy can write a probe."""

    exchange_path = root / EXCHANGE_DIR
    exchange_state = lstat_existing(exchange_path, errors, str(EXCHANGE_DIR))
    if exchange_state is None:
        return True
    if is_symlink(exchange_state.st_mode):
        errors.append(f"coordination hierarchy must not contain a symlink: {EXCHANGE_DIR}")
        return False
    if not stat.S_ISDIR(exchange_state.st_mode):
        errors.append(f"coordination hierarchy must be a directory: {EXCHANGE_DIR}")
        return False

    context_path = exchange_path / "context"
    context_state = lstat_existing(context_path, errors, str(EXCHANGE_DIR / "context"))
    if context_state is None:
        return True
    if is_symlink(context_state.st_mode):
        errors.append(
            f"coordination hierarchy must not contain a symlink: {EXCHANGE_DIR / 'context'}"
        )
        return False
    if not stat.S_ISDIR(context_state.st_mode):
        errors.append(f"coordination hierarchy must be a directory: {EXCHANGE_DIR / 'context'}")
        return False

    return _validate_capsule_hierarchy(context_path, errors)


def _probe_ignore_preservation(
    root: Path, exchange_path: Path, existed_before: bool, write_sentinel: bool, errors: list[str]
) -> None:
    sentinel: Path | None = None
    try:
        context_path = exchange_path / "context"
        context_state = lstat_existing(context_path, errors, str(EXCHANGE_DIR / "context"))
        if (
            write_sentinel
            and existed_before
            and context_state is not None
            and stat.S_ISDIR(context_state.st_mode)
        ):
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                prefix=".context-exchange-validator-",
                dir=context_path,
                delete=False,
            ) as handle:
                handle.write("validator sentinel\n")
                sentinel = Path(handle.name)
            status = git_output(
                root, "status", "--short", "--untracked-files=all", "--", EXCHANGE_DIR.as_posix()
            )
            if status.strip():
                errors.append("ignored Context Exchange probe appeared in git status")
            if not sentinel.exists():
                errors.append("Context Exchange sentinel was not preserved during validation")
            if not exchange_path.is_dir():
                errors.append("Context Exchange directory was removed during validation")
    finally:
        if sentinel is not None:
            sentinel.unlink(missing_ok=True)


def check_ignore_policy(root: Path, errors: list[str], write_sentinel: bool) -> None:
    gitignore = root / ".gitignore"
    if not gitignore.is_file():
        errors.append("missing root .gitignore")
        return

    rules = [line.strip() for line in gitignore.read_text(encoding="utf-8").splitlines()]
    if IGNORE_RULE not in rules:
        errors.append(
            f"root .gitignore must contain the Context Exchange ignore rule {IGNORE_RULE!r}"
        )

    probe = EXCHANGE_DIR / "context" / ".context-exchange-validator-probe"
    ignored = run_git(root, "check-ignore", "-q", "--", probe.as_posix())
    if ignored.returncode != 0:
        errors.append(f"git check-ignore did not match {probe}")
    else:
        detail = run_git(root, "check-ignore", "-v", "--", probe.as_posix())
        detail_source = detail.stdout.split("\t", 1)[0].split(":", 1)[0] if detail.stdout else ""
        if detail.returncode != 0 or detail_source not in {
            ".gitignore",
            (root / ".gitignore").as_posix(),
        }:
            errors.append("git check-ignore did not resolve the probe to the root .gitignore")

    tracked = git_output(root, "ls-files", "--", EXCHANGE_DIR.as_posix()).strip()
    if tracked:
        errors.append(f"Context Exchange must not be tracked: {tracked.splitlines()[0]}")

    exchange_path = root / EXCHANGE_DIR
    existed_before = lstat_existing(exchange_path, errors, str(EXCHANGE_DIR)) is not None
    _probe_ignore_preservation(root, exchange_path, existed_before, write_sentinel, errors)

    if existed_before and not exchange_path.is_dir():
        errors.append("pre-existing Context Exchange directory was not preserved")

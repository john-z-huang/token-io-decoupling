#!/usr/bin/env python3
"""Validate the ignored Context Exchange directory and optional bootstrap capsule."""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import stat
import subprocess
import sys
import tempfile
from pathlib import Path
from pathlib import PurePosixPath
from typing import NamedTuple


IGNORE_RULE = "/.token-io-decoupling/"
EXCHANGE_DIR = Path(".token-io-decoupling")
CAPSULE_DIR = EXCHANGE_DIR / "context" / "context-bootstrap"
MAX_CONTEXT_BYTES = 64 * 1024
SOURCE_ROW_RE = re.compile(
    r"(?m)^\|\s*`?([^|`]+?)`?\s*\|\s*`?([0-9a-f]{40})`?\s*\|\s*$", re.IGNORECASE
)


class SourceEntry(NamedTuple):
    name: str
    recorded_hash: str
    path: Path | None


def run_git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def git_output(root: Path, *args: str) -> str:
    result = run_git(root, *args)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout


def lstat_existing(path: Path, errors: list[str], label: str) -> os.stat_result | None:
    try:
        return path.lstat()
    except FileNotFoundError:
        return None
    except OSError as exc:
        errors.append(f"unable to inspect {label}: {exc}")
        return None


def is_symlink(mode: int) -> bool:
    return stat.S_ISLNK(mode)


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
        errors.append(f"coordination hierarchy must not contain a symlink: {EXCHANGE_DIR / 'context'}")
        return False
    if not stat.S_ISDIR(context_state.st_mode):
        errors.append(f"coordination hierarchy must be a directory: {EXCHANGE_DIR / 'context'}")
        return False

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
            errors.append(f"capsule document exceeds {MAX_CONTEXT_BYTES} bytes: {CAPSULE_DIR / name}")
            safe = False
    return safe


def check_ignore_policy(root: Path, errors: list[str], write_sentinel: bool) -> None:
    gitignore = root / ".gitignore"
    if not gitignore.is_file():
        errors.append("missing root .gitignore")
        return

    rules = [line.strip() for line in gitignore.read_text(encoding="utf-8").splitlines()]
    if IGNORE_RULE not in rules:
        errors.append(f"root .gitignore must contain the anchored rule {IGNORE_RULE!r}")

    probe = EXCHANGE_DIR / "context" / ".context-exchange-validator-probe"
    ignored = run_git(root, "check-ignore", "-q", "--", probe.as_posix())
    if ignored.returncode != 0:
        errors.append(f"git check-ignore did not match {probe}")
    else:
        detail = run_git(root, "check-ignore", "-v", "--", probe.as_posix())
        detail_source = detail.stdout.split("\t", 1)[0].split(":", 1)[0] if detail.stdout else ""
        if detail.returncode != 0 or detail_source not in {".gitignore", (root / ".gitignore").as_posix()}:
            errors.append("git check-ignore did not resolve the probe to the root .gitignore")

    tracked = git_output(root, "ls-files", "--", EXCHANGE_DIR.as_posix()).strip()
    if tracked:
        errors.append(f"Context Exchange must not be tracked: {tracked.splitlines()[0]}")

    exchange_path = root / EXCHANGE_DIR
    existed_before = lstat_existing(exchange_path, errors, str(EXCHANGE_DIR)) is not None
    sentinel: Path | None = None
    try:
        context_path = exchange_path / "context"
        context_state = lstat_existing(context_path, errors, str(EXCHANGE_DIR / "context"))
        if write_sentinel and existed_before and context_state is not None and stat.S_ISDIR(context_state.st_mode):
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", prefix=".context-exchange-validator-", dir=context_path, delete=False
            ) as handle:
                handle.write("validator sentinel\n")
                sentinel = Path(handle.name)
            status = git_output(root, "status", "--short", "--untracked-files=all", "--", EXCHANGE_DIR.as_posix())
            if status.strip():
                errors.append("ignored Context Exchange probe appeared in git status")
            if not sentinel.exists():
                errors.append("Context Exchange sentinel was not preserved during validation")
            if not exchange_path.is_dir():
                errors.append("Context Exchange directory was removed during validation")
    finally:
        if sentinel is not None:
            sentinel.unlink(missing_ok=True)

    if existed_before and not exchange_path.is_dir():
        errors.append("pre-existing Context Exchange directory was not preserved")


def safe_source_path(root: Path, source: str, errors: list[str]) -> Path | None:
    """Return a repository-contained source path after lstat validation."""

    source = source.strip()
    if not source or "\x00" in source or source.startswith(("/", "\\")) or re.match(r"^[A-Za-z]:", source):
        errors.append(f"source path must be repository-relative: {source or '<empty>'}")
        return None
    pure_source = PurePosixPath(source)
    if pure_source.is_absolute() or ".." in pure_source.parts or "\\" in source:
        errors.append(f"source path must not be absolute or contain parent traversal: {source}")
        return None

    candidate = root.joinpath(*pure_source.parts)
    root_real = root.resolve()
    current = root
    for part in pure_source.parts:
        current = current / part
        state = lstat_existing(current, errors, f"source path {source}")
        if state is None:
            return candidate
        if is_symlink(state.st_mode):
            errors.append(f"source path must not contain a symlink: {source}")
            return None

    try:
        candidate.resolve(strict=False).relative_to(root_real)
    except ValueError:
        errors.append(f"source path escapes the repository: {source}")
        return None

    final_state = lstat_existing(candidate, errors, f"source path {source}")
    if final_state is not None and not stat.S_ISREG(final_state.st_mode):
        errors.append(f"source path must be a regular file: {source}")
        return None
    return candidate


def validate_capsule(root: Path, errors: list[str], warnings: list[str], strict_freshness: bool) -> None:
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
            errors.append(f"capsule document exceeds {MAX_CONTEXT_BYTES} bytes: {CAPSULE_DIR / name}")
        else:
            required_states[name] = state

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
        errors.append(f"manifest exceeds {MAX_CONTEXT_BYTES} bytes: {manifest_path.relative_to(root)}")
        return
    try:
        manifest = manifest_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        errors.append(f"capsule manifest is not valid UTF-8: {exc}")
        return
    required_sections = ("## Snapshot identity", "## Authoritative source fingerprints", "## Freshness contract")
    for section in required_sections:
        if section not in manifest:
            errors.append(f"manifest is missing required section: {section}")
    required_fields = {
        "Captured:": r"(?m)^-\s+Captured:\s+\S",
        "Repository:": r"(?m)^-\s+Repository:\s+\S",
        "HEAD:": r"(?m)^-\s+`?HEAD`?(?:\s+and\s+[^:]+)?:\s*`?[0-9a-f]{40}",
        "HEAD^{tree}:": r"(?m)^-\s+`?HEAD\^\{tree\}`?:\s*`?[0-9a-f]{40}",
        "Tracked delta from HEAD:": r"(?m)^-\s+Tracked delta from `?HEAD`?:\s+",
        "SHA-256 tracked-delta fingerprint": r"SHA-256 of `git diff HEAD --binary` is `?[0-9a-f]{64}",
        "Non-coordination working-tree scope": r"(?m)^-\s+Non-coordination working-tree scope:\s*\d+\s+paths?\b",
        "SHA-256 filtered porcelain status": r"SHA-256 of filtered porcelain status is `?[0-9a-f]{64}",
    }
    for label, pattern in required_fields.items():
        if not re.search(pattern, manifest, re.IGNORECASE):
            errors.append(f"manifest is missing required freshness field: {label}")
    if not re.search(r"(?m)^\s*[-\d]+\.\s+", manifest):
        errors.append("manifest freshness contract must contain numbered invalidation rules")

    source_entries = [
        SourceEntry(name=match.group(1).strip(), recorded_hash=match.group(2), path=None)
        for match in SOURCE_ROW_RE.finditer(manifest)
    ]
    if not source_entries:
        errors.append("manifest must contain at least one 40-hex source fingerprint row")

    validated_entries: list[SourceEntry] = []
    for entry in source_entries:
        validated_entries.append(entry._replace(path=safe_source_path(root, entry.name, errors)))

    stale: list[str] = []
    try:
        current_head = git_output(root, "rev-parse", "HEAD").strip()
        current_tree = git_output(root, "rev-parse", "HEAD^{tree}").strip()
        diff = subprocess.run(
            ["git", "diff", "HEAD", "--binary"],
            cwd=root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
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
            errors.append("filtered porcelain status unexpectedly contains the ignored Context Exchange root")
        current_status_hash = hashlib.sha256(current_status.encode("utf-8")).hexdigest()
        head_match = re.search(r"(?m)^-\s+`?HEAD`?(?:\s+and\s+[^:]+)?:\s*`?([0-9a-f]{40})", manifest, re.IGNORECASE)
        tree_match = re.search(r"(?m)^-\s+`?HEAD\^\{tree\}`?:\s*`?([0-9a-f]{40})", manifest, re.IGNORECASE)
        diff_match = re.search(r"SHA-256 of `git diff HEAD --binary` is `?([0-9a-f]{64})", manifest, re.IGNORECASE)
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
    except (RuntimeError, subprocess.CalledProcessError) as exc:
        errors.append(f"unable to evaluate capsule freshness: {exc}")

    if stale:
        message = "capsule freshness mismatch; refresh affected sections before relying on it: " + ", ".join(stale)
        if strict_freshness:
            errors.append(message)
        else:
            warnings.append(message)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--allow-stale",
        action="store_true",
        help="report, but do not reject, snapshot drift while inspecting a capsule during refresh",
    )
    args = parser.parse_args()
    root = args.root.resolve()
    errors: list[str] = []
    warnings: list[str] = []
    try:
        hierarchy_safe = validate_hierarchy(root, errors)
        if hierarchy_safe:
            validate_capsule(root, errors, warnings, not args.allow_stale)
        # Never create a probe until all hierarchy, capsule, and source-path lstat checks have completed.
        check_ignore_policy(root, errors, write_sentinel=hierarchy_safe and not errors)
    except (OSError, UnicodeError, RuntimeError) as exc:
        errors.append(str(exc))

    for warning in warnings:
        print(f"Warning: {warning}", file=sys.stderr)
    if errors:
        print("Context Exchange validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("Context Exchange validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

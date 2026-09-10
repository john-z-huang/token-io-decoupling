#!/usr/bin/env python3
"""Regression fixtures for scripts/check-context-exchange.py."""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check-context-exchange.py"
EXCHANGE = Path(".token-io-decoupling")
CAPSULE = EXCHANGE / "context" / "context-bootstrap"
MAX_CONTEXT_BYTES = 64 * 1024


class ContextExchangeValidatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.git("init", "-q")
        self.git("config", "user.email", "validator@example.invalid")
        self.git("config", "user.name", "Context Validator")
        (self.root / ".gitignore").write_text("/.token-io-decoupling/\n", encoding="utf-8")
        (self.root / "README.md").write_text("fixture\n", encoding="utf-8")
        self.git("add", ".gitignore", "README.md")
        self.git("commit", "-m", "fixture")

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def git(self, *args: str, check: bool = True) -> str:
        result = subprocess.run(
            ["git", *args],
            cwd=self.root,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if check and result.returncode != 0:
            raise AssertionError(result.stderr)
        return result.stdout

    def validator(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--root", str(self.root), *args],
            cwd=ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def filtered_status(self) -> str:
        return self.git(
            "status",
            "--porcelain=v1",
            "--untracked-files=all",
            "--",
            ".",
            ":(exclude).token-io-decoupling/",
        )

    def write_capsule(self, source_entries: list[tuple[str, str | None]] | None = None) -> None:
        source_entries = source_entries or [("README.md", None)]
        capsule = self.root / CAPSULE
        capsule.mkdir(parents=True, exist_ok=True)
        (capsule / "project-context.md").write_text("# Project Context\n", encoding="utf-8")
        (capsule / "policy-context.md").write_text("# Policy Context\n", encoding="utf-8")
        head = self.git("rev-parse", "HEAD").strip()
        tree = self.git("rev-parse", "HEAD^{tree}").strip()
        diff = subprocess.run(
            ["git", "diff", "HEAD", "--binary"], cwd=self.root, check=True, stdout=subprocess.PIPE
        ).stdout
        status = self.filtered_status()
        rows: list[str] = []
        for source, recorded_hash in source_entries:
            if recorded_hash is None:
                recorded_hash = self.git("hash-object", source).strip()
            rows.append(f"| `{source}` | `{recorded_hash}` |")
        manifest = f"""# Context Bootstrap Manifest

Status: reusable factual baseline.

## Snapshot identity

- Captured: 2026-09-10T20:08:43+0800.
- Repository: `fixture`.
- Branch: `main`.
- `HEAD` and `origin/main`: `{head}`.
- `HEAD^{{tree}}`: `{tree}`.
- Tracked delta from `HEAD`: {len(self.git('diff', '--name-only', 'HEAD').splitlines())} modified paths; SHA-256 of `git diff HEAD --binary` is `{hashlib.sha256(diff).hexdigest()}`.
- Non-coordination working-tree scope: {len(status.splitlines())} paths; SHA-256 of filtered porcelain status is `{hashlib.sha256(status.encode('utf-8')).hexdigest()}`.

## Authoritative source fingerprints

| Source | Hash |
|---|---|
{chr(10).join(rows)}

## Freshness contract

1. HEAD/tree or tracked delta changes invalidate the capsule.
2. Relevant untracked project status changes invalidate the capsule.
3. Listed source hashes must match.
"""
        (capsule / "MANIFEST.md").write_text(manifest, encoding="utf-8")

    def test_absent_capsule_is_accepted(self) -> None:
        result = self.validator()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("absent", result.stdout)

    def test_fresh_capsule_and_sentinel_preservation(self) -> None:
        self.write_capsule()
        keep = self.root / EXCHANGE / "context" / "keep.md"
        keep.write_text("keep me\n", encoding="utf-8")
        result = self.validator()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(keep.is_file())
        self.assertTrue((self.root / EXCHANGE).is_dir())
        self.assertEqual(self.git("status", "--short", "--untracked-files=all", "--", EXCHANGE.as_posix()), "")

    def test_untracked_status_drift_and_allow_stale_boundary(self) -> None:
        self.write_capsule()
        (self.root / "new-untracked.txt").write_text("drift\n", encoding="utf-8")
        strict = self.validator()
        self.assertNotEqual(strict.returncode, 0)
        self.assertIn("non-coordination", strict.stderr)
        allowed = self.validator("--allow-stale")
        self.assertEqual(allowed.returncode, 0, allowed.stderr)
        self.assertIn("filtered porcelain status", allowed.stderr)

    def test_manifest_requires_recorded_status_scope_and_hash(self) -> None:
        self.write_capsule()
        manifest = self.root / CAPSULE / "MANIFEST.md"
        content = manifest.read_text(encoding="utf-8")
        content = "\n".join(
            line for line in content.splitlines() if "Non-coordination working-tree scope:" not in line
        ) + "\n"
        manifest.write_text(content, encoding="utf-8")
        result = self.validator("--allow-stale")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Non-coordination working-tree scope", result.stderr)

    def test_malformed_regular_file_hierarchy_is_rejected(self) -> None:
        exchange = self.root / EXCHANGE
        exchange.write_text("not a directory\n", encoding="utf-8")
        result = self.validator("--allow-stale")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must be a directory", result.stderr)
        exchange.unlink()
        exchange.mkdir()
        (exchange / "context").write_text("not a directory\n", encoding="utf-8")
        result = self.validator("--allow-stale")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("context", result.stderr)

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks unavailable")
    def test_hierarchy_symlink_is_rejected_without_writing_outside(self) -> None:
        outside = self.root.parent / f"{self.root.name}-outside"
        outside.mkdir()
        try:
            outside_context = outside / "context"
            outside_context.mkdir()
            os.symlink(outside, self.root / EXCHANGE)
            result = self.validator("--allow-stale")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("symlink", result.stderr)
            self.assertEqual(list(outside.glob("context/.context-exchange-validator-*")), [])
            (self.root / EXCHANGE).unlink()
            (self.root / EXCHANGE).mkdir()
            os.symlink(outside_context, self.root / EXCHANGE / "context")
            result = self.validator("--allow-stale")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("symlink", result.stderr)
            self.assertEqual(list(outside_context.glob(".context-exchange-validator-*")), [])
        finally:
            context_link = self.root / EXCHANGE / "context"
            if context_link.is_symlink():
                context_link.unlink()
            if (self.root / EXCHANGE).is_symlink():
                (self.root / EXCHANGE).unlink()
            if (self.root / EXCHANGE).is_dir():
                (self.root / EXCHANGE).rmdir()
            outside.joinpath("context").rmdir()
            outside.rmdir()

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks unavailable")
    def test_capsule_and_source_symlinks_are_rejected(self) -> None:
        outside = self.root.parent / f"{self.root.name}-capsule-outside"
        outside.mkdir()
        try:
            context = self.root / EXCHANGE / "context"
            context.mkdir(parents=True)
            os.symlink(outside, context / "context-bootstrap")
            result = self.validator("--allow-stale")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("symlink", result.stderr)
            self.assertEqual(list(outside.glob(".context-exchange-validator-*")), [])
            (context / "context-bootstrap").unlink()
            (outside / "leak.md").write_text("outside\n", encoding="utf-8")
            os.symlink(outside / "leak.md", self.root / "leak.md")
            self.write_capsule([("leak.md", "0" * 40)])
            result = self.validator("--allow-stale")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("symlink", result.stderr)
            (self.root / "leak.md").unlink()
        finally:
            if (self.root / "leak.md").is_symlink():
                (self.root / "leak.md").unlink()
            outside.joinpath("leak.md").unlink(missing_ok=True)
            outside.rmdir()

    def test_absolute_and_parent_source_paths_are_rejected_even_allow_stale(self) -> None:
        self.write_capsule([("/etc/passwd", "0" * 40), ("../outside.txt", "0" * 40)])
        result = self.validator("--allow-stale")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("repository-relative", result.stderr)
        self.assertIn("parent traversal", result.stderr)

    def test_manifest_size_limit_is_rejected_before_parse(self) -> None:
        capsule = self.root / CAPSULE
        capsule.mkdir(parents=True)
        (capsule / "project-context.md").write_text("small\n", encoding="utf-8")
        (capsule / "policy-context.md").write_text("small\n", encoding="utf-8")
        (capsule / "MANIFEST.md").write_bytes(b"x" * (MAX_CONTEXT_BYTES + 1))
        result = self.validator("--allow-stale")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("exceeds", result.stderr)


if __name__ == "__main__":
    unittest.main()

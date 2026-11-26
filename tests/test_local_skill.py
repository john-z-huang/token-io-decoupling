from __future__ import annotations

import hashlib
import json
import runpy
import sys
import unittest
from os.path import relpath
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from urllib.parse import unquote, urlsplit

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from document_rules import links_in_markdown
from local_skill import DEFAULT_NAME, MARKER, update_local_skill


class LocalSkillTests(unittest.TestCase):
    def test_compiler_retires_only_the_exact_legacy_generated_document(self):
        compiler = runpy.run_path(str(SCRIPTS / "compile-reference-dsl.py"))
        main = compiler["main"]
        with TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            skill = root / "skill"
            relative = "agents/retired.yaml"
            legacy = skill / relative
            legacy.parent.mkdir(parents=True)
            variants = (b"description: retired\n", b"description: legacy\n")
            fingerprints = {relative: [hashlib.sha256(body).hexdigest() for body in variants]}
            manifest = root / "retired.json"
            manifest.write_text(json.dumps(fingerprints), encoding="utf-8")
            outputs = {skill / "SKILL.md": "# Orchestration\n"}
            with patch.dict(main.__globals__, {
                "ROOT": root, "SKILL": skill, "RETIRED_FINGERPRINTS": manifest,
                "compile_rules": lambda: outputs,
            }), patch.object(sys, "stderr"), patch.object(sys, "argv", ["compiler"]):
                edited = variants[0] + "本地备注\n".encode()
                legacy.write_bytes(edited)
                self.assertEqual(main(), 1)
                self.assertEqual(legacy.read_bytes(), edited)
                legacy.write_bytes(variants[1])
                unknown = legacy.with_name("custom.yaml")
                unknown.write_bytes(variants[1])
                self.assertEqual(main(), 1)
                self.assertEqual(unknown.read_bytes(), variants[1])
                self.assertEqual(legacy.read_bytes(), variants[1])
                unknown.unlink()
                legacy.unlink()
                outside = root / legacy.name
                outside.write_bytes(variants[1])
                legacy.symlink_to(outside)
                self.assertEqual(main(), 1)
                self.assertTrue(legacy.is_symlink())
                legacy.unlink()
                legacy.write_bytes(variants[1])
                self.assertEqual(main(), 0)
                self.assertFalse(legacy.exists())
                self.assertEqual(outside.read_bytes(), variants[1])

    def test_installer_publishes_same_skill_to_default_and_project_directories(self):
        compiler = SCRIPTS / "compile-reference-dsl.py"
        with TemporaryDirectory() as directory:
            home = Path(directory).resolve()
            main = runpy.run_path(str(compiler))["main"]
            with patch.object(Path, "home", return_value=home), patch.object(
                sys, "argv", [str(compiler), "--install-skill"]
            ):
                self.assertEqual(main(), 0)
            target = home / ".agents" / "skills" / "token-io-decoupling"
            self.assertIn("\nname: token-io-decoupling\n", (target / "SKILL.md").read_text(encoding="utf-8"))
            self.assertTrue((target / "hooks" / "README.md").is_file())
            self.assertTrue((target / "references" / "README.md").is_file())
            old_reference_directory = Path("references/coding")
            self.assertFalse((target / old_reference_directory).exists())
            role_directory = Path("references/roles")
            roles = {
                role_directory / f"{name}.md"
                for name in (
                    "main-agent", "primary-output", "change-verification", "context-bootstrap-refresh",
                    "documentation-comments-git-operations",
                )
            }
            self.assertFalse((target / "agents").exists())
            self.assertFalse((target / "_project").exists())
            manifest = json.loads((target / MARKER).read_text(encoding="utf-8"))
            self.assertEqual(manifest["name"], "token-io-decoupling")
            self.assertTrue(all(path.endswith(".md") for path in manifest["files"]))
            self.assertTrue({role.as_posix() for role in roles}.issubset(manifest["files"]))
            expected_manifest = (target / MARKER).read_bytes()
            old_roles = {
                directory / role.name
                for directory in (old_reference_directory, old_reference_directory / "roles")
                for role in roles
            }
            with patch.object(Path, "home", return_value=home):
                old_outputs = {
                    Path("SKILL.md"): "旧版本\n",
                    Path("agents/worker.md"): "旧角色说明\n",
                    **{
                        role: f"<!-- 由 rules/{role.with_suffix('.yaml').as_posix()} 生成。请在 DSL 中维护正文。 -->\n"
                        for role in old_roles
                    },
                }
                self.assertEqual(update_local_skill(old_outputs), target)
                with patch.object(sys, "argv", [str(compiler), "--update-skill"]):
                    self.assertEqual(main(), 0)
            self.assertEqual((target / MARKER).read_bytes(), expected_manifest)
            self.assertFalse((target / "agents").exists())
            self.assertFalse((target / old_reference_directory).exists())
            project = home / "project"
            project.mkdir()
            (project / ".git").mkdir()
            with patch.object(Path, "home", return_value=home), patch.object(
                sys, "argv", [str(compiler), "--update-skill", "--project-root", str(project)]
            ):
                self.assertEqual(main(), 0)
            project_target = project / ".agents" / "skills" / DEFAULT_NAME
            self.assertEqual((project_target / MARKER).read_bytes(), (target / MARKER).read_bytes())
            linked_paths = set()
            for path in target.rglob("*.md"):
                markdown = path.read_text(encoding="utf-8")
                with self.subTest(path=path.relative_to(target)):
                    self.assertNotIn("请在 DSL 中维护正文。", markdown)
                for _, _, href in links_in_markdown(markdown):
                    url = urlsplit(href)
                    if url.scheme or url.netloc or not url.path:
                        continue
                    destination = (path.parent / unquote(url.path)).resolve()
                    with self.subTest(path=path.relative_to(target), href=href):
                        self.assertTrue(destination.is_relative_to(target))
                        self.assertTrue(destination.exists())
                        linked_paths.add(destination.relative_to(target))
            self.assertTrue(roles.issubset(linked_paths))

    def test_cli_installs_and_updates_named_skill_in_custom_directory(self):
        compiler = SCRIPTS / "compile-reference-dsl.py"
        main = runpy.run_path(str(compiler))["main"]
        with TemporaryDirectory() as directory:
            home = Path(directory).resolve()
            skills_dir = home / "custom skills"
            name = "custom-skill"
            target = skills_dir / name
            entry = target / "SKILL.md"
            install = [
                str(compiler), "--install-skill",
                "--skills-dir", relpath(skills_dir), "--name", name,
            ]
            with patch.object(Path, "home", return_value=home):
                with patch.object(sys, "argv", install):
                    self.assertEqual(main(), 0)
                installed_text = entry.read_text(encoding="utf-8")
                self.assertIn(f"name: {name}\n", installed_text)
                update_local_skill({Path("SKILL.md"): "旧版本\n"}, name, skills_dir=skills_dir)
                with patch.object(sys, "argv", install), patch.object(sys, "stderr"):
                    self.assertEqual(main(), 1)
                self.assertEqual(entry.read_text(encoding="utf-8"), "旧版本\n")
                update = [
                    str(compiler), "--update-skill", "--skills-dir", str(skills_dir), "--name", name,
                ]
                with patch.object(sys, "argv", update):
                    self.assertEqual(main(), 0)
                self.assertEqual(entry.read_text(encoding="utf-8"), installed_text)
            self.assertFalse((home / ".agents").exists())

    def test_updates_custom_installation_and_preserves_local_edits(self):
        with TemporaryDirectory() as directory:
            home = Path(directory).resolve()
            skills_dir = home / "custom-skills"
            target = skills_dir / DEFAULT_NAME
            shared_entry = home / ".agents" / "skills" / DEFAULT_NAME / "SKILL.md"
            shared_entry.parent.mkdir(parents=True)
            shared_entry.write_bytes(b"shared")
            target.mkdir(parents=True)
            entry = target / "SKILL.md"
            entry.write_bytes(b"old")
            (target / MARKER).write_text(
                json.dumps(
                    {
                        "format": 1,
                        "version": "0.1.0",
                        "name": DEFAULT_NAME,
                        "files": {"SKILL.md": hashlib.sha256(b"old").hexdigest()},
                    }
                ),
                encoding="utf-8",
            )
            outputs = {Path("SKILL.md"): "新指令\n"}
            with patch.object(Path, "home", return_value=home):
                self.assertEqual(update_local_skill(outputs, skills_dir=skills_dir), target)
                self.assertEqual(entry.read_text(encoding="utf-8"), "新指令\n")
                entry.write_text("本地修改", encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "本地修改"):
                    update_local_skill(outputs, skills_dir=skills_dir)
            self.assertEqual(entry.read_text(encoding="utf-8"), "本地修改")
            self.assertEqual(shared_entry.read_bytes(), b"shared")

    def test_installer_rejects_unsafe_directory_overrides(self):
        with TemporaryDirectory() as directory:
            home = Path(directory).resolve()
            project = home / "project"
            project.mkdir()
            alias = home / "project-alias"
            alias.symlink_to(project, target_is_directory=True)
            with patch.object(Path, "home", return_value=home):
                for project_root in (Path("relative"), home, alias):
                    with self.subTest(project_root=project_root), self.assertRaises(ValueError):
                        update_local_skill({}, project_root=project_root)
                for skills_dir in (alias, project / ".git" / "skills"):
                    with self.subTest(skills_dir=skills_dir), self.assertRaises(ValueError):
                        update_local_skill({}, skills_dir=skills_dir)
            self.assertFalse((home / ".agents").exists())
            self.assertFalse((project / ".agents").exists())

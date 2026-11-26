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
    def test_compiler_recognizes_generated_reference_replaced_by_split_rules(self):
        compiler = runpy.run_path(str(SCRIPTS / "compile-reference-dsl.py"))
        is_split_lsp_reference = compiler["is_split_lsp_reference"]
        with TemporaryDirectory() as temporary:
            skill = Path(temporary).resolve() / "skill"
            directory = skill / "references/coding/layer-01-fundamental-concepts/session-runtime"
            directory.mkdir(parents=True)
            legacy = directory / "LSP-MCP-Tools.md"
            original = compiler["SOURCE"] / legacy.relative_to(skill).with_suffix(".yaml")
            legacy.write_text(compiler["source_notice"](original) + "\n", encoding="utf-8")
            lsp = directory / "lsp-code-navigation.md"
            memory = directory / "project-memory.md"
            with patch.dict(is_split_lsp_reference.__globals__, {"SKILL": skill}):
                self.assertFalse(is_split_lsp_reference(legacy, {lsp: ""}))
                self.assertTrue(is_split_lsp_reference(legacy, {lsp: "", memory: ""}))
                legacy.write_text("本地记录\n", encoding="utf-8")
                self.assertFalse(is_split_lsp_reference(legacy, {lsp: "", memory: ""}))

    def test_installer_publishes_same_skill_to_both_preset_directories(self):
        compiler = SCRIPTS / "compile-reference-dsl.py"
        with TemporaryDirectory() as directory:
            home = Path(directory).resolve()
            main = runpy.run_path(str(compiler))["main"]
            with patch.object(Path, "home", return_value=home), patch.object(
                sys, "argv", [str(compiler), "--install-skill"]
            ):
                self.assertEqual(main(), 0)
            target = home / ".agents" / "skills" / "token-io-decoupling"
            self.assertFalse((home / ".pi").exists())
            self.assertIn("\nname: token-io-decoupling\n", (target / "SKILL.md").read_text(encoding="utf-8"))
            self.assertTrue((target / "hooks" / "README.md").is_file())
            self.assertFalse((target / "_project").exists())
            manifest = json.loads((target / MARKER).read_text(encoding="utf-8"))
            self.assertEqual(manifest["name"], "token-io-decoupling")
            with patch.object(Path, "home", return_value=home), patch.object(
                sys, "argv", [str(compiler), "--install-skill", "--host", "pi"]
            ):
                self.assertEqual(main(), 0)
            pi = home / ".pi" / "agent" / "skills" / DEFAULT_NAME
            self.assertEqual((pi / MARKER).read_bytes(), (target / MARKER).read_bytes())
            with patch.object(Path, "home", return_value=home):
                self.assertEqual(update_local_skill({Path("SKILL.md"): "旧版本\n"}), target)
                with patch.object(sys, "argv", [str(compiler), "--update-skill"]):
                    self.assertEqual(main(), 0)
            self.assertEqual((target / MARKER).read_bytes(), (pi / MARKER).read_bytes())
            project = home / "project"
            project.mkdir()
            (project / ".git").mkdir()
            with patch.object(Path, "home", return_value=home), patch.object(
                sys, "argv", [str(compiler), "--update-skill", "--host", "codex",
                              "--project-root", str(project)]
            ):
                self.assertEqual(main(), 0)
            codex = project / ".agents" / "skills" / DEFAULT_NAME
            self.assertEqual((codex / MARKER).read_bytes(), (target / MARKER).read_bytes())
            for path in target.rglob("*.md"):
                for _, _, href in links_in_markdown(path.read_text(encoding="utf-8")):
                    url = urlsplit(href)
                    if url.scheme or url.netloc or not url.path:
                        continue
                    destination = (path.parent / unquote(url.path)).resolve()
                    with self.subTest(path=path.relative_to(target), href=href):
                        self.assertTrue(destination.is_relative_to(target))
                        self.assertTrue(destination.exists())

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
                str(compiler), "--install-skill", "--host", "codex",
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
            self.assertFalse((home / ".pi").exists())

    def test_updates_pi_installation_and_preserves_local_edits(self):
        with TemporaryDirectory() as directory:
            home = Path(directory).resolve()
            target = home / ".pi" / "agent" / "skills" / DEFAULT_NAME
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
                self.assertEqual(update_local_skill(outputs, host="pi"), target)
                self.assertEqual(entry.read_text(encoding="utf-8"), "新指令\n")
                entry.write_text("本地修改", encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "本地修改"):
                    update_local_skill(outputs, host="pi")
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
                        update_local_skill({}, host="codex", project_root=project_root)
                for skills_dir in (alias, project / ".git" / "skills"):
                    with self.subTest(skills_dir=skills_dir), self.assertRaises(ValueError):
                        update_local_skill({}, skills_dir=skills_dir)
            self.assertFalse((home / ".agents").exists())
            self.assertFalse((project / ".agents").exists())

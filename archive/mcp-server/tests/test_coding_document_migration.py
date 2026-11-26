"""中文文档迁移清单、目录导航和章节结构回归。"""
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts/check_coding_document_migration.py"
SPEC = importlib.util.spec_from_file_location("coding_document_migration", SCRIPT)
assert SPEC and SPEC.loader
checker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checker)


class CodingDocumentMigrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        shutil.copytree(REPO / "docs", self.root / "docs")
        shutil.copytree(REPO / "skill", self.root / "skill")

    def test_repository_passes_with_no_mirrors(self):
        self.assertEqual(checker.validate(self.root), [])
        for directory in ("docs", "skill"):
            self.assertFalse(list((self.root / directory).rglob("*_zh_cn.md")))

    def test_missing_navigation_is_reported(self):
        for layer in checker.NAVIGATION_LAYERS:
            path = self.root / "skill/references/coding" / layer / "README.md"
            original = path.read_text()
            with self.subTest(layer=layer):
                path.unlink()
                self.assertTrue(checker.validate(self.root))
            path.write_text(original)

    def test_readme_requires_every_direct_owner_and_child(self):
        base = self.root / "skill/references/coding"
        for layer in checker.NAVIGATION_LAYERS:
            for path in (base / layer).rglob("README.md"):
                original = path.read_text()
                for target in checker.MARKDOWN_LINK.findall(original):
                    if not target.endswith(".md") or target.startswith("../"):
                        continue
                    with self.subTest(readme=path, target=target):
                        path.write_text(original.replace(f"]({target})", "](removed.md)"))
                        self.assertTrue(checker.validate(self.root))
                path.write_text(original)

    def test_invalid_duplicate_unsafe_and_missing_migration_targets_fail(self):
        path = self.root / checker.MAP
        original = path.read_text()
        for mode in ("duplicate", "unsafe", "missing", "renamed", "status", "reason"):
            data = json.loads(original)
            entry = next(item for item in data["document_moves"] if item.get("status", "active") == "active")
            if mode == "duplicate":
                data["document_moves"].append(dict(entry))
            elif mode == "unsafe":
                entry["to"] = "../escape.md"
            elif mode == "missing":
                entry["to"] = entry["to"].replace(".md", "-missing.md")
            elif mode == "renamed":
                entry["from"] = entry["from"].replace(".md", "-renamed.md")
            elif mode == "status":
                entry["status"] = "unknown"
            else:
                entry["status"] = "retired"
                entry["reason"] = ""
            with self.subTest(mode=mode):
                path.write_text(json.dumps(data, ensure_ascii=False))
                self.assertTrue(checker.validate(self.root))
        path.write_text(original)

    def test_layer_01_checker_imports_without_scripts_path(self):
        script = REPO / "scripts/check-layer-01-sections.py"
        result = subprocess.run([sys.executable, "-I", "-c", "import importlib.util,sys; s=importlib.util.spec_from_file_location('isolated',sys.argv[1]); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); assert callable(m.check_document)", str(script)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()

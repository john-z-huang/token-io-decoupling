"""Markdown 文档发现与本地链接验证。"""
import contextlib
import importlib.util
import io
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
from markdown_discovery import discover_markdown


def load(name):
    spec = importlib.util.spec_from_file_location(name, REPO / "scripts" / name)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


links = load("check-doc-layer-links.py")


class MarkdownDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.write("skill/SKILL.md", "---\nname: example\ndescription: 中文说明\n---\n# 中文指令\n")
        self.write("README.md", "# 中文说明\n[技能](skill/SKILL.md)\n")
        self.write("docs/WORKFLOW.md", "# 中文流程\n")

    def write(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def run_check(self, module):
        with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
            return module.main(self.root)

    def test_markdown_fixture_passes_local_link_check(self):
        self.assertEqual(self.run_check(links), 0)

    def test_generated_and_operational_noise_is_pruned(self):
        for folder in (".git", ".serena", ".venv", "node_modules", "build", "dist", "vendor", "__pycache__"):
            self.write(f"{folder}/noise.md", "English noise")
        self.write("archive/CHANGELOG/old.md", "English archived Markdown")
        self.write("AGENTS_NOT_USE_.md", "English inactive backup")
        self.write("AGENTS_zh_cn_NOT_USE_.md", "中文停用备份")
        names = {p.relative_to(self.root).as_posix() for p in discover_markdown(self.root)}
        self.assertEqual(names, {"README.md", "skill/SKILL.md", "docs/WORKFLOW.md"})

    def test_directory_and_markdown_symlinks_are_not_scanned(self):
        with tempfile.TemporaryDirectory() as external:
            source = Path(external) / "source.md"
            source.write_text("English noise")
            (self.root / "external").symlink_to(external, target_is_directory=True)
            (self.root / "external.md").symlink_to(source)
            self.assertEqual(len(discover_markdown(self.root)), 3)

    def test_nonstandard_virtual_environment_is_pruned(self):
        self.write("custom-env/pyvenv.cfg", "home = /example")
        self.write("custom-env/noise.md", "English noise")
        self.assertEqual(len(discover_markdown(self.root)), 3)

    def test_missing_local_target_fails(self):
        self.write("docs/WORKFLOW.md", "# 中文\n[丢失目标](missing.md)")
        self.assertEqual(self.run_check(links), 1)


if __name__ == "__main__":
    unittest.main()

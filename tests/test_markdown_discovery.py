"""Regression coverage for bounded maintained-Markdown discovery and scanners."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))


def load_script(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


discovery = load_script("markdown_discovery", "markdown_discovery.py")
multilingual = load_script("multilingual_docs_validator", "check-multilingual-docs.py")
layer_links = load_script("doc_layer_links_validator", "check-doc-layer-links.py")


class MarkdownDiscoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self._write("agents/openai.yaml", 'short_description: "English | 中文"\n')
        self._write("AGENTS.md", "Read MULTI_LINGUAL.md.\n")
        self._write("AGENTS_zh_cn.md", "Read MULTI_LINGUAL_zh_cn.md.\n")
        self._write("SKILL.md", "---\ntitle: fixture\n---\n\n[English](SKILL.md)\n")
        self._write("SKILL_zh_cn.md", "[简体中文](SKILL_zh_cn.md)\n")
        self._write("docs/index.md", "[English](index.md)\n")
        self._write("docs/zh-cn/index.md", "[简体中文](index.md)\n")

        pairs = [path.as_posix() for path in multilingual.PAIR_ROOTS]
        pairs.extend(path.as_posix() for path in multilingual.CORE_DOCS)
        for english in pairs:
            path = Path(english)
            title = path.stem.replace("_", " ")
            self._write(
                english,
                f"# {title}\n\n[English]({path.name}) | [简体中文]({path.stem}_zh_cn.md)\n",
            )
            self._write(
                path.with_name(f"{path.stem}_zh_cn.md").as_posix(),
                f"# {title}\n\n[English]({path.name}) | [简体中文]({path.stem}_zh_cn.md)\n",
            )

        self._write("AGENTS.md", "Read MULTI_LINGUAL.md.\n")
        self._write("AGENTS_zh_cn.md", "Read MULTI_LINGUAL_zh_cn.md.\n")
        self._write("SKILL.md", "---\ntitle: fixture\n---\n\n[English](SKILL.md)\n")

        self._write("mcp/custom-env/pyvenv.cfg", "home = /usr/bin\n")
        self._write("mcp/custom-env/Lib/noise.md", "generated\n")

        for core in multilingual.CORE_DOCS:
            content = (self.root / core).read_text(encoding="utf-8")
            self.assertNotIn("Codex", content)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _write(self, relative: str, content: str) -> Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def _run(self, module) -> tuple[int, str]:
        stdout, stderr = StringIO(), StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            result = module.main(self.root)
        return result, stdout.getvalue() + stderr.getvalue()

    def test_valid_authored_fixture_passes_both_scanners(self) -> None:
        self.assertEqual(self._run(multilingual)[0], 0)
        self.assertEqual(self._run(layer_links)[0], 0)

    def test_authored_mcp_document_missing_mirror_fails(self) -> None:
        (self.root / "mcp/DEVELOPMENT_zh_cn.md").unlink()
        result, output = self._run(multilingual)
        self.assertEqual(result, 1)
        self.assertIn("mcp/DEVELOPMENT_zh_cn.md", output)

    def test_cross_language_dependency_fails(self) -> None:
        self._write(
            "ENHANCED_ARCHITECTURE.md",
            "[English](ENHANCED_ARCHITECTURE.md) | [简体中文](mcp/DEVELOPMENT_zh_cn.md)\n",
        )
        result, output = self._run(multilingual)
        self.assertEqual(result, 1)
        self.assertIn("cross-language Markdown link", output)
        result, output = self._run(layer_links)
        self.assertEqual(result, 1)
        self.assertIn("cross-language dependency", output)

    def test_bad_local_target_fails_layer_link_validation(self) -> None:
        self._write("mcp/DEVELOPMENT.md", "[missing](missing-owner.md)\n")
        result, output = self._run(layer_links)
        self.assertEqual(result, 1)
        self.assertIn("missing local target", output)

    def test_generated_and_operational_noise_is_pruned_but_mcp_docs_remain(
        self,
    ) -> None:
        noise = [
            "mcp/.venv/lib/python/site-packages/noise.md",
            "mcp/.pytest_cache/noise.md",
            "mcp/__pycache__/noise.md",
            "mcp/dist/noise.md",
            "mcp/rule_sources/references/noise.md",
            "mcp/src/token_io_mcp/_resources/rules/noise.md",
            "mcp/custom-env/Lib/noise.md",
            ".serena/cache/noise.md",
            "vendor/package/noise.md",
        ]
        for path in noise:
            self._write(path, "sed: --: No such file or directory\n[bad](missing.md)\n")

        discovered = {
            path.relative_to(self.root).as_posix()
            for path in discovery.discover_markdown(self.root)
        }
        self.assertIn("mcp/DEVELOPMENT.md", discovered)
        self.assertIn("mcp/DEVELOPMENT_zh_cn.md", discovered)
        for path in noise:
            self.assertNotIn(path, discovered)
        self.assertEqual(self._run(multilingual)[0], 0)
        self.assertEqual(self._run(layer_links)[0], 0)

    def test_directory_symlink_is_not_traversed(self) -> None:
        outside = Path(self.tempdir.name).parent / f"{self.root.name}-outside"
        outside.mkdir()
        (outside / "foreign.md").write_text("foreign\n", encoding="utf-8")
        link = self.root / "mcp/linked-docs"
        link.parent.mkdir(parents=True, exist_ok=True)
        try:
            link.symlink_to(outside, target_is_directory=True)
        except OSError as exc:
            self.skipTest(f"directory symlinks are unavailable: {exc}")
        try:
            self.assertNotIn(link / "foreign.md", discovery.discover_markdown(self.root))
        finally:
            link.unlink()
            (outside / "foreign.md").unlink()
            outside.rmdir()

    def test_markdown_file_symlink_is_not_scanned(self) -> None:
        outside = Path(self.tempdir.name).parent / f"{self.root.name}-outside.md"
        outside.write_text("outside root\n", encoding="utf-8")
        link = self.root / "mcp/linked.md"
        link.parent.mkdir(parents=True, exist_ok=True)
        try:
            link.symlink_to(outside)
        except OSError as exc:
            outside.unlink()
            self.skipTest(f"file symlinks are unavailable: {exc}")
        try:
            self.assertNotIn(link, discovery.discover_markdown(self.root))
        finally:
            link.unlink()
            outside.unlink()


if __name__ == "__main__":
    unittest.main()

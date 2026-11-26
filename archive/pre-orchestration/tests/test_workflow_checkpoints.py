"""中文 Layer-03 语义和实际模块消费的回归检查。"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
SPEC = importlib.util.spec_from_file_location("workflow_checkpoints", REPO / "scripts/check-workflow-checkpoints.py")
assert SPEC and SPEC.loader
checker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checker)


class WorkflowCheckpointConsumptionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        shutil.copytree(REPO / "skill", self.root / "skill")
        self.original = checker.ROOT, checker.L3, checker.HOOKS
        checker.ROOT = self.root
        checker.L3 = self.root / "skill/references/coding/layer-03-workflow-checkpoints"
        checker.HOOKS = self.root / "skill/hooks"
        self.addCleanup(self.restore)

    def restore(self):
        checker.ROOT, checker.L3, checker.HOOKS = self.original

    def run_check(self):
        with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
            return checker.main()

    def test_chinese_repository_passes(self):
        self.assertEqual(self.run_check(), 0)

    def test_every_owner_is_required(self):
        for slug in checker.SLUGS:
            path = checker.L3 / f"{slug}.md"
            original = path.read_text()
            with self.subTest(owner=slug):
                path.unlink()
                self.assertEqual(self.run_check(), 1)
                path.write_text(original)

    def test_required_chinese_sections_cannot_be_removed(self):
        for slug in checker.SLUGS:
            path = checker.L3 / f"{slug}.md"
            original = path.read_text()
            for section in checker.SECTIONS["zh"]:
                if section not in original:
                    continue  # module-entry-resolution has an explicitly declared title alias.
                with self.subTest(owner=slug, section=section):
                    path.write_text(original.replace(section, "## 删除必需章节"))
                    self.assertEqual(self.run_check(), 1)
            path.write_text(original)

    def test_all_chinese_safety_clauses_are_required(self):
        for slug, languages in checker.OWNER_TERMS.items():
            path = checker.L3 / f"{slug}.md"
            original = path.read_text()
            for term in languages["zh"]:
                with self.subTest(owner=slug, term=term):
                    self.assertIn(term.casefold(), original.casefold())
                    path.write_text(re.sub(re.escape(term), "已移除安全条件", original, flags=re.I))
                    self.assertEqual(self.run_check(), 1)
            path.write_text(original)

    def test_owner_only_in_related_section_is_not_consumed(self):
        path = checker.HOOKS / "documentation.md"
        target = "../references/coding/layer-03-workflow-checkpoints/documentation-impact.md"
        text = path.read_text()
        path.write_text(text.replace(target, "missing.md") + f"\n[参考]({target})\n")
        self.assertEqual(self.run_check(), 1)

    def test_selector_requires_operational_route_entry_link(self):
        path = self.root / "skill/workflows/coding.md"
        path.write_text(path.read_text().replace("route-entry.md", "removed.md"))
        self.assertEqual(self.run_check(), 1)


if __name__ == "__main__":
    unittest.main()

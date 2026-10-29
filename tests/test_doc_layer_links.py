import importlib.util
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path, PurePosixPath


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/check-doc-layer-links.py"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("doc_layer_links", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class DocumentLayerNavigationTests(unittest.TestCase):
    def test_navigation_can_link_within_its_own_layer(self):
        self.assertTrue(MODULE.is_navigation_document(PurePosixPath("references/coding/layer-02-workflow-concepts/INDEX.md")))
        self.assertTrue(MODULE.allowed("layer-02", "layer-02", True))

    def test_navigation_cannot_link_to_a_higher_layer(self):
        self.assertFalse(MODULE.allowed("layer-02", "layer-03", True))

    def test_non_navigation_layer_two_owner_cannot_link_to_layer_two(self):
        self.assertFalse(MODULE.allowed("layer-02", "layer-02", False))

    def test_layer_two_owner_can_link_to_layer_one(self):
        self.assertTrue(MODULE.allowed("layer-02", "layer-01", False))

    def test_layer_three_cannot_link_up_to_layer_four(self):
        self.assertFalse(MODULE.allowed("layer-03", "layer-04", False))

    def test_layer_four_can_consume_layer_three(self):
        self.assertTrue(MODULE.allowed("layer-04", "layer-03", False))

    def test_top_routes_have_exact_module_allowlists(self):
        route = PurePosixPath("references/coding/layer-04-workflows/coding-single-agent.md")
        single = PurePosixPath("references/coding/layer-04-workflows/modules/single-execution.md")
        delegated = PurePosixPath("references/coding/layer-04-workflows/modules/delegated-execution.md")
        self.assertTrue(MODULE.allowed("layer-04-route", "layer-04-module", False, route, single))
        self.assertFalse(MODULE.allowed("layer-04-route", "layer-04-module", False, route, delegated))

    def test_nested_files_cannot_impersonate_route_or_module(self):
        nested_route = PurePosixPath("references/coding/layer-04-workflows/nested/coding-single-agent.md")
        nested_module = PurePosixPath("references/coding/layer-04-workflows/modules/nested/entry-readiness.md")
        self.assertFalse(MODULE.allowed("layer-04-route", "layer-04-module", False, nested_route, nested_module))

    def test_modules_cannot_link_to_sibling_or_route(self):
        module = PurePosixPath("references/coding/layer-04-workflows/modules/work-definition.md")
        sibling = PurePosixPath("references/coding/layer-04-workflows/modules/documentation.md")
        route = PurePosixPath("references/coding/layer-04-workflows/coding-single-agent.md")
        self.assertFalse(MODULE.allowed("layer-04-module", "layer-04-module", False, module, sibling))
        self.assertFalse(MODULE.allowed("layer-04-module", "layer-04-route", False, module, route))

    def test_layer_two_cannot_link_to_layer_three_or_four(self):
        self.assertFalse(MODULE.allowed("layer-02", "layer-03", False))
        self.assertFalse(MODULE.allowed("layer-02", "layer-04", False))

    def test_layer_three_owner_can_consume_layer_two(self):
        self.assertTrue(MODULE.allowed("layer-03", "layer-02", False))

    def _run_checker(self, files):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            for relative_path, content in files.items():
                path = root / relative_path
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
            errors = io.StringIO()
            with redirect_stderr(errors):
                result = MODULE.main(root)
            return result, errors.getvalue()

    def test_layer_three_route_coordinates_are_rejected_everywhere(self):
        cases = (
            (
                "references/coding/layer-03-workflow-checkpoints/entry.md",
                "prose\n在M06之后继续。",
                ("entry.md:2 -> M06",),
            ),
            (
                "references/coding/layer-03-workflow-checkpoints/entry.md",
                "S01/M01 and S02-S04",
                ("entry.md:1 -> S01", "entry.md:1 -> M01", "entry.md:1 -> S02", "entry.md:1 -> S04"),
            ),
            (
                "references/coding/layer-03-workflow-checkpoints/entry.md",
                "inline `M08` reference",
                ("entry.md:1 -> M08",),
            ),
            (
                "references/coding/layer-03-workflow-checkpoints/entry.md",
                "```text\nS09\n```",
                ("entry.md:2 -> S09",),
            ),
            (
                "references/coding/layer-03-workflow-checkpoints/README.md",
                "Navigation mentions M10",
                ("README.md:1 -> M10",),
            ),
            (
                "references/coding/layer-03-workflow-checkpoints/INDEX_zh_cn.md",
                "目录中出现 S11",
                ("INDEX_zh_cn.md:1 -> S11",),
            ),
            (
                "references/coding/layer-03-workflow-checkpoints/new/nested/unregistered-owner.md",
                "S12",
                ("new/nested/unregistered-owner.md:1 -> S12",),
            ),
        )
        for path, content, expected_diagnostics in cases:
            with self.subTest(path=path, content=content):
                result, diagnostics = self._run_checker({path: content})
                self.assertEqual(result, 1)
                for diagnostic in expected_diagnostics:
                    self.assertIn(diagnostic, diagnostics)

    def test_route_coordinates_are_allowed_in_layer_four(self):
        result, diagnostics = self._run_checker(
            {
                "references/coding/layer-04-workflows/coding-single-agent.md": (
                    "## Workflow map\n```mermaid\nS01 --> S02\n```\n"
                    "[Checkpoint](../layer-03-workflow-checkpoints/checkpoint.md)\n"
                ),
                "references/coding/layer-03-workflow-checkpoints/checkpoint.md": (
                    "This checkpoint returns verified evidence to its caller.\n"
                ),
            }
        )
        self.assertEqual(result, 0, diagnostics)
        self.assertEqual(diagnostics, "")

    def test_layer_three_rejects_module_checkpoint_coordinates(self):
        for content in ("ER01 is a route step.", "```text\nDE07\n```", "目录中的 SM03 checkpoint"):
            result, diagnostics = self._run_checker({
                "references/coding/layer-03-workflow-checkpoints/entry.md": content,
            })
            self.assertEqual(result, 1)
            self.assertIn("Layer-03 route coordinate dependency", diagnostics)

    def test_semantic_layer_three_text_and_valid_layer_two_link_pass(self):
        result, diagnostics = self._run_checker(
            {
                "references/coding/layer-03-workflow-checkpoints/checkpoint.md": (
                    "Use the current Decision evidence. See [Decision](../layer-02-workflow-concepts/decision.md).\n"
                    "S05x, longS06name, MS07, S008, and standard are not route coordinates.\n"
                ),
                "references/coding/layer-02-workflow-concepts/decision.md": "Decision checkpoint.\n",
            }
        )
        self.assertEqual(result, 0, diagnostics)
        self.assertEqual(diagnostics, "")

    def test_inline_code_pseudolinks_are_not_validated_as_documentation_links(self):
        for ticks in ("`", "``"):
            with self.subTest(ticks=ticks):
                pseudo = f"{ticks}[Missing](../layer-03-workflow-checkpoints/missing.md){ticks}"
                result, diagnostics = self._run_checker({
                    "references/coding/layer-02-workflow-concepts/source.md": pseudo,
                })
                self.assertEqual(result, 0, diagnostics)


if __name__ == "__main__":
    unittest.main()

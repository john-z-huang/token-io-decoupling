import importlib.util
import sys
import unittest
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

    def test_layer_two_cannot_link_to_layer_three_or_four(self):
        self.assertFalse(MODULE.allowed("layer-02", "layer-03", False))
        self.assertFalse(MODULE.allowed("layer-02", "layer-04", False))

    def test_layer_three_owner_can_consume_layer_two(self):
        self.assertTrue(MODULE.allowed("layer-03", "layer-02", False))


if __name__ == "__main__":
    unittest.main()

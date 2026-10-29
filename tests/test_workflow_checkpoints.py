"""Independent integration and mutation regressions for module-local L3 consumption."""
from __future__ import annotations

import importlib.util
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/check-workflow-checkpoints.py"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("workflow_checkpoints", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
ROOT = SCRIPT.parents[1]


class WorkflowCheckpointConsumptionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        for rel in ("references/coding/layer-03-workflow-checkpoints",
                    "references/coding/layer-04-workflows/modules", "workflows"):
            shutil.copytree(ROOT / rel, self.root / rel)
        self.original = (MODULE.ROOT, MODULE.L3, MODULE.MODULES)
        MODULE.ROOT = self.root
        MODULE.L3 = self.root / "references/coding/layer-03-workflow-checkpoints"
        MODULE.MODULES = self.root / "references/coding/layer-04-workflows/modules"

    def tearDown(self):
        MODULE.ROOT, MODULE.L3, MODULE.MODULES = self.original
        self.tmp.cleanup()

    def test_repository_has_real_consumption_for_all_l3_owners(self):
        self.assertEqual(MODULE.main(), 0)

    def test_link_only_in_related_concepts_does_not_count(self):
        path = MODULE.MODULES / "documentation.md"
        text = path.read_text(encoding="utf-8")
        target = "[Documentation Impact](../../layer-03-workflow-checkpoints/documentation-impact.md)"
        text = text.replace(target, "", 1)
        text += f"\n## Related concepts\n\n{target}\n"
        path.write_text(text, encoding="utf-8")
        self.assertEqual(MODULE.main(), 1)

    def test_wrong_directory_or_language_does_not_count(self):
        path = MODULE.MODULES / "documentation.md"
        text = path.read_text(encoding="utf-8").replace(
            "../../layer-03-workflow-checkpoints/documentation-impact.md",
            "../../layer-02-workflow-concepts/documentation-impact.md", 1)
        path.write_text(text, encoding="utf-8")
        self.assertEqual(MODULE.main(), 1)

    def test_missing_module_entry_resolution_consumer_fails(self):
        for name in ("entry-readiness.md", "entry-readiness_zh_cn.md"):
            path = MODULE.MODULES / name
            path.write_text(path.read_text(encoding="utf-8").replace(
                "../../layer-03-workflow-checkpoints/module-entry-resolution", "../../disabled/module-entry-resolution"))
        self.assertEqual(MODULE.main(), 1)

    def test_unconsumed_owner_fails_even_if_owner_exists(self):
        path = MODULE.MODULES / "documentation.md"
        path.write_text(path.read_text(encoding="utf-8").replace(
            "../../layer-03-workflow-checkpoints/documentation-impact.md", "../../other/documentation-impact.md", 1))
        zh = MODULE.MODULES / "documentation_zh_cn.md"
        zh.write_text(zh.read_text(encoding="utf-8").replace(
            "../../layer-03-workflow-checkpoints/documentation-impact_zh_cn.md", "../../other/documentation-impact_zh_cn.md", 1))
        self.assertEqual(MODULE.main(), 1)

    def test_advice_at_wrong_local_checkpoint_does_not_count(self):
        path = MODULE.MODULES / "work-definition.md"
        text = path.read_text(encoding="utf-8")
        link = "[Advisory Selection](../../layer-03-workflow-checkpoints/advisory-selection.md)"
        text = text.replace(link, "", 1)
        text = text.replace("**WD01 — Establish bounded current Context.",
                            "**WD01 — Establish bounded current Context. " + link, 1)
        path.write_text(text, encoding="utf-8")
        self.assertEqual(MODULE.main(), 1)

    def test_empty_required_layer_three_section_fails(self):
        path = MODULE.L3 / "route-entry.md"
        text = path.read_text(encoding="utf-8").replace(
            "## Trigger and inputs\n\n", "## Trigger and inputs\n\n## Decision and result\n\n", 1)
        path.write_text(text, encoding="utf-8")
        self.assertEqual(MODULE.main(), 1)

    def test_route_entry_requires_real_selector_link_in_entry_step(self):
        path = self.root / "workflows/coding.md"
        text = path.read_text(encoding="utf-8").replace(
            "[Route Entry](../references/coding/layer-03-workflow-checkpoints/route-entry.md)",
            "Route Entry", 1)
        path.write_text(text, encoding="utf-8")
        self.assertEqual(MODULE.main(), 1)

    def test_inline_code_owner_link_does_not_count_as_consumption(self):
        path = MODULE.MODULES / "documentation.md"
        text = path.read_text(encoding="utf-8")
        link = "[Documentation Impact](../../layer-03-workflow-checkpoints/documentation-impact.md)"
        self.assertIn(link, text)
        text = text.replace(link, f"`{link}`", 1)
        path.write_text(text, encoding="utf-8")
        self.assertEqual(MODULE.main(), 1)

    def test_inline_code_route_entry_link_does_not_count(self):
        path = self.root / "workflows/coding.md"
        text = path.read_text(encoding="utf-8")
        link = "[Route Entry](../references/coding/layer-03-workflow-checkpoints/route-entry.md)"
        self.assertIn(link, text)
        text = text.replace(link, f"``{link}``", 1)
        path.write_text(text, encoding="utf-8")
        self.assertEqual(MODULE.main(), 1)

    def test_audit_pending_timeout_and_no_reprompt_semantics_are_required(self):
        path = MODULE.L3 / "session-audit-resolution.md"
        path.write_text(path.read_text(encoding="utf-8").replace("never repeat the template", "repeat the template", 1))
        self.assertEqual(MODULE.main(), 1)

    def test_context_source_hash_and_freshness_semantics_are_required(self):
        path = MODULE.L3 / "context-source-selection.md"
        path.write_text(path.read_text(encoding="utf-8").replace("hash", "digest", 1))
        self.assertEqual(MODULE.main(), 1)

    def test_owner_safety_clause_in_related_section_or_fence_does_not_count(self):
        path = MODULE.L3 / "context-source-selection.md"
        original = path.read_text(encoding="utf-8")
        operation = "read every match for this task"
        self.assertIn(operation, original)
        related = original.replace(operation, "read all plan matches", 1) + f"\n- {operation}\n"
        fenced = original.replace(operation, "read all plan matches", 1)
        related_marker = "\n## Related concepts"
        self.assertIn(related_marker, fenced)
        fenced = fenced.replace(related_marker, f"\n```text\n{operation}\n```\n{related_marker}", 1)
        for relocated, text in (("Related concepts", related), ("fenced code", fenced)):
            with self.subTest(relocated=relocated):
                path.write_text(text, encoding="utf-8")
                self.assertEqual(MODULE.main(), 1)

    def test_session_canonical_authority_and_readback_safety_is_required(self):
        path = MODULE.L3 / "session-state-resolution.md"
        text = path.read_text(encoding="utf-8").replace(
            "An outage alone never changes authority", "An outage may change authority", 1)
        path.write_text(text, encoding="utf-8")
        self.assertEqual(MODULE.main(), 1)

    def test_active_plan_read_fail_closed_clause_is_required(self):
        path = MODULE.L3 / "context-source-selection.md"
        text = path.read_text(encoding="utf-8").replace(
            "read every match", "read one match", 1)
        path.write_text(text, encoding="utf-8")
        self.assertEqual(MODULE.main(), 1)

    def test_role_reservation_must_not_release_slice_or_create_child(self):
        path = MODULE.L3 / "role-reservation.md"
        text = path.read_text(encoding="utf-8").replace(
            "does not release a Slice", "releases a Slice", 1)
        path.write_text(text, encoding="utf-8")
        self.assertEqual(MODULE.main(), 1)

    def test_repair_handoff_and_epoch_reverification_require_current_fingerprint(self):
        path = MODULE.L3 / "repair-disposition.md"
        text = path.read_text(encoding="utf-8").replace(
            "new fingerprint", "old fingerprint", 1)
        path.write_text(text, encoding="utf-8")
        self.assertEqual(MODULE.main(), 1)

    def test_documentation_impact_must_preserve_before_after_epochs(self):
        path = MODULE.L3 / "documentation-impact.md"
        text = path.read_text(encoding="utf-8").replace(
            "before/after fingerprints", "after fingerprints", 1)
        path.write_text(text, encoding="utf-8")
        self.assertEqual(MODULE.main(), 1)


if __name__ == "__main__":
    unittest.main()

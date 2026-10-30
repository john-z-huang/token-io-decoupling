"""Independent literal mutation tests and repository integration for route/module maps."""
from __future__ import annotations

import importlib.util
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/check-layer-04-workflow-maps.py"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("workflow_map_validator", SCRIPT)
assert SPEC and SPEC.loader
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)
REPO = SCRIPT.parents[1]
ROUTES = REPO / "docs/skill/references/coding/layer-04-workflows"


class WorkflowMapMigrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        for rel in ("docs/skill/references/coding/layer-03-workflow-checkpoints",
                    "docs/skill/references/coding/layer-04-workflows", "AGENTS.md", "AGENTS_zh_cn.md",
                    ".github/workflows/multilingual-docs.yml", "docs/workflow-module-migration.json"):
            source = REPO / rel
            target = self.root / rel
            if source.is_dir():
                shutil.copytree(source, target)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)

    def tearDown(self):
        self.tmp.cleanup()

    def read(self, rel):
        return (self.root / rel).read_text(encoding="utf-8")

    def mutate(self, rel, old, new):
        path = self.root / rel
        text = path.read_text(encoding="utf-8")
        self.assertIn(old, text)
        path.write_text(text.replace(old, new, 1), encoding="utf-8")

    def assert_rejected(self):
        self.assertTrue(validator.check_repository(self.root))

    def test_real_repository_routes_and_all_eight_module_maps_pass(self):
        self.assertEqual(validator.check_repository(REPO), [])

    def test_complete_single_and_multi_route_order_is_required(self):
        self.mutate("docs/skill/references/coding/layer-04-workflows/coding-single-agent.md",
                    "2. **SM02 — Session readiness.", "2. **SM03 — Session readiness.")
        self.assert_rejected()

    def test_extra_route_checkpoint_is_reported_without_index_error(self):
        self.mutate("docs/skill/references/coding/layer-04-workflows/coding-single-agent.md",
                    "7. **SM07 — Delivery and acceptance.",
                    "7. **SM07 — Delivery and acceptance.\n8. **SM08 — Unexpected checkpoint.")
        errors = validator.check_repository(self.root)
        self.assertTrue(any("exactly ordered checkpoints" in error for error in errors))
        self.assertFalse(any("IndexError" in error for error in errors))

    def test_route_must_call_exact_module_in_same_language(self):
        self.mutate("docs/skill/references/coding/layer-04-workflows/coding-single-agent.md",
                    "modules/single-execution.md", "modules/delegated-execution.md")
        self.assert_rejected()

    def test_single_agent_cannot_gain_delegated_execution_checkpoint(self):
        self.mutate("docs/skill/references/coding/layer-04-workflows/coding-single-agent.md",
                    'SM04["SM04 Single-Agent execution"]', 'DE04["DE04 delegated execution"]')
        self.assert_rejected()

    def test_route_shortcut_around_verification_is_rejected(self):
        self.mutate("docs/skill/references/coding/layer-04-workflows/coding-single-agent.md",
                    "SM04 -- current implementation result and provisional evidence --> SM05",
                    "SM04 -- current implementation result and provisional evidence --> SM07")
        self.assert_rejected()

    def test_route_entry_returns_to_recorded_caller_not_first_module(self):
        self.mutate("docs/skill/references/coding/layer-04-workflows/coding-single-agent.md",
                    "resume original suspended caller --> RESUME", "resume original suspended caller --> SM01")
        self.assert_rejected()

    def test_resume_requires_guarded_recorded_target_and_conflict_block(self):
        self.mutate("docs/skill/references/coding/layer-04-workflows/coding-multi-agent.md",
                    "recorded caller is MM07", "any caller may select MM07")
        self.assert_rejected()

    def test_module_checkpoint_must_exist_in_both_map_and_numbered_list(self):
        self.mutate("docs/skill/references/coding/layer-04-workflows/modules/documentation.md",
                    'DOC04["DOC04 Classify post-write impact and advance affected epochs"]',
                    'DOC99["DOC99 Classify post-write impact and advance affected epochs"]')
        self.assert_rejected()

    def test_module_map_cannot_have_unreachable_orphan(self):
        self.mutate("docs/skill/references/coding/layer-04-workflows/modules/work-definition.md",
                    'WD03["WD03 Resolve default shared task plan"]',
                    'WD03["WD03 Resolve default shared task plan"]\n    ORPHAN["orphan"]')
        self.assert_rejected()

    def test_fixed_module_contract_rejects_deleted_control_coverage_edge(self):
        self.mutate("docs/skill/references/coding/layer-04-workflows/modules/single-execution.md",
                    "prior Continue covers Slice; boundary and epochs current --> D_REROUTE",
                    "prior Continue covers Slice; boundary and epochs current --> SE05")
        self.assert_rejected()

    def test_fixed_module_contract_rejects_deleted_memory_readback_order_edge(self):
        self.mutate("docs/skill/references/coding/layer-04-workflows/modules/documentation.md",
                    "DOC03 -- write succeeded and readback confirmed --> DOC04",
                    "DOC03 -- write succeeded and readback confirmed --> DOC05")
        self.assert_rejected()

    def test_plan_persistence_failure_cannot_continue_execution(self):
        for module, checkpoint, block in (
            ("single-execution", "SE02", "SE_BLOCK"),
            ("delegated-execution", "DE04", "DE_BLOCK"),
        ):
            for suffix, label in (
                ("", "required plan access or update failed"),
                ("_zh_cn", "必需计划访问或更新失败"),
            ):
                with self.subTest(module=module, language=suffix):
                    rel = f"docs/skill/references/coding/layer-04-workflows/modules/{module}{suffix}.md"
                    path = self.root / rel
                    original = path.read_text(encoding="utf-8")
                    self.mutate(rel, f"{checkpoint} -- {label} --> {block}",
                                f"{checkpoint} -- {label} --> D_GATE")
                    self.assert_rejected()
                    path.write_text(original, encoding="utf-8")

    def test_plan_default_cannot_revert_to_optional_planning_intent(self):
        for suffix, current, old in (
            ("", "Persistence explicitly prohibited?", "Planning intent present?"),
            ("_zh_cn", "明确禁止持久化？", "存在规划意图？"),
        ):
            with self.subTest(language=suffix):
                rel = f"docs/skill/references/coding/layer-04-workflows/modules/work-definition{suffix}.md"
                path = self.root / rel
                original = path.read_text(encoding="utf-8")
                self.mutate(rel, current, old)
                self.assert_rejected()
                path.write_text(original, encoding="utf-8")

    def test_plan_restriction_cannot_skip_explicit_persistence_conflict(self):
        rel = "docs/skill/references/coding/layer-04-workflows/modules/work-definition.md"
        self.mutate(rel,
                    "D_PLAN -- explicit persistence requirement conflicts --> WD_BLOCK",
                    "D_PLAN -- explicit persistence requirement conflicts --> WD_PLAN_NA")
        self.assert_rejected()

    def test_completed_plan_cannot_skip_final_update_before_archive(self):
        self.mutate("docs/skill/references/coding/layer-04-workflows/modules/delivery-acceptance.md",
                    "DA04 Preserve full plan; append final evidence; verify lossless archive",
                    "DA04 Archive matching plan and read back")
        self.assert_rejected()

    def test_completion_cannot_replace_history_with_summary(self):
        self.mutate("docs/skill/references/coding/layer-04-workflows/modules/delivery-acceptance.md",
                    "a final summary cannot replace accumulated records",
                    "a final summary may replace accumulated records")
        self.assert_rejected()

    def test_archive_requires_identical_content_not_just_final_status(self):
        self.mutate("docs/skill/references/coding/layer-04-workflows/modules/delivery-acceptance.md",
                    "content identical to the verified final active baseline",
                    "a completed final status")
        self.assert_rejected()

    def test_bilingual_archive_map_cannot_weaken_preservation(self):
        for suffix, old, new in (
            ("", "preservation passed; archive equals final active content", "archive contains a summary"),
            ("_zh_cn", "内容保留通过；归档等于最终活动内容", "归档包含摘要"),
        ):
            rel = f"docs/skill/references/coding/layer-04-workflows/modules/delivery-acceptance{suffix}.md"
            with self.subTest(language=suffix):
                original = self.read(rel)
                self.mutate(rel, old, new)
                self.assert_rejected()
                (self.root / rel).write_text(original, encoding="utf-8")

    def test_missing_required_plan_cannot_take_archive_exception(self):
        self.mutate("docs/skill/references/coding/layer-04-workflows/modules/delivery-acceptance.md",
                    "D_PLAN -- required plan missing or inaccessible --> DA_NEEDS_PLAN",
                    "D_PLAN -- required plan missing or inaccessible --> DA_PLAN_NA")
        self.assert_rejected()

    def test_archive_exception_requires_documented_persistence_restriction(self):
        self.mutate("docs/skill/references/coding/layer-04-workflows/modules/delivery-acceptance.md",
                    "D_PLAN -- no active plan; documented persistence restriction --> DA_PLAN_NA",
                    "D_PLAN -- no active plan --> DA_PLAN_NA")
        self.assert_rejected()

    def test_fixed_module_contract_rejects_archive_before_all_criteria_edge(self):
        self.mutate("docs/skill/references/coding/layer-04-workflows/modules/delivery-acceptance.md",
                    "DA03 -- all criteria mapped; every applicable item passes on current epochs --> D_PLAN",
                    "DA02 -- exact target and staged/committed fingerprint match; effect result confirmed --> D_PLAN")
        self.assert_rejected()

    def test_fixed_module_contract_rejects_weakened_control_coverage_label(self):
        self.mutate("docs/skill/references/coding/layer-04-workflows/modules/single-execution.md",
                    "prior Continue still cover this bounded Slice",
                    "prior Continue may cover this bounded Slice")
        self.assert_rejected()

    def test_repository_scope_map_labels_are_required_in_both_languages(self):
        cases = (
            (
                "docs/skill/references/coding/layer-04-workflows/modules/work-definition.md",
                "verify repository scope",
                "verify storage scope",
            ),
            (
                "docs/skill/references/coding/layer-04-workflows/modules/work-definition_zh_cn.md",
                "核验仓库存储范围",
                "核验存储范围",
            ),
            (
                "docs/skill/references/coding/layer-04-workflows/modules/delivery-acceptance.md",
                "same repository scope",
                "matching scope",
            ),
            (
                "docs/skill/references/coding/layer-04-workflows/modules/delivery-acceptance_zh_cn.md",
                "同一仓库存储范围",
                "对应存储范围",
            ),
        )
        for rel, old, new in cases:
            with self.subTest(path=rel):
                original = self.read(rel)
                self.mutate(rel, old, new)
                errors = validator.check_repository(self.root)
                self.assertTrue(
                    any("is missing required safety label" in error for error in errors),
                    errors,
                )
                (self.root / rel).write_text(original, encoding="utf-8")

    def test_repository_scope_semantics_are_required_with_unchanged_maps(self):
        cases = (
            (
                "docs/skill/references/coding/layer-04-workflows/modules/work-definition.md",
                "selected storage scope, repository identity and paired active/archive namespaces",
                "selected storage scope and paired active/archive namespaces",
            ),
            (
                "docs/skill/references/coding/layer-04-workflows/modules/delivery-acceptance.md",
                "same verified repository storage scope",
                "same verified workspace storage scope",
            ),
        )
        for rel, old, new in cases:
            with self.subTest(path=rel):
                original = self.read(rel)
                self.mutate(rel, old, new)
                errors = validator.check_repository(self.root)
                self.assertTrue(
                    any("module lost required semantic contract" in error for error in errors),
                    errors,
                )
                (self.root / rel).write_text(original, encoding="utf-8")

    def test_auxiliary_bootstrap_must_resume_original_task_at_de01(self):
        self.mutate("docs/skill/references/coding/layer-04-workflows/modules/delegated-execution.md",
                    "after the auxiliary task completes, return to DE01",
                    "after the auxiliary task completes, continue to DE02")
        self.assert_rejected()

    def test_amend_requires_current_contract_decision_and_context_before_continue(self):
        self.mutate("docs/skill/references/coding/layer-04-workflows/modules/single-execution.md",
                    "Contract/Decision and needed Context current --> SE05",
                    "scope is ready --> SE05")
        errors = validator.check_repository(self.root)
        self.assertTrue(any("SE_NEEDS_AMEND -> SE05" in error for error in errors))

    def test_manifest_requires_declared_owner_at_its_actual_checkpoint(self):
        import json
        path = self.root / "docs/workflow-module-migration.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        entry = data["routes"]["single-agent"]["steps"][0]["targets"][0]
        entry["owner_refs"] = ["enhanced-path-selection"]
        path.write_text(json.dumps(data), encoding="utf-8")
        self.assert_rejected()

    def test_bilingual_module_graph_topology_must_match(self):
        self.mutate("docs/skill/references/coding/layer-04-workflows/modules/documentation_zh_cn.md",
                    "DOC05 -- 适用检查通过；未受影响维度有依据 --> DOC06", "DOC05 --> DOC_BLOCK")
        self.assert_rejected()

    def test_entry_map_must_keep_needs_and_block_outcomes(self):
        self.mutate("docs/skill/references/coding/layer-04-workflows/modules/entry-readiness.md",
                    "ER00 --> D_ENTRY", "ER00 --> ER01")
        self.assert_rejected()

    def test_ci_trigger_and_commands_are_required(self):
        self.mutate(".github/workflows/multilingual-docs.yml",
                    "run: python3 scripts/check-layer-04-workflow-maps.py", "run: true")
        self.assert_rejected()

    def test_manifest_covers_all_30_legacy_steps_and_preserves_split_hybrids(self):
        import json
        data = json.loads((self.root / "docs/workflow-module-migration.json").read_text(encoding="utf-8"))
        self.assertEqual([item["source_step"] for item in data["routes"]["single-agent"]["steps"]],
                         [f"S{i:02d}" for i in range(1, 15)])
        self.assertEqual([item["source_step"] for item in data["routes"]["multi-agent"]["steps"]],
                         [f"M{i:02d}" for i in range(1, 17)])
        self.assertEqual(len(data["routes"]["single-agent"]["steps"][5]["targets"]), 2)
        self.assertEqual(len(data["routes"]["multi-agent"]["steps"][6]["targets"]), 2)

    def test_manifest_rejects_missing_legacy_mapping_and_wrong_local_checkpoint(self):
        import json
        path = self.root / "docs/workflow-module-migration.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["routes"]["single-agent"]["steps"].pop(5)
        path.write_text(json.dumps(data), encoding="utf-8")
        self.assert_rejected()

    def test_manifest_rejects_deleted_critical_semantic_substep(self):
        import json
        path = self.root / "docs/workflow-module-migration.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["routes"]["multi-agent"]["steps"][6]["semantic_substeps"].pop(1)
        path.write_text(json.dumps(data), encoding="utf-8")
        self.assert_rejected()

    def test_manifest_rejects_mixed_multi_step_reordered_calls(self):
        import json
        path = self.root / "docs/workflow-module-migration.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["routes"]["multi-agent"]["steps"][6]["targets"].reverse()
        path.write_text(json.dumps(data), encoding="utf-8")
        errors = validator.check_repository(self.root)
        self.assertTrue(any("fixed mixed-step checkpoint call order/targets" in error for error in errors))
        data["routes"]["single-agent"]["steps"].insert(5, json.loads((REPO / "docs/workflow-module-migration.json").read_text(encoding="utf-8"))["routes"]["single-agent"]["steps"][5])
        data["routes"]["single-agent"]["steps"][0]["targets"][0]["checkpoints"] = ["ER99"]
        path.write_text(json.dumps(data), encoding="utf-8")
        self.assert_rejected()

    def test_manifest_owner_link_only_in_related_section_does_not_count(self):
        path = self.root / "docs/skill/references/coding/layer-04-workflows/modules/documentation.md"
        text = path.read_text(encoding="utf-8")
        direct = "../../layer-03-workflow-checkpoints/documentation-impact.md"
        self.assertIn(direct, text)
        path.write_text(text.replace(direct, "../../missing/documentation-impact.md", 1), encoding="utf-8")
        self.assert_rejected()

    def test_transitive_owner_link_only_in_related_section_does_not_count(self):
        path = self.root / "docs/skill/references/coding/layer-03-workflow-checkpoints/session-state-resolution.md"
        text = path.read_text(encoding="utf-8")
        target = "[Session Model](../layer-01-fundamental-concepts/session-runtime/session-model.md)"
        self.assertIn(target, text)
        text = text.replace(target, "", 1) + f"\n## Related concepts\n\n- {target}\n"
        path.write_text(text, encoding="utf-8")
        errors = validator.check_repository(self.root)
        self.assertTrue(any("transitive en owner session-state-resolution lacks its fixed owner call" in error for error in errors))

    def test_inline_code_l3_link_does_not_count_as_manifest_consumption(self):
        path = self.root / "docs/skill/references/coding/layer-04-workflows/modules/session-readiness.md"
        text = path.read_text(encoding="utf-8")
        link = "[Session State Resolution](../../layer-03-workflow-checkpoints/session-state-resolution.md)"
        self.assertIn(link, text)
        text = text.replace(f"Apply {link}", f"Apply ``{link}``", 1)
        path.write_text(text, encoding="utf-8")
        errors = validator.check_repository(self.root)
        self.assertTrue(any("owner session-state-resolution is not linked from its designated numbered checkpoint" in error for error in errors))

    def test_empty_owner_refs_require_fixed_exact_l1_l2_markdown_target(self):
        path = self.root / "docs/skill/references/coding/layer-04-workflows/modules/delivery-acceptance.md"
        text = path.read_text(encoding="utf-8")
        target = "../../layer-02-workflow-concepts/completion-and-effects/git.md"
        self.assertIn(target, text)
        text = text.replace(target, "../../layer-02-workflow-concepts/git.md", 1)
        path.write_text(text, encoding="utf-8")
        errors = validator.check_repository(self.root)
        self.assertTrue(any("lacks exact direct owner link" in error for error in errors))

    def test_control_and_auxiliary_bootstrap_contracts_remain_distinct(self):
        single = (ROUTES / "modules/single-execution.md").read_text(encoding="utf-8")
        delegated = (ROUTES / "modules/delegated-execution.md").read_text(encoding="utf-8")
        self.assertIn("next Slice", single)
        self.assertIn("return to DE01", delegated)
        self.assertIn("separately authorize and assess the original task", delegated)
        self.assertIn("write_content_memo: true` or `false", delegated)
        self.assertIn("pending child result returns `needs_prerequisite` and resumes at DE07", delegated)

    def test_memory_is_read_back_before_impact_and_archive_follows_all_criteria(self):
        docs = (ROUTES / "modules/documentation.md").read_text(encoding="utf-8")
        self.assertLess(docs.index("DOC03 -- write succeeded and readback confirmed --> DOC04"),
                        docs.index("DOC04 -- only documentation dimension changed"))
        da = (ROUTES / "modules/delivery-acceptance.md").read_text(encoding="utf-8")
        self.assertIn("DA03 -- all criteria mapped; every applicable item passes on current epochs --> D_PLAN", da)
        self.assertIn("DA04 -- preservation, update, archive or readback failed --> DA_BLOCK", da)

    def test_route_change_return_and_effect_epoch_rules_are_explicit(self):
        for name in ("coding-single-agent.md", "coding-multi-agent.md"):
            text = (ROUTES / name).read_text(encoding="utf-8")
            self.assertIn("resume original suspended caller", text)
            self.assertIn("epoch/effect checks pass", text)
            self.assertIn("caller record missing or conflicts", text)


if __name__ == "__main__":
    unittest.main()

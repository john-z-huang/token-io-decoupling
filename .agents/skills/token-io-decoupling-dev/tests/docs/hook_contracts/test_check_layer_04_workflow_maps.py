"""验证四层来源整合、目标锚点与两种精简 workflow。"""

from __future__ import annotations

import json
import unittest

from .fixtures import ROOT, SKILL, SOURCE_MAP, HookFixture


class WorkflowSourceConsolidationTests(HookFixture):
    """通过真实检查 CLI 变异来源映射，保护历史可追溯性与当前精简入口的边界。"""

    def test_reviewed_source_map_covers_all_files_and_topics(self):
        """真实清单需通过 CLI，且完整保留 218 份来源与 1031 个历史主题。"""
        mapping = json.loads((ROOT / SOURCE_MAP).read_text())
        self.assertEqual(self.run_check(ROOT).returncode, 0)
        self.assertEqual(len(mapping["sources"]), 218)
        self.assertEqual(sum(len(item["topics"]) for item in mapping["sources"]), 1031)

    def test_every_source_requires_replacement_and_fingerprint(self):
        """替代目标与历史指纹各自必需，缺任一项都不能宣称来源已整合。"""
        self.change_mapping(lambda item: item["sources"][0].update(target_refs=[]))
        self.assert_rejected("missing replacement")
        self.change_mapping(lambda item: item["sources"][0].update(baseline_sha256="unknown"))
        self.assert_rejected("missing baseline fingerprint")

    def test_removing_a_source_or_scope_is_rejected(self):
        """删除来源记录或缩小四目录历史范围都应失败，不能借范围变化绕过完整性。"""
        self.change_mapping(lambda item: item["sources"].pop())
        self.assert_rejected("218 baseline source files")
        self.change_mapping(lambda item: item["baseline_scope"].pop())
        self.assert_rejected("four-directory baseline scope")

    def test_duplicate_source_and_wrong_language_are_rejected(self):
        """重复来源和错标历史语言分别失败，避免数量看似正确而实际身份已被覆盖。"""
        self.change_mapping(lambda item: item["sources"].__setitem__(1, dict(item["sources"][0])))
        self.assert_rejected("duplicate source")
        self.change_mapping(lambda item: item["sources"][0].update(language="zh_cn"))
        self.assert_rejected("wrong source language")

    def test_missing_source_topic_is_rejected(self):
        """删除单个主题仍保留文件记录也应失败，逐文件覆盖不能替代逐主题追溯。"""

        def remove_topic(mapping):
            next(item for item in mapping["sources"] if item["topics"])["topics"].pop()

        self.change_mapping(remove_topic)
        self.assert_rejected("1031 baseline topics")

    def test_a_source_without_headings_may_keep_document_level_targets(self):
        """原本没有标题的来源允许只映射整篇文档，不凭空发明历史主题来满足检查。"""
        mapping = json.loads(self.read(SOURCE_MAP))
        without_topics = [item for item in mapping["sources"] if not item["topics"]]
        self.assertTrue(without_topics)
        self.assertTrue(all(item["target_refs"] for item in without_topics))
        self.assertEqual(self.run_check().returncode, 0)

    def test_missing_topic_mapping_is_rejected(self):
        """即使文档已有替代入口，单个主题缺失目标也应作为未解决迁移报告。"""

        def remove_targets(mapping):
            next(item for item in mapping["sources"] if item["topics"])["topics"][0][
                "target_refs"
            ] = []

        self.change_mapping(remove_targets)
        self.assert_rejected("unresolved topic replacement")

    def test_canonical_topic_target_can_be_more_precise_than_document_target(self):
        """主题目标可以比文档目标更精确，证明检查未错误要求两级映射完全相同。"""
        mapping = json.loads(self.read(SOURCE_MAP))
        self.assertTrue(
            any(
                set(topic["target_refs"]) - set(source["target_refs"])
                for source in mapping["sources"]
                for topic in source["topics"]
            )
        )
        self.assertEqual(self.run_check().returncode, 0)

    def test_mapping_reference_cannot_escape_source_root(self):
        """替代引用中的父目录逃逸必须被拒绝，防止把仓库外文件当当前 Hook。"""
        self.change_mapping(
            lambda item: item["sources"][0].update(target_refs=["../../outside.md"])
        )
        self.assert_rejected("unsafe replacement reference")

    def test_missing_current_target_anchor_and_document_are_rejected(self):
        """先破坏真实标题再删除当前文档，两种故障都必须阻止来源检查通过。"""
        self.change_mapping(
            lambda item: item["sources"][0].update(
                target_refs=["references/coding/hooks/shared.md#not-a-real-anchor"]
            )
        )
        self.assert_rejected("replacement anchor does not exist")
        (self.root / SKILL / "references/coding/hooks/shared.md").unlink()
        self.assert_rejected("cannot read required document")

    def test_deleted_placeholders_are_not_required_as_current_documents(self):
        """109 个占位文件已经退役；它们应保持缺失，而真实 Hook 替代关系仍可完整验证。"""
        mapping = json.loads(self.read(SOURCE_MAP))
        retired = {source["retired_path"] for source in mapping["sources"]}
        self.assertEqual(len(retired), 109)
        self.assertTrue(all(not (self.root / SKILL / path).exists() for path in retired))
        self.assertEqual(self.run_check().returncode, 0)

    def test_reintroducing_even_an_empty_retired_directory_is_rejected(self):
        """重新建立空旧目录也应失败，避免占位结构再次被误当成当前政策入口。"""
        mapping = json.loads(self.read(SOURCE_MAP))
        (self.root / SKILL / mapping["baseline_scope"][0]).mkdir(parents=True)
        self.assert_rejected("retired source directories must not exist")

    def test_symlink_replacements_and_retired_directories_are_rejected(self):
        """当前 Hook 的符号链接替换与退役目录的断链复活都不能绕过路径守卫。"""
        shared = self.root / SKILL / "references/coding/hooks/shared.md"
        shared.unlink()
        shared.symlink_to(self.root / SKILL / "SKILL.md")
        self.assert_rejected("symlink replacement reference")
        mapping = json.loads(self.read(SOURCE_MAP))
        retired = self.root / SKILL / mapping["baseline_scope"][0]
        retired.parent.mkdir(parents=True, exist_ok=True)
        retired.symlink_to(self.root / "not-present", target_is_directory=True)
        self.assert_rejected("retired source directories must not exist")

    def test_valid_looking_rewrites_of_reviewed_history_are_rejected(self):
        """替换为格式合法的 SHA 仍应失败，证明指纹检查保护已审核事实而非仅校验格式。"""
        self.change_mapping(lambda item: item["sources"][0].update(baseline_sha256="a" * 64))
        self.assert_rejected("reviewed baseline records were changed")

    def test_replacing_a_topic_without_changing_the_count_is_rejected(self):
        """同数量改名历史主题也应失败，保护主题身份而非只依赖 1031 的计数。"""

        def replace_topic(mapping):
            source = next(item for item in mapping["sources"] if item["topics"])
            source["topics"][0]["heading"] = "A different historical topic"

        self.change_mapping(replace_topic)
        self.assert_rejected("reviewed baseline records were changed")

    def test_retired_evidence_and_entry_baselines_cannot_be_rewritten(self):
        """退役卡片证据和六入口基线各自不可重写，避免虚构删除事实或缩短比例。"""
        self.change_mapping(lambda item: item["sources"][0].update(retired_sha256="b" * 64))
        self.assert_rejected("reviewed retirement evidence was changed")
        self.change_mapping(lambda item: item["entry_baselines"][0].update(baseline_bytes=1))
        self.assert_rejected("reviewed entry baseline records were changed")

    def test_counts_require_integers_and_targets_must_be_current_hooks(self):
        """计数不能靠浮点值蒙混通过，当前入口也不能代替应明确指向的 Hook 文档。"""
        self.change_mapping(lambda item: item.update(source_count=218.0))
        self.assert_rejected("reviewed baseline identity or count: source_count")
        self.change_mapping(lambda item: item["sources"][0].update(target_refs=["SKILL.md"]))
        self.assert_rejected("unsafe replacement reference")

    def test_reviewed_baseline_identity_cannot_be_silently_replaced(self):
        """固定历史提交 ID 是来源口径的一部分，不能只保留文件数量却换成其它历史。"""
        self.change_mapping(lambda item: item.update(baseline_commit="0" * 40))
        self.assert_rejected("reviewed baseline identity")

    def test_short_workflows_keep_all_six_current_event_links(self):
        """删除精简 workflow 的一个当前事件链接也应失败，精简不意味着丢失事件可达性。"""
        relative = SKILL / "references/coding/layer-04-workflows/coding-single-agent.md"
        self.mutate(relative, "../hooks/completion-requested.md", "../hooks/missing-completion.md")
        self.assert_rejected("missing current event instruction: completion_requested")

    def test_both_entries_and_workflows_are_substantially_shorter(self):
        """使用三份历史中文基线比较当前入口，避免把旧英文长度混作缩短依据。"""
        mapping = json.loads(self.read(SOURCE_MAP))
        self.assertEqual(self.run_check().returncode, 0)
        self.assertEqual(len(mapping["entry_baselines"]), 6)
        chinese = [
            entry for entry in mapping["entry_baselines"] if entry["path"].endswith("_zh_cn.md")
        ]
        self.assertEqual(len(chinese), 3)
        for entry in chinese:
            self.assertLess(
                len(self.read(SKILL / entry["canonical_path"])) * 2, entry["baseline_characters"]
            )

    def test_hiding_old_policy_in_default_workflow_is_rejected(self):
        """把大量重复政策塞回短 workflow 应失败，确保业务判断继续集中在 Hook 文档。"""
        relative = SKILL / "references/coding/layer-04-workflows/coding-multi-agent.md"
        self.write(relative, self.read(relative) + "\n" + "Unnecessary repeated policy. " * 1000)
        self.assert_rejected("substantially shorter")

    def test_numbered_stage_or_next_stage_runtime_returns_are_rejected(self):
        """重新加入编号阶段和 next_stage 指令应失败，不能从导航契约复活流程执行器。"""
        relative = SKILL / "SKILL.md"
        self.write(
            relative,
            self.read(relative) + "\nUse decide_decoupling_workflow and next_stage SA01.\n",
        )
        self.assert_rejected("retired numbered-stage runtime instruction")

    def test_workflow_context_ownership_and_dynamic_execution_are_explicit(self):
        """去掉 Agent 自持上下文的明确约定必须失败，防止文档暗示新的状态服务。"""
        relative = SKILL / "SKILL.md"
        self.mutate(relative, "Agent 在自身上下文", "外部状态服务")
        self.assert_rejected("Agent 在自身上下文")

    def test_original_map_entry_still_runs_all_contract_checks(self):
        """旧检查 CLI 仍执行完整来源守卫，兼容命令名不能成为跳过校验的空壳。"""
        script = "check-layer-04-workflow-maps.py"
        self.assertEqual(self.run_check(script=script).returncode, 0)
        self.change_mapping(lambda item: item["sources"].pop())
        result = self.run_check(script=script)
        self.assertEqual(result.returncode, 1)
        self.assertIn("expected all 218 baseline source files", result.stdout)


if __name__ == "__main__":
    unittest.main()

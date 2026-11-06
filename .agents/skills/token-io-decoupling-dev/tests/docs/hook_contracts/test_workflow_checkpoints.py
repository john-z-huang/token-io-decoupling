"""以删除或弱化契约的夹具验证关键 Hook 语义。"""

from __future__ import annotations

import unittest

from .fixtures import EVENT_SECTIONS, HOOKS, JSON_FENCE, ROOT, HookFixture


class WorkflowHookContractTests(HookFixture):
    """逐条破坏真实 Hook 规则，证明精简没有丢失安全、职责和恢复约束。"""

    def test_reviewed_repository_has_six_complete_chinese_events(self):
        """真实仓库的六个中文事件应通过完整契约检查。"""
        self.assertEqual(self.run_check(ROOT).returncode, 0)

    def test_every_event_requires_all_six_operational_sections(self):
        """分别删除必需章节，验证任何一个缺口都不能通过。"""
        relative = HOOKS / "completion-requested.md"
        baseline = self.read(relative)
        for heading in EVENT_SECTIONS:
            with self.subTest(heading=heading):
                self.write(relative, baseline.replace("## " + heading, "## Unreviewed section", 1))
                self.assert_rejected("operational section")
        self.write(relative, baseline)

    def test_missing_and_duplicate_machine_contracts_are_rejected(self):
        """删除或复制机器契约围栏，均必须拒绝执行歧义。"""
        relative = HOOKS / "task-received.md"
        baseline = self.read(relative)
        match = JSON_FENCE.search(baseline)
        self.assertIsNotNone(match)
        for changed in (
            baseline[: match.start()] + baseline[match.end() :],
            baseline + "\n" + match[0],
        ):
            with self.subTest(missing=not JSON_FENCE.search(changed)):
                self.write(relative, changed)
                self.assert_rejected("expected one machine contract")

    def test_contract_identity_and_schema_are_checked(self):
        """文档名与事件身份不一致时，不能把另一事件的契约当作当前规则。"""
        self.change_contract(
            "task_received", lambda item: item.update(event_id="completion_requested")
        )
        self.assert_rejected("wrong schema or event identity")

    def test_unknown_machine_contract_field_cannot_define_a_next_stage(self):
        """额外 next_stage 字段不能重新引入代码驱动的阶段推进。"""
        self.change_contract("task_received", lambda item: item.update(next_stage="execution"))
        self.assert_rejected("contract fields differ")

    def test_unknown_and_duplicate_outcomes_are_rejected(self):
        """未知结果与重复结果都必须失败，不能缩减或扩大批准的选择集合。"""
        self.change_contract(
            "completion_requested", lambda item: item["allowed_outcomes"].append("approved")
        )
        self.assert_rejected("invalid or incomplete allowed_outcomes")
        self.change_contract(
            "completion_requested", lambda item: item.update(allowed_outcomes=["continue"] * 6)
        )
        self.assert_rejected("invalid or incomplete allowed_outcomes")

    def test_mode_contract_cannot_silently_drop_single_agent(self):
        """双模式事件不能通过删掉单代理模式而改变适用范围。"""
        self.change_contract("boundary_requested", lambda item: item.update(modes=["multi-agent"]))
        self.assert_rejected("invalid or incomplete modes")

    def test_completion_requires_criteria_and_actual_final_state(self):
        """完成检查同时要求验收标准和真实最终状态证据。"""
        self.change_contract(
            "completion_requested", lambda item: item["required_facts"].remove("acceptance")
        )
        self.assert_rejected("invalid or incomplete required_facts")
        self.change_contract(
            "completion_requested", lambda item: item["required_evidence"].remove("final_state")
        )
        self.assert_rejected("invalid or incomplete required_evidence")

    def test_mirrored_event_source_is_rejected(self):
        """重新加入带语言后缀的事件副本必须触发单源检查。"""
        self.write(HOOKS / "action-observed_zh_cn.md", self.read(HOOKS / "action-observed.md"))
        self.assert_rejected("noncanonical Chinese document path")

    def test_canonical_shared_contract_must_be_consumed(self):
        """事件必须引用当前共享契约，旧后缀引用不能替代它。"""
        self.mutate(HOOKS / "session-resumed.md", "](shared.md)", "](shared_zh_cn.md)")
        self.assert_rejected("canonical shared contract")

    def test_rule_shape_cannot_grant_authority(self):
        """即使结构完整，删除不授予权限与完成验收的约束也必须失败。"""
        self.mutate(
            HOOKS / "shared.md",
            "任何结果都不独自授权或宣布完成",
            "Every outcome grants permission and declares completion",
        )
        self.assert_rejected("任何结果都不独自授权")

    def test_workflow_state_must_remain_in_agent_context(self):
        """将无状态规则改成服务维护数据库时必须拒绝。"""
        self.mutate(
            HOOKS / "shared.md",
            "Workflow 不提供数据库",
            "Workflow maintains its own database",
        )
        self.assert_rejected("Workflow 不提供数据库")

    def test_missing_context_cannot_be_replaced_with_successful_history(self):
        """缺失上下文只能报告缺口，不能编造已通过历史。"""
        self.mutate(
            HOOKS / "shared.md", "上下文缺失是需指明的证据缺口", "上下文缺失时恢复已通过历史"
        )
        self.assert_rejected("上下文缺失是需指明的证据缺口")

    def test_capacity_reservation_is_not_dispatch(self):
        """预留容量或选择建议不能直接创建和派发子代理。"""
        self.mutate(
            HOOKS / "shared.md",
            "容量预留或执行者建议不创建/派发子级",
            "容量预留 creates/dispatches",
        )
        self.assert_rejected("容量预留")

    def test_busy_child_and_full_return_guards_are_required(self):
        """必须等待忙碌的合适子级，并读取完整真实返回后才依赖结果。"""
        self.mutate(
            HOOKS / "shared.md",
            "适任子级忙时等待",
            "assume a busy child is available",
        )
        self.assert_rejected("适任子级忙时等待")
        self.mutate(HOOKS / "shared.md", "读取完整真实安全返回", "receipt only")
        self.assert_rejected("读取完整真实安全返回")

    def test_large_root_output_cannot_bypass_the_release_boundary(self):
        """大输出也不能让 Root 跳过已放行边界直接物化。"""
        self.mutate(
            HOOKS / "boundary-requested.md",
            "Root 不立即物化",
            "Root may immediately materialize it",
        )
        self.assert_rejected("Root 不立即物化")

    def test_effect_uncertainty_requires_readback_before_repeat(self):
        """效果不明时必须保留读回要求，不能直接重放写入。"""
        self.mutate(HOOKS / "action-observed.md", "获准读回", "blind replay")
        self.assert_rejected("获准读回")

    def test_amend_and_evidence_request_do_not_pass_control(self):
        """修订和证据请求不是放行选择，不能隐式继续依赖动作。"""
        self.mutate(
            HOOKS / "progress-reported.md",
            "Amend 先修改 Contract/Decision",
            "Amend immediately continues execution",
        )
        self.assert_rejected("Amend 先修改 Contract/Decision")
        self.mutate(
            HOOKS / "progress-reported.md",
            "不是第四种最终放行选择",
            "a fourth final release choice",
        )
        self.assert_rejected("不是第四种最终放行选择")

    def test_safety_clause_hidden_in_code_or_related_section_does_not_count(self):
        """安全句放进示例代码或参考章节，不能冒充当前执行约束。"""
        relative = HOOKS / "completion-requested.md"
        baseline = self.read(relative)
        clause = "要求独立验证时须真实独立。"
        self.assertIn(clause, baseline)
        for hidden in (
            "\n```text\n" + clause + "\n```\n",
            "\n## Related concepts\n" + clause + "\n",
        ):
            with self.subTest(hidden=hidden):
                self.write(relative, baseline.replace(clause, "", 1) + hidden)
                self.assert_rejected("独立验证")

    def test_completion_stop_and_native_notice_do_not_imply_success(self):
        """服务不能宣布完成，也不能把原生 Stop 改成无限阻塞。"""
        self.mutate(
            HOOKS / "completion-requested.md",
            "服务不宣布任务完成",
            "service declares the task complete",
        )
        self.assert_rejected("服务不宣布任务完成")
        self.mutate(
            HOOKS / "completion-requested.md",
            "不自动阻塞 Stop",
            "always block Stop",
        )
        self.assert_rejected("不自动阻塞 Stop")

    def test_requested_resource_completion_preserves_full_content(self):
        """资源归档要求完整字节保全，摘要不能替代原内容。"""
        self.mutate(HOOKS / "completion-requested.md", "保留完整字节", "keeping a summary")
        self.assert_rejected("保留完整字节")

    def test_instruction_failure_cannot_restore_author_source_lookup(self):
        """编译指令不可用时不能退回读取作者源文件。"""
        self.mutate(
            HOOKS / "session-resumed.md",
            "不转向搜索作者文件",
            "search author files instead",
        )
        self.assert_rejected("不转向搜索作者文件")

    def test_native_stop_coverage_is_not_claimed_as_model_injection(self):
        """原生 Stop 通知不能被文档描述成向模型注入完整契约。"""
        self.mutate(HOOKS / "README.md", "不是模型注入契约", "a model-injected contract")
        self.assert_rejected("不是模型注入契约")

    def test_legacy_checkpoint_entry_delegates_to_the_same_event_contracts(self):
        """兼容检查入口与主入口使用同一事件验证，坏身份仍须拒绝。"""
        self.assertEqual(self.run_check().returncode, 0)
        self.change_contract("task_received", lambda item: item.update(event_id="wrong"))
        result = self.run_check()
        self.assertEqual(result.returncode, 1)
        self.assertIn("wrong schema or event identity", result.stdout)


if __name__ == "__main__":
    unittest.main()

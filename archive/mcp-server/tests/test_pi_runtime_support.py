"""Pi 指令的模块结构、旧宿主清理与 Server 迁移边界回归。"""
from __future__ import annotations

import runpy
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OWNER = (
    "skill/references/coding/layer-01-fundamental-concepts/"
    "session-runtime/runtime-provider-support.md"
)
CORE = runpy.run_path(str(ROOT / "scripts/compliance_core_loader.py"))["load_compliance_core"]()
CHECKER = runpy.run_path(str(ROOT / "scripts/check-layer-01-sections.py"))


class PiRuntimeSupportTests(unittest.TestCase):
    def setUp(self):
        self.text = (ROOT / OWNER).read_text(encoding="utf-8")

    def test_runtime_owner_has_only_pi_modules(self):
        self.assertEqual(CORE.layer01_section_issues(OWNER, self.text), [])
        self.assertEqual(
            [heading for _line, heading, _offset in CORE.top_level_sections(self.text)],
            ["通用规范", "Pi Coding Agent 优化指令", "相关概念"],
        )
        for legacy in ("Codex", "Claude", "ChatGPT", "sonnet", "haiku", "spawn_agent"):
            self.assertNotIn(legacy, self.text)

    def test_installed_skill_relative_path_uses_same_contract(self):
        self.assertEqual(
            CORE.layer01_section_issues(OWNER.removeprefix("skill/"), self.text), []
        )

    def test_required_modules_cannot_be_missing_duplicate_empty_or_reordered(self):
        for heading in ("通用规范", "Pi Coding Agent 优化指令"):
            for changed in (
                self.text.replace(f"## {heading}", "## 不受支持的模块"),
                self.text + f"\n## {heading}\n重复模块。\n",
            ):
                with self.subTest(heading=heading, changed=changed[:40]):
                    self.assertTrue(CORE.layer01_section_issues(OWNER, changed))
        empty = "## 通用规范\n\n## Pi Coding Agent 优化指令\n正文。\n"
        reversed_sections = "## Pi Coding Agent 优化指令\n正文。\n## 通用规范\n正文。\n"
        self.assertTrue(CORE.layer01_section_issues(OWNER, empty))
        self.assertTrue(CORE.layer01_section_issues(OWNER, reversed_sections))

    def test_all_owners_share_pi_structure_with_server_contract(self):
        directory = (ROOT / OWNER).parent.parent
        owners = CHECKER["discover_owner_documents"](directory)
        self.assertEqual(len(owners), 41)
        for owner in owners:
            with self.subTest(owner=owner):
                self.assertEqual(CHECKER["check_document"](owner, ROOT), [])
        # CLI 与 Server 统一使用 Pi 合同，不再对单个 owner 特判。
        other = OWNER.replace("runtime-provider-support.md", "session-model.md")
        self.assertEqual(CORE.layer01_section_issues(other, self.text), [])

    def test_local_validator_rejects_missing_duplicate_empty_and_reordered_modules(self):
        check = CHECKER["layer01_section_issues"]
        self.assertEqual(check(OWNER, self.text), [])
        for heading in ("通用规范", "Pi Coding Agent 优化指令", "相关概念"):
            with self.subTest(heading=heading):
                self.assertTrue(check(OWNER, self.text.replace(f"## {heading}", "## 未知")))
                self.assertTrue(check(OWNER, self.text + f"\n## {heading}\n重复\n"))
        self.assertTrue(check(OWNER, "## 通用规范\n\n## Pi Coding Agent 优化指令\n内容\n## 相关概念\n链接\n"))
        self.assertTrue(check(OWNER, "## Pi Coding Agent 优化指令\n内容\n## 通用规范\n内容\n## 相关概念\n链接\n"))

    def test_active_skill_contains_no_legacy_host_instructions(self):
        import re

        forbidden = re.compile(r"codex|claude|chatgpt|\b(?:haiku|sonnet|spawn_agent|send_input|read_thread|update_plan)\b", re.I)
        for path in (ROOT / "skill").rglob("*.md"):
            with self.subTest(path=path):
                # openai-codex 是 Pi provider 标识，不是旧宿主指令；仅豁免完整标识。
                text = re.sub(r"\bopenai-codex\b", "pi-provider", path.read_text(encoding="utf-8"))
                self.assertIsNone(forbidden.search(text))

    def test_child_endpoint_follows_current_root_metadata(self):
        for fact in (
            "每次创建新子代理前", "PI_PROVIDER", "PI_MODEL",
            "openai-codex", "同一 `openai` API 路由",
            "端点继承不要求模型 ID 或 thinking 与 Root 相同",
            "不得用陈旧启动值覆盖当前状态", "配置优先级",
            "工具不能保证同端点", "不得静默切换 provider",
            "端点跟随是创建必需条件", "不得读取/输出 token",
        ):
            with self.subTest(fact=fact):
                self.assertIn(fact, self.text)
        for relative in (
            "skill/references/coding/layer-01-fundamental-concepts/delegation/delegation-child-creation.md",
            "skill/hooks/delegation.md",
        ):
            with self.subTest(path=relative):
                text = (ROOT / relative).read_text(encoding="utf-8")
                self.assertIn("runtime-provider-support.md#子代理端点跟随-root", text)
                self.assertIn("创建前", text)
                self.assertIn("同端点", text)

    def test_one_shot_extension_and_api_boundaries(self):
        directory = (ROOT / OWNER).parent.parent
        creation = (directory / "delegation/delegation-child-creation.md").read_text(encoding="utf-8")
        self.assertIn("一次性", creation)
        self.assertIn("不伪造宿主 ID", creation)
        self.assertIn("workflow_select_child_effort", creation)
        advisory = (directory / "execution-planning/decisions-advisory.md").read_text(encoding="utf-8")
        for fact in ("OPENAI_API_KEY", "OPENAI_BASE_URL", "gpt-6-luna", "Mock"):
            self.assertIn(fact, advisory)

    def test_delegated_module_handles_synchronous_results_without_replay(self):
        module = ROOT / "skill/hooks/delegation.md"
        text = module.read_text(encoding="utf-8")
        self.assertIn("同一次工具调用创建、派发、执行并返回", text)
        self.assertIn("同步一次性调用返回后直接在 DE07 审阅", text)
        self.assertIn("不重放任务", text)
        self.assertNotIn("不得等子代理结果返回后才开始 DE07", text)

    def test_model_and_extension_boundaries_remain_explicit(self):
        for fact in (
            "Pi 不默认提供内置子代理或 Plan mode",
            "workflow_select_child_effort",
            "Not applicable",
            "OPENAI_API_KEY",
            "OPENAI_BASE_URL",
            "gpt-6-luna",
            "三个独立边界",
            "hidden",
            "isError",
        ):
            self.assertIn(fact, self.text)


if __name__ == "__main__":
    unittest.main()

"""检查共用运行时规则与宿主能力边界。"""
from __future__ import annotations

import runpy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OWNER = (
    "skill/references/coding/layer-01-fundamental-concepts/"
    "session-runtime/runtime-provider-support.md"
)
sys.path.insert(0, str(ROOT / "scripts"))
import document_rules as CORE

CHECKER = runpy.run_path(str(ROOT / "scripts/check-layer-01-sections.py"))


class RuntimeSupportTests(unittest.TestCase):
    def setUp(self):
        self.text = (ROOT / OWNER).read_text(encoding="utf-8")

    def test_runtime_owner_uses_shared_modules(self):
        self.assertEqual(CORE.layer01_section_issues(OWNER, self.text), [])
        self.assertEqual(
            [heading for _line, heading, _offset in CORE.top_level_sections(self.text)],
            ["通用规范", "运行时指引", "相关概念"],
        )
        for legacy in ("Codex", "Claude", "ChatGPT", "sonnet", "haiku", "spawn_agent"):
            self.assertNotIn(legacy, self.text)

    def test_installed_skill_relative_path_uses_same_contract(self):
        self.assertEqual(
            CORE.layer01_section_issues(OWNER.removeprefix("skill/"), self.text), []
        )

    def test_required_modules_cannot_be_missing_duplicate_empty_or_reordered(self):
        for heading in ("通用规范", "运行时指引"):
            for changed in (
                self.text.replace(f"## {heading}", "## 不受支持的模块"),
                self.text + f"\n## {heading}\n重复模块。\n",
            ):
                with self.subTest(heading=heading, changed=changed[:40]):
                    self.assertTrue(CORE.layer01_section_issues(OWNER, changed))
        empty = "## 通用规范\n\n## 运行时指引\n正文。\n"
        reversed_sections = "## 运行时指引\n正文。\n## 通用规范\n正文。\n"
        self.assertTrue(CORE.layer01_section_issues(OWNER, empty))
        self.assertTrue(CORE.layer01_section_issues(OWNER, reversed_sections))

    def test_all_owners_share_runtime_structure(self):
        directory = (ROOT / OWNER).parent.parent
        owners = CHECKER["discover_owner_documents"](directory)
        self.assertEqual(len(owners), 42)
        for owner in owners:
            with self.subTest(owner=owner):
                self.assertEqual(CHECKER["check_document"](owner, ROOT), [])
        other = OWNER.replace("runtime-provider-support.md", "session-model.md")
        self.assertEqual(CORE.layer01_section_issues(other, self.text), [])

    def test_local_validator_rejects_missing_duplicate_empty_and_reordered_modules(self):
        check = CHECKER["layer01_section_issues"]
        self.assertEqual(check(OWNER, self.text), [])
        for heading in ("通用规范", "运行时指引", "相关概念"):
            with self.subTest(heading=heading):
                self.assertTrue(check(OWNER, self.text.replace(f"## {heading}", "## 未知")))
                self.assertTrue(check(OWNER, self.text + f"\n## {heading}\n重复\n"))
        self.assertTrue(check(OWNER, "## 通用规范\n\n## 运行时指引\n内容\n## 相关概念\n链接\n"))
        self.assertTrue(check(OWNER, "## 运行时指引\n内容\n## 通用规范\n内容\n## 相关概念\n链接\n"))

    def test_core_runtime_keeps_host_specific_settings_in_adapters(self):
        coding = ROOT / "skill/references/coding"
        for path in coding.rglob("*.md"):
            with self.subTest(path=path):
                body = path.read_text(encoding="utf-8")
                for host_setting in ("PI_PROVIDER", "PI_MODEL", "openai-codex", "/reload"):
                    self.assertNotIn(host_setting, body)
        entry = (ROOT / "skill/SKILL.md").read_text(encoding="utf-8")
        for host in ("pi", "codex"):
            self.assertIn(f"(references/hosts/{host}.md)", entry)

    def test_child_endpoint_follows_current_root_metadata(self):
        for fact in (
            "每次创建新子代理前", "配置优先级", "工具不能保证同端点",
            "端点跟随是创建必需条件", "端点继承不要求模型 ID 或推理强度与 Root 相同",
        ):
            with self.subTest(fact=fact):
                self.assertIn(fact, self.text)
        pi = (ROOT / "skill/references/hosts/pi.md").read_text(encoding="utf-8")
        for fact in ("PI_PROVIDER", "PI_MODEL", "openai-codex", "同一个 API 路由", "thinking"):
            self.assertIn(fact, pi)
        codex = (ROOT / "skill/references/hosts/codex.md").read_text(encoding="utf-8")
        self.assertIn("可将继承记录为同端点证据", codex)
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
        self.assertIn("模型和推理设置按委派能力实际支持的控制处理", creation)
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
            "明确必需的设置无法落实时暂停创建",
            "Not applicable",
            "OPENAI_API_KEY",
            "OPENAI_BASE_URL",
            "gpt-6-luna",
            "三个独立边界",
            "隐藏或拒绝访问的工具不得换入口绕过",
            "逐项检查错误、状态和缺失证据",
        ):
            self.assertIn(fact, self.text)


if __name__ == "__main__":
    unittest.main()

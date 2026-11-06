"""以真实作者源与产品资源验证编译完整性、可重复性和发布边界。"""

from __future__ import annotations

import io
import json
import re
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path
from posixpath import normpath
from urllib.parse import unquote, urlsplit

from token_io_instruction_compiler.bundle import deterministic_zip
from token_io_instruction_compiler.compiler import Compiler
from token_io_instruction_compiler.sources import CompilationError, canonical, digest


class ProductResourceTests(unittest.TestCase):
    """从真实生成资源核对交付契约，并在隔离作者树中检查变更传播与故障。"""

    @classmethod
    def setUpClass(cls):
        """读取当前产品资源并先拒绝重复或逃逸归档项，避免错误样本污染后续断言。"""
        cls.repository = Path(__file__).resolve().parents[2]
        resources = (
            cls.repository
            / "mcp/packages/token_io_decoupling_workflow/src"
            / "token_io_decoupling_workflow/_resources"
        )
        cls.instructions = json.loads((resources / "instructions.json").read_bytes())
        cls.bundle = (
            cls.repository / "mcp/src/token_io_decoupling/_resources/skill_bundle.zip"
        ).read_bytes()
        with zipfile.ZipFile(io.BytesIO(cls.bundle)) as archive:
            names = archive.namelist()
            if len(names) != len(set(names)):
                raise AssertionError("duplicate packaged Skill file")
            cls.skill_files = {}
            for name in names:
                path = Path(name)
                if path.is_absolute() or ".." in path.parts or "\\" in name:
                    raise AssertionError("unsafe packaged Skill path")
                cls.skill_files[name] = archive.read(name)
        cls.source = cls.repository / "instruction-compiler/sources/skill"

    def staging(self):
        """复制真实作者树供单个变异场景使用，避免测试改写仓库及其它场景。"""
        work = tempfile.TemporaryDirectory()
        self.addCleanup(work.cleanup)
        root = Path(work.name)
        shutil.copytree(
            self.repository / "instruction-compiler/sources", root / "instruction-compiler/sources"
        )
        return root

    def test_six_events_and_two_workflows_replace_numbered_routes(self):
        """产品只暴露六事件与两种短 workflow；编号路线不能以文件或字段形式复活。"""
        self.assertEqual(
            {
                "task_received",
                "boundary_requested",
                "action_observed",
                "progress_reported",
                "completion_requested",
                "session_resumed",
            },
            set(self.instructions["events"]),
        )
        self.assertEqual({"single-agent", "multi-agent"}, set(self.instructions["workflows"]))
        self.assertEqual(3, self.instructions["schema_version"])
        self.assertEqual("zh_cn", self.instructions["language"])
        self.assertNotIn("routes", self.instructions)
        self.assertNotIn("stages", self.instructions)
        self.assertNotRegex("\n".join(self.skill_files), r"(?:^|/)(?:steps|routes|instructions)/")
        self.assertLess(len(self.instructions["nodes"]["contract"]["text"]), 12000)

    def test_all_event_text_is_exactly_shared_plus_current_author_card(self):
        """逐事件对照真实作者来源及 JSON 契约，防止交付正文或结构字段漏掉共享约束。"""
        compiler = Compiler(self.repository)
        for event, entry in self.instructions["events"].items():
            with self.subTest(event=event):
                current = f"references/coding/hooks/{event.replace('_', '-')}.md"
                expected = compiler.sources.instruction(
                    ["references/coding/hooks/shared.md", current]
                )
                self.assertEqual(expected["text"], entry["text"])
                self.assertEqual(expected["content_sha256"], entry["content_sha256"])
                self.assertEqual({"common.shared", f"event.{event}"}, set(entry["instruction_ids"]))
                match = re.search(r"(?ms)^```json\n(.*?)^```", (self.source / current).read_text())
                assert match is not None, "canonical Hook contract is missing"
                contract = json.loads(match.group(1))
                self.assertEqual(contract, {field: entry[field] for field in contract})

    def test_every_instruction_entry_has_complete_inline_text_without_mirrors(self):
        """所有入口必须直接交付无首尾空白的完整正文，不能残留语言镜像分支。"""
        for group in ("nodes", "fragments", "events", "policies", "workflows"):
            for name, entry in self.instructions[group].items():
                with self.subTest(group=group, name=name):
                    self.assertTrue(entry["text"])
                    self.assertEqual(entry["text"].strip(), entry["text"])
                    self.assertNotIn("en", entry)
                    self.assertNotIn("zh_cn", entry)

    def test_short_workflows_are_current_author_instructions_without_event_preloading(self):
        """短 workflow 只包含当前模式指令，不能靠预加载事件政策或隐含后继扩大交付。"""
        compiler = Compiler(self.repository)
        for mode, entry in self.instructions["workflows"].items():
            path = f"references/coding/layer-04-workflows/coding-{mode}.md"
            self.assertEqual(compiler.sources.instruction([path]), entry)
            self.assertLess(len(entry["text"]), 2200)
            self.assertNotIn('"required_facts"', entry["text"])
            self.assertNotIn("next_stage", entry["text"])

    def test_legacy_lookup_ids_are_preserved_without_successors(self):
        """保留既有查询 ID，同时删除路径镜像与动作后继，维持静态查询的兼容边界。"""
        expected = {
            "acceptance",
            "context",
            "contract",
            "contract_change",
            "control",
            "decision",
            "delegation",
            "documentation",
            "git",
            "implementation",
            "mode",
            "output_class",
            "repair",
            "repair_execution",
            "repair_handoff",
            "repair_scope",
            "slice",
            "task_intent",
            "verification",
            "verification_impact",
        }
        self.assertEqual(expected, set(self.instructions["nodes"]))
        self.assertEqual(3, self.instructions["registry"]["contract_version"])
        for node in self.instructions["registry"]["nodes"]:
            self.assertEqual([], node["next_checkpoint_ids"])
            self.assertNotIn("owner_mirrors", node)
            self.assertNotIn("resource_paths", node)
        self.assertNotIn("source_path", json.dumps(self.instructions["context_index"]))
        self.assertEqual(2, self.instructions["context_index"]["schema_version"])

    def test_policies_preserve_fine_grained_scope_without_stage_selection(self):
        """核对物化权限限制和细粒度政策的真实来源，避免迁移时放宽写入或委派条件。"""
        policies = self.instructions["policies"]
        self.assertIn(
            "payload.request.policy_scope: generic_project",
            policies["candidate-compliance"]["text"],
        )
        self.assertIn("不执行代码或授权写入", policies["candidate-compliance"]["text"])
        boundary = self.instructions["events"]["boundary_requested"]["text"]
        for name in (
            "session-role-ownership",
            "task-assignment",
            "child-role-selection",
            "output-token-routing",
        ):
            for selected in policies[name]["sections"].values():
                self.assertIn(selected, boundary)
        self.assertIn("Root 不立即物化", boundary)

    def test_packaged_files_are_current_reviewed_author_sources(self):
        """逐文件对照当前作者内容；只有入口可追加构建页脚，归档不得混入旧语言副本。"""
        for path, data in self.skill_files.items():
            if not path.endswith((".md", ".yaml")):
                continue
            source = (self.source / path).read_text().rstrip()
            content = data.decode()
            if path == "SKILL.md":
                self.assertTrue(content.startswith(source + "\n\n构建："))
                self.assertIn(self.instructions["build_id"], content)
            else:
                self.assertEqual(source + "\n", content)
            self.assertTrue(content.endswith("\n"))
            self.assertFalse(content.endswith("\n\n"))
        self.assertEqual(13, sum(path.endswith(".md") for path in self.skill_files))
        self.assertFalse(any("_zh_cn" in path or "/zh-cn/" in path for path in self.skill_files))

    def test_manifest_and_build_identity_bind_all_delivery_surfaces(self):
        """正文、Skill 清单和文档索引必须属于同一内容身份，防止单表更新造成混批。"""
        manifest = json.loads(self.skill_files["manifest.json"])
        self.assertEqual(3, manifest["schema_version"])
        self.assertEqual("zh_cn", manifest["language"])
        self.assertEqual(self.instructions["build_id"], manifest["build_id"])
        expected = {
            path: digest(data) for path, data in self.skill_files.items() if path != "manifest.json"
        }
        self.assertEqual(expected, manifest["files"])
        self.assertEqual(expected, self.instructions["skill_files"])
        body = {
            key: value
            for key, value in self.instructions.items()
            if key not in {"build_id", "skill_files"}
        }
        self.assertEqual(digest(canonical(body)), self.instructions["build_id"])
        index = json.loads(self.skill_files["instruction-index.json"])
        self.assertEqual(3, index["schema_version"])
        self.assertEqual("zh_cn", index["language"])
        self.assertEqual(set(self.instructions["events"]), set(index["events"]))
        self.assertIsInstance(index["checkpoints"]["contract"]["document"], str)

    def test_packaged_navigation_resolves_inside_single_language_delivery(self):
        """产品中的本地导航都应落在同一交付清单内，不能依赖未安装的作者文件。"""
        for path, data in self.skill_files.items():
            if not path.endswith(".md"):
                continue
            for _label, target in re.findall(r"\[([^\]]+)\]\(([^)]+)\)", data.decode()):
                parts = urlsplit(target)
                if parts.scheme or parts.netloc or not parts.path:
                    continue
                relative = normpath(str(Path(path).parent / unquote(parts.path)))
                self.assertFalse(relative.startswith("../"), (path, target))
                self.assertIn(relative, self.skill_files, (path, target))

    def test_entry_change_invalidates_build_without_rewriting_event_rules(self):
        """只修改入口说明时应更换构建身份，独立事件政策内容应保持原值。"""
        root = self.staging()
        entry = root / "instruction-compiler/sources/skill/SKILL.md"
        entry.write_text(entry.read_text() + "\n验收前审阅当前实际证据。\n")
        updated, _files = Compiler(root).compile()
        self.assertNotEqual(self.instructions["build_id"], updated["build_id"])
        self.assertEqual(self.instructions["events"], updated["events"])

    def test_shared_change_reaches_every_event_and_legacy_contract(self):
        """在共享约束注入可辨识修改，确认所有事件、默认查询及文档交付同步更新。"""
        root = self.staging()
        entry = root / "instruction-compiler/sources/skill/references/coding/hooks/shared.md"
        entry.write_text(entry.read_text().replace("实际权限", "实际权限与 canary-guard", 1))
        updated, files = Compiler(root).compile()
        self.assertNotEqual(self.instructions["build_id"], updated["build_id"])
        for event in updated["events"].values():
            self.assertIn("canary-guard", event["text"])
        self.assertIn("canary-guard", updated["nodes"]["contract"]["text"])
        self.assertIn(b"canary-guard", files["references/coding/hooks/shared.md"])

    def test_report_detaches_source_trace_and_delivery_from_compiler_state(self):
        """调用方修改报告快照后，编译器仍保留原追溯与规模，防止别名共享污染验收。"""
        compiler = Compiler(self.repository)
        document, _files = compiler.compile()
        report = compiler.report
        expected = len(document["nodes"]["contract"]["text"])
        self.assertEqual(expected, report["delivery"]["default_contract"]["characters"])
        self.assertTrue(report["source_hashes"])
        report["delivery"]["default_contract"]["characters"] = -1
        report["source_hashes"].clear()
        current = compiler.report
        self.assertEqual(expected, current["delivery"]["default_contract"]["characters"])
        self.assertTrue(current["source_hashes"])

    def test_unrequested_document_does_not_inflate_or_change_default_delivery(self):
        """加入大量未选文档不应改变构建或归档，证明作者目录不会被无界自动展开。"""
        root = self.staging()
        entry = root / "instruction-compiler/sources/skill/references/unrequested.md"
        entry.write_text("未请求的独立文档。\n" * 2000)
        updated, files = Compiler(root).compile()
        self.assertEqual(self.instructions["build_id"], updated["build_id"])
        self.assertFalse(any("unrequested" in path for path in files))

    def test_contract_missing_sections_invalid_enums_or_duplicate_fences_fail(self):
        """分别破坏必需标题、合法结果和唯一契约块，确认整次编译失败而非猜测修复。"""
        corruptions = (
            ("missing_section", "## 判断", "## 已退役判断"),
            ("outcome", '"continue",', '"allow",'),
            ("duplicate", "\n", "\n```json\n{}\n```\n"),
        )
        for corruption, before, after in corruptions:
            with self.subTest(corruption=corruption):
                root = self.staging()
                path = (
                    root
                    / "instruction-compiler/sources/skill/references/coding/hooks/task-received.md"
                )
                text = path.read_text()
                self.assertIn(before, text)
                path.write_text(text.replace(before, after, 1))
                with self.assertRaises(CompilationError):
                    Compiler(root).compile()

    def test_english_headings_do_not_replace_required_chinese_contract(self):
        """只替换必需中文标题为英文仍应失败，防止旧双语规则成为隐式兼容回退。"""
        root = self.staging()
        path = root / "instruction-compiler/sources/skill/references/coding/hooks/task-received.md"
        path.write_text(path.read_text().replace("## 判断", "## Judgment", 1))
        with self.assertRaisesRegex(CompilationError, "missing or duplicate source heading"):
            Compiler(root).compile()

    def test_link_escape_missing_target_or_retired_language_copy_fails(self):
        """逃逸链接、缺失文件和退役语言路径分别失败，保护交付闭包而非仅检查文件存在。"""
        for target in ("../../../outside.md", "not-delivered.md", "task-received_zh_cn.md"):
            with self.subTest(target=target):
                root = self.staging()
                path = (
                    root
                    / "instruction-compiler/sources/skill/references/coding/hooks/task-received.md"
                )
                path.write_text(path.read_text() + f"\n[当前政策]({target})\n")
                with self.assertRaises(CompilationError):
                    Compiler(root).compile()

    def test_zip_is_reproducible_and_excludes_private_or_retired_sources(self):
        """改变输入顺序仍应产生同一 ZIP，产品清单也不能夹带开发目录或退役源。"""
        self.assertEqual(self.bundle, deterministic_zip(self.skill_files))
        self.assertEqual(
            self.bundle, deterministic_zip(dict(reversed(list(self.skill_files.items()))))
        )
        for path in self.skill_files:
            self.assertNotIn(".agents", path)
            self.assertNotIn("sources", Path(path).parts)
            self.assertNotIn("tests", Path(path).parts)
            self.assertNotIn("layer-01-fundamental-concepts", path)


if __name__ == "__main__":
    unittest.main()

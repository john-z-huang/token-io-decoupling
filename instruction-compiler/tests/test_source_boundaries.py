"""校验显式来源选择、指令依赖和作者目录安全边界。"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from token_io_instruction_compiler.compiler import Compiler
from token_io_instruction_compiler.sources import (
    AuthorSources,
    CompilationError,
    extract_heading,
    safe_file,
    source_path,
    validate_dependency_graph,
)


class HeadingTests(unittest.TestCase):
    """保护真实 Markdown 标题选择，不让示例、重复或空段落伪装成有效政策。"""

    def test_fenced_heading_does_not_end_or_duplicate_real_section(self):
        """代码围栏中的同名标题只是示例，不应截断真实区段或造成重复标题判断。"""
        text = "## Actions\nDo this.\n```md\n## Actions\nexample\n```\n## End\nOther.\n"
        selected = extract_heading(text, "Actions")
        self.assertIn("Do this.", selected)
        self.assertIn("example", selected)
        self.assertNotIn("Other.", selected)

    def test_duplicate_missing_and_empty_sections_fail(self):
        """重复、缺失与无正文的标题均无法唯一交付政策，因此必须明确失败。"""
        for text, title in (("## A\nx\n## A\ny", "A"), ("## A\nx", "B"), ("## A\n\n## B\nx", "A")):
            with self.subTest(text=text), self.assertRaises(CompilationError):
                extract_heading(text, title)


class ExecutionDependencyTests(unittest.TestCase):
    """验证静态指令依赖的完整性；它不代表任务运行路线或阶段状态。"""

    def index(self, fragments):
        """构造最小 schema 2 作者索引，让场景只改变待验证的依赖关系。"""
        return {
            "schema_version": 2,
            "nodes": [{"node_id": "contract", "default_fragment_ids": ["a"]}],
            "fragments": [
                {"node_id": "contract", "source_path": "rule.md", **entry} for entry in fragments
            ],
        }

    def test_missing_dependency_blocks_compilation(self):
        """显式依赖不存在时不能交付部分政策，错误应准确指出缺失依赖。"""
        with self.assertRaisesRegex(CompilationError, "missing instruction dependency"):
            validate_dependency_graph(
                self.index([{"fragment_id": "a", "dependencies": ["missing"]}])
            )

    def test_cycle_blocks_compilation(self):
        """环状依赖没有有限展开，必须在编译阶段失败而非进入递归运行。"""
        with self.assertRaisesRegex(CompilationError, "cycle"):
            validate_dependency_graph(
                self.index(
                    [
                        {"fragment_id": "a", "dependencies": ["b"]},
                        {"fragment_id": "b", "dependencies": ["a"]},
                    ]
                )
            )

    def test_valid_order_does_not_turn_control_return_into_source_recursion(self):
        """完整且无环的依赖图可以通过校验，不将合法静态组合误判为运行控制回跳。"""
        validate_dependency_graph(
            self.index([{"fragment_id": "a", "dependencies": ["b"]}, {"fragment_id": "b"}])
        )


class SourceBoundaryTests(unittest.TestCase):
    """通过临时作者文件验证读取范围、预算和单次编译的缓存与身份隔离。"""

    def sources(self, temp, *, max_chars=12000):
        """正常构造读取器，显式设置完整指令预算，避免测试依赖未初始化私有字段。"""
        return AuthorSources(Path(temp), max_chars=max_chars)

    def test_traversal_and_symlink_sources_rejected(self):
        """逃逸、绝对路径、符号链接和缺失文件都不能成为作者来源。"""
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "actual.md").write_text("policy")
            (root / "link.md").symlink_to(root / "actual.md")
            for path in ("../outside.md", "/tmp/outside.md", "link.md", "missing.md"):
                with self.subTest(path=path), self.assertRaises(CompilationError):
                    safe_file(root, path)

    def test_navigation_does_not_expand_or_create_runtime_continuations(self):
        """本地链接保留可读标签，但不自动读取目标或生成继续调用，限制指令展开范围。"""
        with tempfile.TemporaryDirectory() as temp:
            sources = self.sources(temp)
            (Path(temp) / "first.md").write_text(
                "# First\n\n## Actions\nRead [Second](second.md) when applicable.\n"
            )
            (Path(temp) / "second.md").write_text("# Second\nSeparate required guard.\n")
            result = sources.instruction(["first.md"])
            self.assertIn("Read Second when applicable.", result["text"])
            self.assertNotIn("Separate required guard", result["text"])
            self.assertNotIn("rules_get_context", result["text"])
            self.assertEqual(["first.md"], sources.trace["closures"]["first.md"]["sources"])
            self.assertFalse(sources.trace["closures"]["first.md"]["navigation_expanded"])

    def test_explicit_dependency_is_required_even_when_link_is_only_navigation(self):
        """导航本身不强制读取；一旦目标成为显式依赖，缺失文件就必须阻止交付。"""
        with tempfile.TemporaryDirectory() as temp:
            sources = self.sources(temp)
            (Path(temp) / "first.md").write_text("# First\n[Missing](missing.md).\n")
            sources.instruction(["first.md"])
            with self.assertRaises(CompilationError):
                sources.instruction(["first.md", "missing.md"])

    def test_explicit_section_selection_excludes_other_judgment_and_examples(self):
        """仅交付明确选择的判断区段，另一事件与不存在的标题不能混入当前指令。"""
        with tempfile.TemporaryDirectory() as temp:
            sources = self.sources(temp)
            (Path(temp) / "first.md").write_text(
                "# First\n## Current judgment\nCheck authorization.\n"
                "## Another event\nDo not preload this.\n"
            )
            result = sources.instruction(["first.md#Current judgment"])
            self.assertIn("Check authorization", result["text"])
            self.assertNotIn("Do not preload this", result["text"])
            with self.assertRaises(CompilationError):
                sources.instruction(["first.md#Missing"])

    def test_budget_failure_never_truncates_required_instruction(self):
        """完整正文超过预算时整体失败，不能靠截断末尾规则获得表面成功。"""
        with tempfile.TemporaryDirectory() as temp:
            sources = self.sources(temp, max_chars=100)
            (Path(temp) / "first.md").write_text("# First\n" + "Required guard. " * 50)
            with self.assertRaisesRegex(CompilationError, "exceeds approved bound"):
                sources.instruction(["first.md"])

    def test_duplicate_explicit_sources_are_delivered_once(self):
        """重复指定同一来源时只交付一次正文及身份，避免重复约束耗尽预算。"""
        with tempfile.TemporaryDirectory() as temp:
            sources = self.sources(temp)
            (Path(temp) / "first.md").write_text("# First\nRequired guard.\n")
            result = sources.instruction(["first.md", "first.md"])
            self.assertEqual(1, result["text"].count("Required guard"))
            self.assertEqual(1, len(result["instruction_ids"]))

    def test_source_content_cache_is_local_to_each_compilation(self):
        """修改文件后新读取器必须看到新内容及 Hash，防止跨构建缓存沿用旧政策。"""
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "first.md"
            path.write_text("# First\nOriginal guard.\n")
            first = self.sources(temp).instruction(["first.md"])
            path.write_text("# First\nRevised guard.\n")
            second = self.sources(temp).instruction(["first.md"])
            self.assertIn("Original guard", first["text"])
            self.assertIn("Revised guard", second["text"])
            self.assertNotEqual(first["content_sha256"], second["content_sha256"])

    def test_source_identities_preserve_sections_and_readable_paths(self):
        """不同标题或不同真实路径必须保留不同身份，不能通过标点归一化意外合并。"""
        with tempfile.TemporaryDirectory() as temp:
            sources = self.sources(temp)
            self.assertNotEqual(
                sources.identity("references/owner.md#判断"),
                sources.identity("references/owner.md#结果"),
            )
            self.assertEqual(
                "references/owner.md",
                source_path("instruction-compiler/sources/skill/references/owner.md"),
            )
            self.assertNotEqual(
                sources.identity("references/first_owner.md"),
                sources.identity("references/first-owner.md"),
            )
            self.assertNotEqual(
                source_path("references/first_owner.md"),
                source_path("references/first-owner.md"),
            )

    def test_static_lookup_rejects_successor_chains_and_mismatched_index(self):
        """先验证禁用运行后继，再验证注册表与索引一致性，避免静态查询退化成执行器。"""
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            sources = root / "instruction-compiler/sources"
            sources.mkdir(parents=True)
            registry = {
                "contract_version": 3,
                "nodes": [
                    {
                        "node_id": "contract",
                        "owner_path": "rule.md",
                        "owner_section": "判断",
                        "evaluation_mode": "direct",
                        "failure_action": "暂停依赖工作。",
                        "required_facts": [],
                        "required_evidence": [],
                        "legal_branches": [],
                        "next_checkpoint_ids": ["contract"],
                    }
                ],
            }
            index = {
                "schema_version": 2,
                "nodes": [{"node_id": "contract", "default_fragment_ids": ["a"]}],
                "fragments": [
                    {"fragment_id": "a", "node_id": "contract", "source_path": "rule.md"}
                ],
            }
            (sources / "rule-registry.json").write_text(json.dumps(registry))
            (sources / "rule-context-index.json").write_text(json.dumps(index))
            with self.assertRaisesRegex(CompilationError, "must not declare workflow successors"):
                Compiler(root)
            registry["nodes"][0]["next_checkpoint_ids"] = []
            index["nodes"] = []
            (sources / "rule-registry.json").write_text(json.dumps(registry))
            (sources / "rule-context-index.json").write_text(json.dumps(index))
            with self.assertRaisesRegex(CompilationError, "registry and index nodes differ"):
                Compiler(root)

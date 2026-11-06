"""验证作者 JSON 的真实形状，拒绝旧镜像和无效指令依赖。"""

import copy
import json
import unittest
from pathlib import Path

from token_io_instruction_compiler.contracts import validate_author_registry
from token_io_instruction_compiler.sources import CompilationError, validate_dependency_graph


class AuthorMetadataTests(unittest.TestCase):
    """以真实作者 JSON 为基线逐项破坏形状，确保静态类型之外还有实际输入校验。"""

    def setUp(self):
        """每个场景重新读取当前作者契约，后续只变异复制数据，避免测试相互污染。"""
        sources = Path(__file__).resolve().parents[1] / "sources"
        self.registry = json.loads((sources / "rule-registry.json").read_bytes())
        self.index = json.loads((sources / "rule-context-index.json").read_bytes())

    def test_current_chinese_author_contracts_are_accepted(self):
        """当前单中文注册表和索引应原样通过，作为所有拒绝场景的有效对照。"""
        self.assertEqual(self.registry, validate_author_registry(self.registry))
        validate_dependency_graph(self.index)

    def test_registry_rejects_obsolete_versions_and_mirror_fields(self):
        """旧版本、可被隐式转型的版本值及旧镜像字段都不能进入 contract 3。"""
        for version in (True, 2, 3.0, "3"):
            with self.subTest(version=version), self.assertRaises(CompilationError):
                validate_author_registry({**self.registry, "contract_version": version})
        for field in ("owner_mirrors", "resource_paths"):
            changed = copy.deepcopy(self.registry)
            changed["nodes"][0][field] = {}
            with (
                self.subTest(field=field),
                self.assertRaisesRegex(CompilationError, "unsupported author registry node fields"),
            ):
                validate_author_registry(changed)

    def test_registry_rejects_missing_fields_and_nontext_requirements(self):
        """缺失 owner 或非文本要求必须失败，防止不完整 JSON 借类型注解绕过验证。"""
        for value in (None, "objective", [123], [""]):
            changed = copy.deepcopy(self.registry)
            changed["nodes"][0]["required_facts"] = value
            with self.subTest(value=value), self.assertRaises(CompilationError):
                validate_author_registry(changed)
        changed = copy.deepcopy(self.registry)
        del changed["nodes"][0]["owner_section"]
        with self.assertRaisesRegex(CompilationError, "unsupported author registry node fields"):
            validate_author_registry(changed)

    def test_context_index_rejects_old_bilingual_sections_and_versions(self):
        """索引只接受严格整数 schema 2 和单 section，旧双语字段不能成为回退。"""
        for version in (True, 1, 2.0, "2"):
            with self.subTest(version=version), self.assertRaises(CompilationError):
                validate_dependency_graph({**self.index, "schema_version": version})
        for field in ("section_en", "section_zh_cn"):
            changed = copy.deepcopy(self.index)
            changed["fragments"][0][field] = "判断"
            with (
                self.subTest(field=field),
                self.assertRaisesRegex(CompilationError, "unsupported author fragment fields"),
            ):
                validate_dependency_graph(changed)

    def test_context_index_rejects_missing_sources_and_invalid_dependency_arrays(self):
        """依赖必须是文本数组且每个片段有显式来源，否则不能宣称依赖已完整交付。"""
        for value in (None, "fragment", [123], [""]):
            changed = copy.deepcopy(self.index)
            changed["fragments"][0]["dependencies"] = value
            with self.subTest(value=value), self.assertRaises(CompilationError):
                validate_dependency_graph(changed)
        changed = copy.deepcopy(self.index)
        del changed["fragments"][0]["source_path"]
        with self.assertRaisesRegex(CompilationError, "missing author fragment fields"):
            validate_dependency_graph(changed)

    def test_context_index_rejects_duplicate_fragment_and_node_identities(self):
        """重复片段或节点 ID 必须在建映射前失败，避免后写值静默覆盖已审核条目。"""
        for field, reason in (
            ("fragments", "duplicate author fragment identity"),
            ("nodes", "duplicate author context-index node"),
        ):
            changed = copy.deepcopy(self.index)
            changed[field].append(copy.deepcopy(changed[field][0]))
            with self.subTest(field=field), self.assertRaisesRegex(CompilationError, reason):
                validate_dependency_graph(changed)

"""只允许已审核的 Hook 文档关系，保留旧分层与链接安全边界。"""

from __future__ import annotations

from .fixtures import HOOKS, SKILL, SOURCE_MAP, HookFixture

MEMO = SKILL / "references/coding/layer-01-fundamental-concepts/context-exchange/content-memo.md"
FLOW = SKILL / "references/coding/layer-04-workflows/coding-single-agent.md"


class HookLayerLinkTests(HookFixture):
    """区分有限合法 Hook 关系与未知、退役、越界或符号链接关系。"""

    def check_links(self):
        """通过正式层级链接 CLI 读取退出码与错误定位。"""
        result = self.run_check(script="check-doc-layer-links.py")
        return result.returncode, result.stderr

    def test_reviewed_events_and_entrypoints_pass(self):
        """当前六事件与精简入口的已审核关系应整体通过。"""
        self.assertEqual((0, ""), self.check_links())

    def test_unknown_hook_target_is_not_accepted_by_short_workflow(self):
        """新建未知 Hook 并从流程链接它，不能仅凭目标存在获得合法依赖。"""
        self.write(HOOKS / "invented.md", "# Unreviewed Hook\n")
        self.write(FLOW, self.read(FLOW) + "\n[Unknown](../hooks/invented.md)\n")
        result, errors = self.check_links()
        self.assertEqual(1, result)
        self.assertIn("layer violation", errors)
        self.assertIn("invented.md", errors)

    def test_unknown_hook_source_cannot_read_shared_by_directory_membership(self):
        """未知文件放进 hooks 目录，也不能自动读取共享契约。"""
        self.write(HOOKS / "invented.md", "# Unreviewed Hook\n\n[Shared](shared.md)\n")
        result, errors = self.check_links()
        self.assertEqual(1, result)
        self.assertIn("invented.md", errors)

    def test_unmapped_legacy_owner_cannot_jump_to_hooks(self):
        """退役层内新增的文件不能绕过有限合法边跳向 Hook。"""
        path = SKILL / "references/coding/layer-01-fundamental-concepts/invented.md"
        self.write(path, "# Unmapped\n\n[Shared](../hooks/shared.md)\n")
        result, errors = self.check_links()
        self.assertEqual(1, result)
        self.assertIn("layer violation", errors)

    def test_retired_owner_cannot_gain_access_from_historical_mapping(self):
        """历史映射保留旧来源证据，但不授权被重建的旧文档访问当前 Hook。"""
        self.write(MEMO, "# 退役文档\n\n[事件](../../hooks/boundary-requested.md)\n")
        result, errors = self.check_links()
        self.assertEqual(1, result)
        self.assertIn("content-memo.md", errors)
        self.assertIn("boundary-requested.md", errors)

    def test_hook_directory_cannot_adopt_a_third_flow(self):
        """Hook 导航不能在两个已批准流程之外自行接纳第三个流程。"""
        unknown = SKILL / "references/coding/layer-04-workflows/coding-invented.md"
        self.write(unknown, "# Unreviewed flow\n")
        self.write(
            HOOKS / "README.md",
            self.read(HOOKS / "README.md")
            + "\n[Other flow](../layer-04-workflows/coding-invented.md)\n",
        )
        result, errors = self.check_links()
        self.assertEqual(1, result)
        self.assertIn("coding-invented.md", errors)

    def test_reviewed_edge_rejects_retired_language_mirror(self):
        """合法共享链接改回旧语言后缀时必须失败。"""
        path = HOOKS / "task-received.md"
        self.write(path, self.read(path).replace("](shared.md)", "](shared_zh_cn.md)"))
        result, errors = self.check_links()
        self.assertEqual(1, result)
        self.assertIn("shared_zh_cn.md", errors)
        self.assertIn("missing local target", errors)

    def test_reviewed_edge_still_requires_existing_target(self):
        """已审核的依赖仍要求当前目标文件真实存在。"""
        (self.root / HOOKS / "shared.md").unlink()
        result, errors = self.check_links()
        self.assertEqual(1, result)
        self.assertIn("missing local target", errors)

    def test_reviewed_edge_cannot_follow_a_symlink_target(self):
        """目标改成符号链接后，即使文件内容可读也必须拒绝。"""
        outside = self.root / "outside.md"
        outside.write_text("# External policy\n")
        target = self.root / HOOKS / "shared.md"
        target.unlink()
        target.symlink_to(outside)
        result, errors = self.check_links()
        self.assertEqual(1, result)
        self.assertIn("missing local target", errors)

    def test_hook_link_cannot_escape_repository(self):
        """链接中的路径回退不能把 Hook 依赖扩展到仓库外。"""
        path = HOOKS / "task-received.md"
        self.write(path, self.read(path) + "\n[Escape](../../../../../../../../outside.md)\n")
        result, errors = self.check_links()
        self.assertEqual(1, result)
        self.assertIn("target escapes repository", errors)

    def test_unrelated_references_do_not_gain_mutual_access(self):
        """新增 Hook 例外不赋予普通参考文档互相依赖的权利。"""
        self.write(SKILL / "references/one.md", "# One\n\n[Other](two.md)\n")
        self.write(SKILL / "references/two.md", "# Two\n")
        result, errors = self.check_links()
        self.assertEqual(1, result)
        self.assertIn("layer violation", errors)

    def test_old_direct_layer01_to_workflow_dependency_remains_rejected(self):
        """重建退役来源后直连当前流程，原分层拒绝仍生效。"""
        self.write(MEMO, "# 退役文档\n\n[流程](../../layer-04-workflows/coding-single-agent.md)\n")
        result, errors = self.check_links()
        self.assertEqual(1, result)
        self.assertIn("layer violation", errors)

    def test_existing_invalid_json_map_is_a_reported_configuration_failure(self):
        """来源文件存在但 JSON 损坏时，应报告配置错误而不是忽略它。"""
        self.write(SOURCE_MAP, "{invalid-json")
        result, errors = self.check_links()
        self.assertEqual(1, result)
        self.assertIn("source map contains invalid JSON", errors)

    def test_existing_malformed_source_list_is_not_silently_ignored(self):
        """当前映射 schema 下的非对象来源项必须明确失败。"""
        self.write(SOURCE_MAP, '{"schema_version":2,"sources":[null]}')
        result, errors = self.check_links()
        self.assertEqual(1, result)
        self.assertIn("source map contains an invalid source entry", errors)

    def test_existing_invalid_schema_is_a_reported_configuration_failure(self):
        """布尔值不能冒充映射版本号。"""
        self.write(SOURCE_MAP, '{"schema_version":true,"sources":[]}')
        result, errors = self.check_links()
        self.assertEqual(1, result)
        self.assertIn("source map has an invalid schema", errors)

    def test_unreadable_existing_map_reports_configuration_failure(self):
        """存在但不可读的来源文件必须失败，并恢复权限以便可靠清理。"""
        mapping = self.root / SOURCE_MAP
        original_mode = mapping.stat().st_mode
        try:
            mapping.chmod(0)
            result, errors = self.check_links()
            self.assertEqual(1, result)
            self.assertIn("source map could not be read", errors)
        finally:
            mapping.chmod(original_mode)

    def test_absent_mapping_is_explicitly_compatible_with_old_repositories(self):
        """没有引入来源映射的空旧仓库仍可执行通用链接检查。"""
        legacy = self.root / "legacy-repository"
        legacy.mkdir()
        result = self.run_check(legacy, script="check-doc-layer-links.py")
        self.assertEqual(result.returncode, 0, result.stderr)

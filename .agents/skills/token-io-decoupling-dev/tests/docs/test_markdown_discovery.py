"""验证中文单源契约和有界 Markdown 发现，使用实际私有 CLI。"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SCRIPTS = ROOT / ".agents/skills/token-io-decoupling-dev/scripts"
SKILL = "instruction-compiler/sources/skill"


class MarkdownDiscoveryTests(unittest.TestCase):
    """在最小中文仓库中验证文档发现与真实 CLI 的路径、链接和入口边界。"""

    def setUp(self):
        """构造合法中文入口和模拟环境目录，使每个负例只改变一项前提。"""
        work = tempfile.TemporaryDirectory()
        self.addCleanup(work.cleanup)
        self.root = Path(work.name)
        self.write("AGENTS.md", "[开发指导](.agents/skills/token-io-decoupling-dev/AGENTS.md)")
        self.write(".agents/skills/token-io-decoupling-dev/AGENTS.md", "# 项目开发指导")
        self.write(
            ".agents/skills/token-io-decoupling-dev/references/mcp/DEVELOPMENT.md", "# 开发指南"
        )
        self.write(SKILL + "/SKILL.md", "---\nname: fixture\n---\n\n# 中文指令")
        self.write(SKILL + "/agents/openai.yaml", 'short_description: "中文开发指令"\n')
        self.write(SKILL + "/references/share/shared-protocols.md", "# 通用协议\n\n中文规则。")
        self.write("README.md", "# 项目说明")
        self.write("docs/index.md", "# 项目网站")
        self.write("mcp/custom-env/pyvenv.cfg", "home = /usr/bin\n")
        self.write("mcp/custom-env/Lib/noise.md", "generated")

    def write(self, relative, text):
        """向独立临时仓库写入场景文件，避免污染真实作者文档。"""
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def run_check(self, script="check-chinese-docs.py"):
        """运行实际 CLI 并合并诊断，不通过导入内部函数替代入口测试。"""
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / script), "--root", str(self.root)],
            text=True,
            capture_output=True,
            timeout=30,
        )
        return result.returncode, result.stdout + result.stderr

    def discovered(self):
        """读取发现 CLI 的 JSON 路径集，检查被扫描和被排除的具体文件。"""
        result, output = self.run_check("markdown_discovery.py")
        self.assertEqual(result, 0, output)
        return set(json.loads(output))

    def test_valid_chinese_fixture_passes_both_scanners(self):
        """完整中文单源样例应同时通过发现与文档检查。"""
        self.assertEqual(self.run_check()[0], 0)
        self.assertEqual(self.run_check("check-doc-layer-links.py")[0], 0)

    def test_private_policy_does_not_belong_at_root(self):
        """项目私有规范位于 Skill 下，根入口只负责指向它。"""
        self.write("MULTI_LINGUAL.md", "# 私有开发规范")
        result, output = self.run_check()
        self.assertEqual(result, 1)
        self.assertIn("development-only documentation policy", output)

    def test_mirror_filename_is_rejected(self):
        """当前维护文件不能恢复 _zh_cn 语言副本命名。"""
        self.write("AGENTS_zh_cn.md", "# 中文重复入口")
        result, output = self.run_check()
        self.assertEqual(result, 1)
        self.assertIn("noncanonical Chinese document path", output)

    def test_locale_directory_copy_is_rejected(self):
        """旧 docs/zh-cn 目录不能成为另一套当前页面。"""
        self.write("docs/zh-cn/index.md", "# 重复网页")
        result, output = self.run_check()
        self.assertEqual(result, 1)
        self.assertIn("noncanonical Chinese document path", output)

    def test_language_switch_navigation_is_rejected(self):
        """中文单源入口不能继续提供双语切换导航。"""
        self.write("README.md", "# 项目说明\n\n[English](README.md)")
        result, output = self.run_check()
        self.assertEqual(result, 1)
        self.assertIn("language-switch navigation", output)

    def test_retired_mirror_dependency_is_rejected(self):
        """当前正文链接到旧语言后缀时，即使内容存在也必须拒绝。"""
        self.write("README.md", "# 项目说明\n\n[指导](AGENTS_zh_cn.md)")
        result, output = self.run_check()
        self.assertEqual(result, 1)
        self.assertIn("retired mirror dependency", output)

    def test_canonical_development_guidance_must_exist(self):
        """规范开发入口缺失时应失败，不能只凭链接文本通过。"""
        (self.root / ".agents/skills/token-io-decoupling-dev/AGENTS.md").unlink()
        result, output = self.run_check()
        self.assertEqual(result, 1)
        self.assertIn("missing or symlink local target", output)

    def test_wrong_development_entrypoint_is_rejected(self):
        """根 AGENTS 指向错误开发规范时必须报告入口错误。"""
        self.write("AGENTS.md", "# 项目开发")
        result, output = self.run_check()
        self.assertEqual(result, 1)
        self.assertIn("canonical private development guidance", output)

    def test_missing_local_target_fails(self):
        """本地文件缺失必须被报告，不能作为外部链接跳过。"""
        self.write("README.md", "# 项目说明\n\n[不存在](missing.md)")
        result, output = self.run_check()
        self.assertEqual(result, 1)
        self.assertIn("missing or symlink local target", output)

    def test_missing_local_anchor_fails(self):
        """文件存在但目标章节不存在时仍须失败。"""
        self.write("README.md", "# 项目说明\n\n[目录](docs/index.md#不存在)")
        result, output = self.run_check()
        self.assertEqual(result, 1)
        self.assertIn("missing local anchor", output)

    def test_generated_noise_is_pruned_and_private_mcp_docs_remain(self):
        """生成噪声应被裁剪，私有 MCP 开发说明仍在实际发现范围。"""
        noise = (
            "mcp/.venv/lib/noise.md",
            "mcp/.pytest_cache/noise.md",
            "mcp/__pycache__/noise.md",
            "mcp/dist/noise.md",
            "skills/token-io-decoupling/noise.md",
            "mcp/src/token_io_decoupling/_resources/noise.md",
            "mcp/custom-env/Lib/noise.md",
            ".serena/cache/noise.md",
            "vendor/package/noise.md",
        )
        for path in noise:
            self.write(path, "sed: --: No such file or directory")
        discovered = self.discovered()
        self.assertIn(
            ".agents/skills/token-io-decoupling-dev/references/mcp/DEVELOPMENT.md", discovered
        )
        self.assertTrue(set(noise).isdisjoint(discovered))
        self.assertEqual(self.run_check()[0], 0)

    def test_authored_generated_target_requires_current_file(self):
        """指向生成位置的维护中链接仍要求当前目标真实存在。"""
        target = self.write("skills/token-io-decoupling/SKILL.md", "# 生成的中文指令")
        self.write("README.md", "# 项目说明\n\n[已生成Skill](skills/token-io-decoupling/SKILL.md)")
        self.assertEqual(self.run_check()[0], 0)
        target.unlink()
        self.assertIn("missing or symlink local target", self.run_check()[1])

    def test_symlink_target_is_rejected(self):
        """本地链接不能借符号链接目标绕过仓库边界。"""
        outside = self.write("external/entry.md", "# 外部目标")
        link = self.root / "skills/token-io-decoupling/SKILL.md"
        link.parent.mkdir(parents=True)
        link.symlink_to(outside)
        self.write("README.md", "# 项目说明\n\n[错误目标](skills/token-io-decoupling/SKILL.md)")
        result, output = self.run_check()
        self.assertEqual(result, 1)
        self.assertIn("missing or symlink local target", output)

    def test_directory_and_file_symlinks_are_not_scanned(self):
        """发现器既不扫描目录链接，也不把文件链接当作者源。"""
        actual = self.write("outside/foreign.md", "# 外部文档")
        directory = self.root / "mcp/linked-docs"
        directory.parent.mkdir(exist_ok=True)
        directory.symlink_to(actual.parent, target_is_directory=True)
        file_link = self.root / "mcp/linked.md"
        file_link.symlink_to(actual)
        discovered = self.discovered()
        self.assertNotIn("mcp/linked-docs/foreign.md", discovered)
        self.assertNotIn("mcp/linked.md", discovered)

    def test_skill_metadata_is_chinese_and_single_source(self):
        """Skill 元数据必须描述中文单源能力，不能保留双语描述。"""
        self.write(SKILL + "/agents/openai.yaml", 'short_description: "English | 中文"')
        result, output = self.run_check()
        self.assertEqual(result, 1)
        self.assertIn("single Chinese description", output)

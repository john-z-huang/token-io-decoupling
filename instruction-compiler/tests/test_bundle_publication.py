"""验证同批次发布、可选导出与旧受管文件保护。"""

import json
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from token_io_instruction_compiler.compiler import compile_repository
from token_io_instruction_compiler.sources import CompilationError, digest


class OptionalExportTests(unittest.TestCase):
    """以真实资源作为输入隔离发布器，检查可选导出、持久产物及本地修改保护。"""

    def setUp(self):
        """替换上游编译以固定输入，保留真实发布逻辑；所有写入限定在临时仓库。"""
        repository = Path(__file__).resolve().parents[2]
        work = tempfile.TemporaryDirectory()
        self.addCleanup(work.cleanup)
        self.root = Path(work.name)
        self.preview = self.root / "skills/token-io-decoupling"
        resource = (
            repository
            / "mcp/packages/token_io_decoupling_workflow/src"
            / "token_io_decoupling_workflow/_resources"
        )
        instructions = json.loads((resource / "instructions.json").read_bytes())
        bundle = repository / "mcp/src/token_io_decoupling/_resources/skill_bundle.zip"
        with zipfile.ZipFile(bundle) as archive:
            self.skill_files = {name: archive.read(name) for name in archive.namelist()}
        report = json.loads((repository / "instruction-compiler/build-report.json").read_bytes())
        report.pop("build_id")
        report.pop("language")
        compiler_patch = patch("token_io_instruction_compiler.compilation.pipeline.Compiler")
        compiler = compiler_patch.start().return_value
        self.addCleanup(compiler_patch.stop)
        compiler.compile.return_value = instructions, self.skill_files
        compiler.report = report
        compile_repository(self.root)
        self.persistent = [
            path
            for path in self.root.rglob("*")
            if path.is_file() and self.preview not in path.parents
        ]

    def test_absent_export_is_optional_and_check_does_not_create_it(self):
        """未创建开发导出时 check 仍可成功，而且必须保持所有持久产物字节不变。"""
        shutil.rmtree(self.preview)
        snapshot = {path: path.read_bytes() for path in self.persistent}
        compile_repository(self.root, check=True)
        self.assertFalse(self.preview.exists())
        self.assertEqual(snapshot, {path: path.read_bytes() for path in self.persistent})

    def test_existing_export_still_rejects_missing_changed_and_extra_files(self):
        """一旦存在开发导出，缺文件、改字节和多余文件都应报陈旧，不能被可选性掩盖。"""
        entry = self.preview / "SKILL.md"
        original = entry.read_bytes()
        entry.unlink()
        with self.assertRaisesRegex(CompilationError, "skills/token-io-decoupling/SKILL.md"):
            compile_repository(self.root, check=True)
        entry.write_bytes(original + b"unexpected change\n")
        with self.assertRaisesRegex(CompilationError, "skills/token-io-decoupling/SKILL.md"):
            compile_repository(self.root, check=True)
        entry.write_bytes(original)
        extra = self.preview / "obsolete.md"
        extra.write_text("obsolete\n")
        with self.assertRaisesRegex(CompilationError, "obsolete.md"):
            compile_repository(self.root, check=True)

    def test_persistent_artifacts_are_required_and_checked_without_export(self):
        """没有开发导出也必须逐个核对持久产物，防止只验证可选目录而漏掉产品资源。"""
        shutil.rmtree(self.preview)
        self.assertEqual(4, len(self.persistent))
        for path in self.persistent:
            with self.subTest(path=path.relative_to(self.root)):
                original = path.read_bytes()
                path.unlink()
                with self.assertRaisesRegex(CompilationError, "resources are stale"):
                    compile_repository(self.root, check=True)
                path.write_bytes(original + b"unexpected change\n")
                with self.assertRaisesRegex(CompilationError, "resources are stale"):
                    compile_repository(self.root, check=True)
                path.write_bytes(original)

    def test_compile_recreates_the_optional_export(self):
        """普通发布应能重建缺失导出，并让后续只读检查接受完全相同的文件。"""
        shutil.rmtree(self.preview)
        compile_repository(self.root)
        for path, expected in self.skill_files.items():
            self.assertEqual(expected, (self.preview / path).read_bytes())
        compile_repository(self.root, check=True)

    def test_invalid_previous_manifest_entry_prevents_publication(self):
        """旧清单字段无效时，在任何产物写入前停止，避免不可信清单指导清理。"""
        manifest = self.preview / "manifest.json"
        content = json.loads(manifest.read_bytes())
        content["files"]["retired.md"] = 123
        manifest.write_text(json.dumps(content))
        before = {path: path.read_bytes() for path in self.persistent}

        with self.assertRaisesRegex(CompilationError, "invalid previous export manifest entry"):
            compile_repository(self.root)

        self.assertEqual(before, {path: path.read_bytes() for path in self.persistent})
        self.assertEqual(123, json.loads(manifest.read_bytes())["files"]["retired.md"])

    def test_compile_retires_only_unmodified_files_from_the_previous_manifest(self):
        """有本地编辑的旧受管文件必须保留；恢复旧字节后才允许退役，重复发布应稳定。"""
        retired = self.preview / "instructions/unit.0123456789abcdef.md"
        retired.parent.mkdir(parents=True, exist_ok=True)
        retired.write_text("old generated instruction\n")
        manifest_path = self.preview / "manifest.json"
        manifest = json.loads(manifest_path.read_bytes())
        manifest["files"][retired.relative_to(self.preview).as_posix()] = digest(
            retired.read_bytes()
        )
        manifest_path.write_text(json.dumps(manifest))
        retired.write_text("local edits\n")
        with self.assertRaisesRegex(
            CompilationError, "obsolete exported document has local changes"
        ):
            compile_repository(self.root)
        self.assertEqual("local edits\n", retired.read_text())
        retired.write_text("old generated instruction\n")
        compile_repository(self.root)
        self.assertFalse(retired.exists())
        compile_repository(self.root, check=True)
        compile_repository(self.root)
        compile_repository(self.root, check=True)

    def test_bilingual_export_is_verified_before_retiring_its_managed_mirror(self):
        """旧 schema 2 仅用于核验受管字节；保护本地编辑后，才迁移为单中文 schema 3。"""
        retired = self.preview / "SKILL_zh_cn.md"
        retired.write_text("旧受管中文入口\n")
        manifest_path = self.preview / "manifest.json"
        previous = json.loads(manifest_path.read_bytes())
        previous["schema_version"] = 2
        previous.pop("language")
        previous["files"][retired.name] = digest(retired.read_bytes())
        manifest_path.write_text(json.dumps(previous))
        retired.write_text("未发布的本地修改\n")
        with self.assertRaisesRegex(
            CompilationError, "obsolete exported document has local changes"
        ):
            compile_repository(self.root)
        self.assertEqual("未发布的本地修改\n", retired.read_text())
        retired.write_text("旧受管中文入口\n")
        compile_repository(self.root)
        self.assertFalse(retired.exists())
        current = json.loads(manifest_path.read_bytes())
        self.assertEqual((3, "zh_cn"), (current["schema_version"], current["language"]))
        compile_repository(self.root, check=True)

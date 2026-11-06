"""准备隔离作者树，通过真实开发 CLI 验证文档契约。"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
SCRIPTS = ROOT / ".agents/skills/token-io-decoupling-dev/scripts"
SKILL = Path("instruction-compiler/sources/skill")
HOOKS = SKILL / "references/coding/hooks"
SOURCE_MAP = Path("instruction-compiler/sources/hook-source-map.json")
JSON_FENCE = re.compile(r"(?ms)^```json\s*\n(.*?)^```\s*$")
EVENT_SECTIONS = ("触发", "适用范围", "上下文与证据", "判断", "结果与反馈", "失败与恢复")


class HookFixture(unittest.TestCase):
    """复制真实作者源作为独立试验仓库，通过实际检查 CLI 验证每个变坏场景。"""

    def setUp(self):
        """每个用例获得独立源副本，局部文档损坏不污染其他负例或真实仓库。"""
        work = tempfile.TemporaryDirectory()
        self.addCleanup(work.cleanup)
        self.root = Path(work.name)
        shutil.copytree(
            ROOT / "instruction-compiler/sources", self.root / "instruction-compiler/sources"
        )

    def read(self, relative):
        """读取试验仓库中的文档，保持与检查器相同的 UTF-8 输入。"""
        return (self.root / relative).read_text(encoding="utf-8")

    def write(self, relative, text):
        """仅修改临时源副本，允许用例构造原本不存在的非法路径。"""
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def mutate(self, relative, before, after):
        """先确认要破坏的原句真实存在，再替换一次，防止负例因过时文本而空跑。"""
        baseline = self.read(relative)
        self.assertIn(before, baseline)
        self.write(relative, baseline.replace(before, after, 1))

    def change_contract(self, event, change):
        """只重写指定事件的 JSON 契约，保持其余正文不变以隔离形状验证。"""
        relative = HOOKS / (event.replace("_", "-") + ".md")
        text = self.read(relative)
        match = JSON_FENCE.search(text)
        contract = json.loads(match.group(1))
        change(contract)
        updated = json.dumps(contract, ensure_ascii=False, indent=2)
        self.write(relative, text[: match.start(1)] + updated + "\n" + text[match.end(1) :])

    def change_mapping(self, change):
        """对真实来源映射施加一个局部变更，保留其他基线记录供完整性检查。"""
        mapping = json.loads(self.read(SOURCE_MAP))
        change(mapping)
        self.write(SOURCE_MAP, json.dumps(mapping, ensure_ascii=False, indent=2) + "\n")

    def run_check(self, root=None, script="check-workflow-checkpoints.py"):
        """启动真实检查子进程，不通过导入脚本或修改 sys.path 绕过 CLI 行为。"""
        return subprocess.run(
            [sys.executable, str(SCRIPTS / script), "--root", str(root or self.root)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=30,
        )

    def assert_rejected(self, reason):
        """要求变坏输入以固定失败码和具体原因拒绝，未处理异常不算有效拒绝。"""
        result = self.run_check()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertIn(reason, result.stdout)

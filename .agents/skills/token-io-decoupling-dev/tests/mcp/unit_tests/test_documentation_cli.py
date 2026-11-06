"""通过真实私有 CLI 验证中文入口、文档发现和旧分层拒绝。"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[6]
SCRIPTS = REPO / ".agents/skills/token-io-decoupling-dev/scripts"
SKILL = "instruction-compiler/sources/skill"


def _write(root: Path, relative: str, content: str) -> None:
    """在独立临时仓库准备文档，不改变真实项目文件。"""
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _run(script: str, root: Path) -> subprocess.CompletedProcess[str]:
    """执行实际私有 CLI，保留退出码和诊断以检查入口行为。"""
    return subprocess.run(
        [sys.executable, str(SCRIPTS / script), "--root", str(root)],
        text=True,
        capture_output=True,
        timeout=30,
    )


def _chinese_fixture(root: Path) -> None:
    """准备单中文Skill、开发指向和共享协议，避免负例被无关入口错误掩盖。"""
    _write(root, "AGENTS.md", "[开发指导](.agents/skills/token-io-decoupling-dev/AGENTS.md)")
    _write(root, ".agents/skills/token-io-decoupling-dev/AGENTS.md", "# 开发指导")
    _write(root, SKILL + "/SKILL.md", "---\nname: fixture\n---\n\n# 中文工作流")
    _write(root, SKILL + "/agents/openai.yaml", 'short_description: "中文指令"\n')
    _write(root, SKILL + "/references/share/shared-protocols.md", "# 共享协议")


def test_chinese_cli_accepts_canonical_relative_target(tmp_path: Path) -> None:
    """中文规范路径和真实目标锚点应通过检查。"""
    _chinese_fixture(tmp_path)
    _write(tmp_path, "docs/a.md", "# 中文说明\n\n[参考](b.md#目标)")
    _write(tmp_path, "docs/b.md", "# 目标")
    result = _run("check-chinese-docs.py", tmp_path)
    assert result.returncode == 0, result.stderr


def test_chinese_cli_rejects_retired_mirror_and_language_switch(tmp_path: Path) -> None:
    """旧语言副本与切换导航同时存在时，诊断必须分别指出问题。"""
    _chinese_fixture(tmp_path)
    _write(tmp_path, "docs/a.md", "# 中文说明\n\n[简体中文](a_zh_cn.md)")
    _write(tmp_path, "docs/a_zh_cn.md", "# 旧副本")
    result = _run("check-chinese-docs.py", tmp_path)
    assert result.returncode == 1
    output = result.stdout + result.stderr
    assert "language-switch navigation remains" in output
    assert "a_zh_cn.md" in output


def test_layer_cli_preserves_direct_retired_layer_rejection(tmp_path: Path) -> None:
    """新Hook合法边不能削弱原分层对退役层直连的拒绝。"""
    source = SKILL + "/references/coding/layer-01-fundamental-concepts/a.md"
    target = SKILL + "/references/coding/layer-02-workflow-concepts/b.md"
    _write(tmp_path, source, "# 退役来源\n\n[错误边](../layer-02-workflow-concepts/b.md)")
    _write(tmp_path, target, "# 退役目标")
    result = _run("check-doc-layer-links.py", tmp_path)
    assert result.returncode == 1
    assert "layer violation" in result.stderr
    assert source in result.stderr
    assert target in result.stderr


def test_discovery_covers_canonical_private_mcp_guidance(tmp_path: Path) -> None:
    """当前私有MCP说明及新文件必须被自动发现，不再依靠手写双语文件对清单。"""
    prefix = ".agents/skills/token-io-decoupling-dev/references/mcp/"
    expected = {
        prefix + name + ".md"
        for name in (
            "AGENTS",
            "CODEX_CALLER_CONTEXT",
            "CANDIDATE_COMPLIANCE",
            "DEVELOPMENT",
            "TASK_PLAN_TOOLS",
            "WORKFLOW_ROUTING",
            "new-note",
        )
    }
    for relative in expected:
        _write(tmp_path, relative, "# 中文开发说明")
    _write(tmp_path, "unmanaged/note.md", "# 中文补充说明")
    result = _run("markdown_discovery.py", tmp_path)
    assert result.returncode == 0, result.stderr
    assert expected <= set(json.loads(result.stdout))

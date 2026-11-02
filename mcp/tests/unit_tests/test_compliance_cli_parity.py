from __future__ import annotations

import contextlib
import io
import runpy
import sys
from pathlib import Path, PurePosixPath

from token_io_decoupling_core.compliance_core import (
    PAIR_ROOTS,
    document_link_issues,
    is_bilingual_document,
    layer01_section_issues,
)

REPO = Path(__file__).resolve().parents[3]
SCRIPTS = REPO / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def _write(root: Path, relative: str, content: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _multilingual_fixture(root: Path) -> None:
    for english in PAIR_ROOTS:
        content = "---\n" if english == "docs/skill/SKILL.md" else "stable\n"
        _write(root, english, content)
        _write(root, f"{english.removesuffix('.md')}_zh_cn.md", "稳定\n")
    _write(root, "AGENTS_zh_cn.md", "MULTI_LINGUAL_zh_cn.md\n")
    for english in (
        "docs/skill/references/share/shared-protocols.md",
        "docs/skill/references/coding/layer-01-fundamental-concepts/session-runtime/session-model.md",
        "docs/skill/references/coding/layer-01-fundamental-concepts/execution-control/execution-control.md",
        "docs/skill/references/coding/layer-01-fundamental-concepts/context-exchange/context-exchange.md",
    ):
        _write(root, english, "core text\n")
        _write(root, f"{english.removesuffix('.md')}_zh_cn.md", "核心文本\n")
    for path in (
        "docs/skill/references/example/a.md",
        "docs/skill/references/example/a_zh_cn.md",
        "docs/skill/references/example/b.md",
        "docs/skill/references/example/b_zh_cn.md",
    ):
        _write(root, path, "stable\n")
    _write(
        root,
        "docs/skill/references/example/a.md",
        "[wrong-language](b_zh_cn.md)\n",
    )
    _write(root, "docs/index.md", "index\n")
    _write(root, "docs/zh-cn/index.md", "索引\n")
    _write(root, "AGENTS.md", "MULTI_LINGUAL.md\n")
    _write(root, "AGENTS_zh_cn.md", "MULTI_LINGUAL_zh_cn.md\n")
    _write(root, "docs/skill/SKILL.md", "---\nreferences/example/a.md\n")
    _write(root, "docs/skill/SKILL_zh_cn.md", "参考\n")
    _write(root, "docs/skill/agents/openai.yaml", 'short_description: "English | 中文"\n')


def test_multilingual_cli_uses_shared_target_tuple_parser(tmp_path: Path) -> None:
    _multilingual_fixture(tmp_path)
    script = runpy.run_path(str(SCRIPTS / "check-multilingual-docs.py"))
    stderr = io.StringIO()
    with contextlib.redirect_stderr(stderr):
        result = script["main"](tmp_path)
    assert result == 1
    assert (
        "cross-language Markdown link: docs/skill/references/example/a.md -> b_zh_cn.md"
        in stderr.getvalue()
    )


def test_multilingual_cli_accepts_language_switch_to_exact_mirror(tmp_path: Path) -> None:
    _multilingual_fixture(tmp_path)
    _write(
        tmp_path,
        "docs/skill/references/example/a.md",
        "[简体中文](a_zh_cn.md)\n",
    )
    _write(
        tmp_path,
        "docs/skill/references/example/a_zh_cn.md",
        "[English](a.md)\n",
    )
    script = runpy.run_path(str(SCRIPTS / "check-multilingual-docs.py"))
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        result = script["main"](tmp_path)
    assert result == 0
    assert stderr.getvalue() == ""
    assert "Multilingual documentation validation passed." in stdout.getvalue()


def test_link_and_layer01_cli_helpers_match_the_shared_core(tmp_path: Path) -> None:
    source = "docs/skill/references/coding/layer-01-fundamental-concepts/a.md"
    target = "docs/skill/references/coding/layer-02-workflow-concepts/b.md"
    _write(tmp_path, source, "[bad layer](../layer-02-workflow-concepts/b.md)\n")
    _write(tmp_path, target, "target\n")
    script = runpy.run_path(str(SCRIPTS / "check-doc-layer-links.py"))
    documents = {
        source: (tmp_path / source).read_text(encoding="utf-8"),
        target: (tmp_path / target).read_text(encoding="utf-8"),
    }
    expected = document_link_issues(documents)
    stderr = io.StringIO()
    with contextlib.redirect_stderr(stderr):
        result = script["main"](tmp_path)
    assert result == 1
    assert all(issue in stderr.getvalue() for issue in expected)

    section_path = "docs/skill/references/coding/layer-01-fundamental-concepts/example.md"
    section_text = "## General rules\nRules.\n"
    path = _write(tmp_path, section_path, section_text)
    section_script = runpy.run_path(str(SCRIPTS / "check-layer-01-sections.py"))
    assert section_script["check_document"](path, tmp_path) == layer01_section_issues(
        PurePosixPath(section_path).as_posix(), section_text
    )


def test_runtime_and_cli_share_explicit_mcp_document_pairs(tmp_path: Path) -> None:
    expected = {
        "mcp/AGENTS.md",
        "mcp/CODEX_CALLER_CONTEXT.md",
        "mcp/CANDIDATE_COMPLIANCE.md",
        "mcp/DEVELOPMENT.md",
        "mcp/TASK_PLAN_TOOLS.md",
        "mcp/WORKFLOW_ROUTING.md",
    }
    assert expected <= set(PAIR_ROOTS)
    assert all(is_bilingual_document(path) for path in expected)
    assert all(
        is_bilingual_document(
            PurePosixPath(path).with_name(f"{PurePosixPath(path).stem}_zh_cn.md").as_posix()
        )
        for path in expected
    )
    assert not is_bilingual_document("mcp/unmanaged-note.md")

    script = runpy.run_path(str(SCRIPTS / "check-multilingual-docs.py"))
    assert {path.as_posix() for path in script["PAIR_ROOTS"]} == set(PAIR_ROOTS)

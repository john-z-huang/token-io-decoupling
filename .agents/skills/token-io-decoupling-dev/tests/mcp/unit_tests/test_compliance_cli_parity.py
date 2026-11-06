from __future__ import annotations

import contextlib
import io
import runpy
import sys
from pathlib import Path, PurePosixPath

REPO = Path(__file__).resolve().parents[6]
SCRIPTS = REPO / ".agents/skills/token-io-decoupling-dev/scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from compliance_core_loader import load_compliance_core  # noqa: E402

SKILL_SOURCE = "instruction-compiler/sources/skill/"
_PRIVATE = load_compliance_core()
PAIR_ROOTS = _PRIVATE.PAIR_ROOTS
document_link_issues = _PRIVATE.document_link_issues
is_bilingual_document = _PRIVATE.is_bilingual_document
layer01_section_issues = _PRIVATE.layer01_section_issues


def _write(root: Path, relative: str, content: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _multilingual_fixture(root: Path) -> None:
    for english in PAIR_ROOTS:
        content = (
            "---\n" if english == "instruction-compiler/sources/skill/SKILL.md" else "stable\n"
        )
        _write(root, english, content)
        _write(root, f"{english.removesuffix('.md')}_zh_cn.md", "稳定\n")
    _write(
        root,
        "AGENTS_zh_cn.md",
        ".agents/skills/token-io-decoupling-dev/AGENTS_zh_cn.md\n",
    )
    for english in (
        SKILL_SOURCE + "references/share/shared-protocols.md",
        SKILL_SOURCE
        + "references/coding/layer-01-fundamental-concepts/session-runtime/session-model.md",
        SKILL_SOURCE
        + "references/coding/layer-01-fundamental-concepts/execution-control/execution-control.md",
        SKILL_SOURCE
        + "references/coding/layer-01-fundamental-concepts/context-exchange/context-exchange.md",
    ):
        _write(root, english, "core text\n")
        _write(root, f"{english.removesuffix('.md')}_zh_cn.md", "核心文本\n")
    for path in (
        SKILL_SOURCE + "references/example/a.md",
        SKILL_SOURCE + "references/example/a_zh_cn.md",
        SKILL_SOURCE + "references/example/b.md",
        SKILL_SOURCE + "references/example/b_zh_cn.md",
    ):
        _write(root, path, "stable\n")
    _write(
        root,
        SKILL_SOURCE + "references/example/a.md",
        "[wrong-language](b_zh_cn.md)\n",
    )
    _write(root, "docs/index.md", "index\n")
    _write(root, "docs/zh-cn/index.md", "索引\n")
    _write(root, "AGENTS.md", ".agents/skills/token-io-decoupling-dev/AGENTS.md\n")
    _write(
        root,
        "AGENTS_zh_cn.md",
        ".agents/skills/token-io-decoupling-dev/AGENTS_zh_cn.md\n",
    )
    _write(root, "instruction-compiler/sources/skill/SKILL.md", "---\nreferences/example/a.md\n")
    _write(root, "instruction-compiler/sources/skill/SKILL_zh_cn.md", "参考\n")
    _write(
        root,
        "instruction-compiler/sources/skill/agents/openai.yaml",
        'short_description: "English | 中文"\n',
    )


def test_multilingual_cli_uses_shared_target_tuple_parser(tmp_path: Path) -> None:
    _multilingual_fixture(tmp_path)
    script = runpy.run_path(str(SCRIPTS / "check-multilingual-docs.py"))
    stderr = io.StringIO()
    with contextlib.redirect_stderr(stderr):
        result = script["main"](tmp_path)
    assert result == 1
    assert (
        "cross-language Markdown link: " + SKILL_SOURCE + "references/example/a.md -> b_zh_cn.md"
    ) in stderr.getvalue()


def test_multilingual_cli_accepts_language_switch_to_exact_mirror(tmp_path: Path) -> None:
    _multilingual_fixture(tmp_path)
    _write(
        tmp_path,
        SKILL_SOURCE + "references/example/a.md",
        "[简体中文](a_zh_cn.md)\n",
    )
    _write(
        tmp_path,
        SKILL_SOURCE + "references/example/a_zh_cn.md",
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
    source = SKILL_SOURCE + "references/coding/layer-01-fundamental-concepts/a.md"
    target = SKILL_SOURCE + "references/coding/layer-02-workflow-concepts/b.md"
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

    section_path = SKILL_SOURCE + "references/coding/layer-01-fundamental-concepts/example.md"
    section_text = "## General rules\nRules.\n"
    path = _write(tmp_path, section_path, section_text)
    section_script = runpy.run_path(str(SCRIPTS / "check-layer-01-sections.py"))
    assert section_script["check_document"](path, tmp_path) == layer01_section_issues(
        PurePosixPath(section_path).as_posix(), section_text
    )


def test_private_checkers_cover_migrated_mcp_document_pairs(tmp_path: Path) -> None:
    expected = {
        ".agents/skills/token-io-decoupling-dev/references/mcp/AGENTS.md",
        ".agents/skills/token-io-decoupling-dev/references/mcp/CODEX_CALLER_CONTEXT.md",
        ".agents/skills/token-io-decoupling-dev/references/mcp/CANDIDATE_COMPLIANCE.md",
        ".agents/skills/token-io-decoupling-dev/references/mcp/DEVELOPMENT.md",
        ".agents/skills/token-io-decoupling-dev/references/mcp/TASK_PLAN_TOOLS.md",
        ".agents/skills/token-io-decoupling-dev/references/mcp/WORKFLOW_ROUTING.md",
    }
    assert expected <= set(PAIR_ROOTS)
    assert all(is_bilingual_document(path) for path in expected)
    assert all(
        is_bilingual_document(
            PurePosixPath(path).with_name(f"{PurePosixPath(path).stem}_zh_cn.md").as_posix()
        )
        for path in expected
    )
    assert is_bilingual_document(
        ".agents/skills/token-io-decoupling-dev/references/mcp/new-note.md"
    )
    assert not is_bilingual_document("unmanaged/note.md")

    script = runpy.run_path(str(SCRIPTS / "check-multilingual-docs.py"))
    assert {path.as_posix() for path in script["PAIR_ROOTS"]} == set(PAIR_ROOTS)

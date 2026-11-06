#!/usr/bin/env python3
"""Validate bilingual Markdown structure, link isolation, and common core rules."""

from __future__ import annotations

import re
import sys
from pathlib import Path, PurePosixPath

from compliance_core_loader import load_compliance_core
from markdown_discovery import discover_markdown

_COMPLIANCE_CORE = load_compliance_core()

ROOT = Path(__file__).resolve().parents[4]
ZH_SUFFIX = "_zh_cn.md"
LINK_RE = _COMPLIANCE_CORE._LINK_RE
FENCED_CODE_RE = _COMPLIANCE_CORE._MULTILINGUAL_FENCE_RE

PAIR_ROOTS = [Path(path) for path in _COMPLIANCE_CORE.PAIR_ROOTS]

CORE_DOCS = [
    PurePosixPath("instruction-compiler/sources/skill/references/share/shared-protocols.md"),
    PurePosixPath("instruction-compiler/sources/skill/references/coding/layer-01-fundamental-concepts/session-runtime/session-model.md"),
    PurePosixPath("instruction-compiler/sources/skill/references/coding/layer-01-fundamental-concepts/execution-control/execution-control.md"),
    PurePosixPath("instruction-compiler/sources/skill/references/coding/layer-01-fundamental-concepts/context-exchange/context-exchange.md"),
]

LOCALE_DIRECTORY_PAIRS = [
    (PurePosixPath("docs/index.md"), PurePosixPath("docs/zh-cn/index.md")),
]

PRODUCT_SPECIFIC_PATTERNS = {
    "Luna": re.compile(r"\bLuna\b", re.IGNORECASE),
    "concrete GPT model": re.compile(r"\bgpt-[a-z0-9_.-]+", re.IGNORECASE),
    "Codex": re.compile(r"\bCodex\b", re.IGNORECASE),
    "OpenAI": re.compile(r"\bOpenAI\b", re.IGNORECASE),
    "Claude": re.compile(r"\bClaude(?:\s+Code)?\b", re.IGNORECASE),
    "Anthropic": re.compile(r"\bAnthropic\b", re.IGNORECASE),
    "Sonnet": re.compile(r"\bSonnet\b", re.IGNORECASE),
    "Opus": re.compile(r"\bOpus\b", re.IGNORECASE),
    "Codex home path": re.compile(r"~/.codex(?:/|\b)", re.IGNORECASE),
    "Claude home path": re.compile(r"~/.claude(?:/|\b)", re.IGNORECASE),
    "reasoning_effort parameter": re.compile(r"\breasoning_effort\b", re.IGNORECASE),
}


def zh_peer(path: PurePosixPath) -> PurePosixPath:
    return PurePosixPath(_COMPLIANCE_CORE.mirror_path(path.as_posix()))


def en_peer(path: PurePosixPath) -> PurePosixPath:
    return PurePosixPath(_COMPLIANCE_CORE.mirror_path(path.as_posix()))


def normalize_target(source: PurePosixPath, raw: str) -> PurePosixPath | None:
    return _COMPLIANCE_CORE.normalize_multilingual_target(source, raw)


def main(root: Path | None = None) -> int:
    root = Path(root or ROOT).absolute()
    errors: list[str] = []
    markdown_files = discover_markdown(root)

    for markdown in markdown_files:
        text = markdown.read_text(encoding="utf-8")
        if "sed: --: No such file or directory" in text:
            errors.append(f"stray shell-error text: {markdown.relative_to(root)}")

    skill_text = (root / "instruction-compiler/sources/skill/SKILL.md").read_text(encoding="utf-8")
    if not skill_text.startswith("---\n"):
        errors.append("instruction-compiler/sources/skill/SKILL.md must start with YAML front matter")

    english_docs = [PurePosixPath(path.as_posix()) for path in PAIR_ROOTS]
    english_docs += [
        PurePosixPath(path.relative_to(root).as_posix())
        for path in markdown_files
        if _COMPLIANCE_CORE.is_bilingual_document(path.relative_to(root).as_posix())
        if not path.name.endswith(ZH_SUFFIX)
    ]
    bilingual_english = [path for path in english_docs if (root / path).exists()]
    known_pairs = set(bilingual_english)
    known_pairs.update(zh_peer(path) for path in bilingual_english)
    all_relative_paths = [
        PurePosixPath(path.relative_to(root).as_posix()).as_posix()
        for path in markdown_files
    ]
    errors.extend(
        _COMPLIANCE_CORE.multilingual_mirror_issues(
            all_relative_paths,
            lambda path: (root / PurePosixPath(path)).exists(),
        )
    )

    for english, chinese in LOCALE_DIRECTORY_PAIRS:
        if not (root / english).exists():
            errors.append(f"missing locale-directory English file: {english}")
        if not (root / chinese).exists():
            errors.append(f"missing locale-directory Chinese file: {chinese}")

    known_documents = {
        path.as_posix(): (root / path).read_text(encoding="utf-8")
        for path in sorted(known_pairs, key=str)
        if (root / path).exists()
    }
    errors.extend(_COMPLIANCE_CORE.multilingual_cross_language_issues(known_documents))

    for english in CORE_DOCS:
        for rel in (english, zh_peer(english)):
            file_path = root / rel
            if not file_path.exists():
                errors.append(f"missing product-neutral core document: {rel}")
                continue
            text = file_path.read_text(encoding="utf-8")
            # Layer-01 has provider sections; only the opening and general rules
            # must stay product-neutral. Provider headings themselves name products.
            text = text.split("\n## Codex CLI / ChatGPT Desktop ", 1)[0]
            for label, pattern in PRODUCT_SPECIFIC_PATTERNS.items():
                if pattern.search(text):
                    errors.append(f"product-specific term in core ({label}): {rel}")

    for obsolete in ("MULTI_LINGUAL.md", "MULTI_LINGUAL_zh_cn.md"):
        if (root / obsolete).exists():
            errors.append(f"development-only multilingual owner must not exist at root: {obsolete}")

    agents = (root / "AGENTS.md").read_text(encoding="utf-8")
    if ".agents/skills/token-io-decoupling-dev/AGENTS.md" not in agents or ".agents/skills/token-io-decoupling-dev/AGENTS_zh_cn.md" in agents:
        errors.append("AGENTS.md must link the private English development AGENTS.md")

    agents_zh = (root / "AGENTS_zh_cn.md").read_text(encoding="utf-8")
    if ".agents/skills/token-io-decoupling-dev/AGENTS_zh_cn.md" not in agents_zh:
        errors.append("AGENTS_zh_cn.md must link the private Chinese development AGENTS_zh_cn.md")

    skill = (root / "instruction-compiler/sources/skill/SKILL.md").read_text(encoding="utf-8")
    if "references/" in skill and re.search(r"references/[^)\s\x60]*_zh_cn\.md", skill):
        errors.append("instruction-compiler/sources/skill/SKILL.md must not reference _zh_cn references")

    skill_zh = (root / "instruction-compiler/sources/skill/SKILL_zh_cn.md").read_text(encoding="utf-8")
    for match in re.findall(r"references/[^)\s\x60]+\.md", skill_zh):
        if not match.endswith(ZH_SUFFIX):
            errors.append(f"instruction-compiler/sources/skill/SKILL_zh_cn.md references an English file: {match}")

    openai_yaml = (root / "instruction-compiler/sources/skill/agents/openai.yaml").read_text(encoding="utf-8")
    short_description = re.search(
        r'^\s*short_description:\s*["\'](.+)["\']\s*$',
        openai_yaml,
        re.MULTILINE,
    )
    if not short_description:
        errors.append("instruction-compiler/sources/skill/agents/openai.yaml is missing short_description")
    elif " | " not in short_description.group(1):
        errors.append("instruction-compiler/sources/skill/agents/openai.yaml short_description must use 'English | 中文' format")

    if errors:
        print("Multilingual documentation validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print("Multilingual documentation validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

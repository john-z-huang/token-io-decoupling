#!/usr/bin/env python3
"""Validate bilingual Markdown structure, link isolation, and common core rules."""

from __future__ import annotations

import re
import sys
from pathlib import Path, PurePosixPath

from markdown_discovery import discover_markdown

ROOT = Path(__file__).resolve().parents[1]
ZH_SUFFIX = "_zh_cn.md"
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
FENCED_CODE_RE = re.compile(r"```.*?```", re.DOTALL)

PAIR_ROOTS = [
    Path("README.md"),
    Path("SKILL.md"),
    Path("AGENTS.md"),
    Path("MULTI_LINGUAL.md"),
    Path("workflows/coding.md"),
    Path("ENHANCED_ARCHITECTURE.md"),
    Path("EXTERNAL_REFERENCES.md"),
    Path("mcp/DEVELOPMENT.md"),
]

CORE_DOCS = [
    PurePosixPath("references/share/shared-protocols.md"),
    PurePosixPath("references/coding/layer-01-fundamental-concepts/session-model.md"),
    PurePosixPath("references/coding/layer-01-fundamental-concepts/execution-control.md"),
    PurePosixPath("references/coding/layer-01-fundamental-concepts/context-exchange.md"),
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
    return path.with_name(f"{path.stem}_zh_cn.md")


def en_peer(path: PurePosixPath) -> PurePosixPath:
    return path.with_name(path.name.removesuffix(ZH_SUFFIX) + ".md")


def normalize_target(source: PurePosixPath, raw: str) -> PurePosixPath | None:
    target = raw.split("#", 1)[0].split("?", 1)[0]
    if not target or "://" in target or target.startswith("mailto:") or not target.endswith(".md"):
        return None
    return PurePosixPath(source.parent, target)


def main(root: Path | None = None) -> int:
    root = Path(root or ROOT).absolute()
    errors: list[str] = []
    markdown_files = discover_markdown(root)

    for markdown in markdown_files:
        text = markdown.read_text(encoding="utf-8")
        if "sed: --: No such file or directory" in text:
            errors.append(f"stray shell-error text: {markdown.relative_to(root)}")

    skill_text = (root / "SKILL.md").read_text(encoding="utf-8")
    if not skill_text.startswith("---\n"):
        errors.append("SKILL.md must start with YAML front matter")

    english_docs = [PurePosixPath(p.as_posix()) for p in PAIR_ROOTS]
    english_docs += [
        PurePosixPath(p.relative_to(root).as_posix())
        for p in markdown_files
        if p.is_relative_to(root / "references")
        if not p.name.endswith(ZH_SUFFIX)
    ]

    bilingual_english = [p for p in english_docs if (root / p).exists()]
    bilingual_set = set(bilingual_english)

    for english in bilingual_english:
        chinese = zh_peer(english)
        if not (root / chinese).exists():
            errors.append(f"missing Chinese mirror: {chinese} for {english}")

    paired_root_zh = {zh_peer(PurePosixPath(p.as_posix())).name for p in PAIR_ROOTS}
    for chinese_path in [p for p in markdown_files if p.name.endswith(ZH_SUFFIX)]:
        chinese = PurePosixPath(chinese_path.relative_to(root).as_posix())
        english = en_peer(chinese)
        is_reference = bool(chinese.parts) and chinese.parts[0] == "references"
        if (is_reference or chinese.name in paired_root_zh) and not (root / english).exists():
            errors.append(f"missing English canonical file: {english} for {chinese}")

    known_pairs = bilingual_set | {zh_peer(p) for p in bilingual_set}

    for english, chinese in LOCALE_DIRECTORY_PAIRS:
        if not (root / english).exists():
            errors.append(f"missing locale-directory English file: {english}")
        if not (root / chinese).exists():
            errors.append(f"missing locale-directory Chinese file: {chinese}")

    for rel in sorted(known_pairs, key=str):
        file_path = root / rel
        if not file_path.exists():
            continue
        text = file_path.read_text(encoding="utf-8")
        text_without_code = FENCED_CODE_RE.sub("", text)
        source_is_zh = rel.name.endswith(ZH_SUFFIX)
        for raw_target in LINK_RE.findall(text_without_code):
            target = normalize_target(rel, raw_target)
            if target is None:
                continue
            target_is_zh = target.name.endswith(ZH_SUFFIX)
            counterpart = en_peer(rel) if source_is_zh else zh_peer(rel)
            if source_is_zh != target_is_zh and target != counterpart:
                errors.append(f"cross-language Markdown link: {rel} -> {raw_target}")

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

    agents = (root / "AGENTS.md").read_text(encoding="utf-8")
    if "MULTI_LINGUAL.md" not in agents or "MULTI_LINGUAL_zh_cn.md" in agents:
        errors.append("AGENTS.md must reference only MULTI_LINGUAL.md")

    agents_zh = (root / "AGENTS_zh_cn.md").read_text(encoding="utf-8")
    if "MULTI_LINGUAL_zh_cn.md" not in agents_zh:
        errors.append("AGENTS_zh_cn.md must reference MULTI_LINGUAL_zh_cn.md")

    skill = (root / "SKILL.md").read_text(encoding="utf-8")
    if "references/" in skill and re.search(r"references/[^)\s`]*_zh_cn\.md", skill):
        errors.append("SKILL.md must not reference _zh_cn references")

    skill_zh = (root / "SKILL_zh_cn.md").read_text(encoding="utf-8")
    for match in re.findall(r"references/[^)\s`]+\.md", skill_zh):
        if not match.endswith(ZH_SUFFIX):
            errors.append(f"SKILL_zh_cn.md references an English file: {match}")

    openai_yaml = (root / "agents/openai.yaml").read_text(encoding="utf-8")
    short_description = re.search(
        r'^\s*short_description:\s*["\'](.+)["\']\s*$', openai_yaml, re.MULTILINE
    )
    if not short_description:
        errors.append("agents/openai.yaml is missing short_description")
    elif " | " not in short_description.group(1):
        errors.append("agents/openai.yaml short_description must use 'English | 中文' format")

    if errors:
        print("Multilingual documentation validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print("Multilingual documentation validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

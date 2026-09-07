#!/usr/bin/env python3
"""Validate bilingual Markdown structure and language-link isolation."""

from __future__ import annotations

import re
import sys
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
ZH_SUFFIX = "_zh_cn.md"
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")

PAIR_ROOTS = [Path("README.md"), Path("SKILL.md"), Path("AGENTS.md"), Path("MULTI_LINGUAL.md")]


def zh_peer(path: PurePosixPath) -> PurePosixPath:
    return path.with_name(f"{path.stem}_zh_cn.md")


def en_peer(path: PurePosixPath) -> PurePosixPath:
    return path.with_name(path.name.removesuffix(ZH_SUFFIX) + ".md")


def normalize_target(source: PurePosixPath, raw: str) -> PurePosixPath | None:
    target = raw.split("#", 1)[0].split("?", 1)[0]
    if not target or "://" in target or target.startswith("mailto:") or not target.endswith(".md"):
        return None
    return PurePosixPath(source.parent, target)


def main() -> int:
    errors: list[str] = []

    english_docs = [PurePosixPath(p.as_posix()) for p in PAIR_ROOTS]
    english_docs += [PurePosixPath(p.relative_to(ROOT).as_posix()) for p in sorted((ROOT / "references").glob("*.md")) if not p.name.endswith(ZH_SUFFIX)]

    bilingual_english = [p for p in english_docs if (ROOT / p).exists()]
    bilingual_set = set(bilingual_english)

    for english in bilingual_english:
        chinese = zh_peer(english)
        if not (ROOT / chinese).exists():
            errors.append(f"missing Chinese mirror: {chinese} for {english}")

    paired_root_zh = {zh_peer(PurePosixPath(p.as_posix())).name for p in PAIR_ROOTS}
    for chinese_path in [p for p in ROOT.rglob(f"*{ZH_SUFFIX}") if ".git" not in p.parts]:
        chinese = PurePosixPath(chinese_path.relative_to(ROOT).as_posix())
        english = en_peer(chinese)
        if chinese.parent == PurePosixPath("references") or chinese.name in paired_root_zh:
            if not (ROOT / english).exists():
                errors.append(f"missing English canonical file: {english} for {chinese}")

    known_pairs = bilingual_set | {zh_peer(p) for p in bilingual_set}

    for rel in sorted(known_pairs, key=str):
        file_path = ROOT / rel
        if not file_path.exists():
            continue
        text = file_path.read_text(encoding="utf-8")
        source_is_zh = rel.name.endswith(ZH_SUFFIX)
        for raw_target in LINK_RE.findall(text):
            target = normalize_target(rel, raw_target)
            if target is None:
                continue
            target_is_zh = target.name.endswith(ZH_SUFFIX)
            counterpart = en_peer(rel) if source_is_zh else zh_peer(rel)
            if source_is_zh != target_is_zh and target != counterpart:
                errors.append(f"cross-language Markdown link: {rel} -> {raw_target}")

    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    if "MULTI_LINGUAL.md" not in agents or "MULTI_LINGUAL_zh_cn.md" in agents:
        errors.append("AGENTS.md must reference only MULTI_LINGUAL.md")

    agents_zh = (ROOT / "AGENTS_zh_cn.md").read_text(encoding="utf-8")
    if "MULTI_LINGUAL_zh_cn.md" not in agents_zh:
        errors.append("AGENTS_zh_cn.md must reference MULTI_LINGUAL_zh_cn.md")

    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    if "references/" in skill and re.search(r"references/[^)\s`]*_zh_cn\.md", skill):
        errors.append("SKILL.md must not reference _zh_cn runtime references")

    skill_zh = (ROOT / "SKILL_zh_cn.md").read_text(encoding="utf-8")
    for match in re.findall(r"references/[^)\s`]+\.md", skill_zh):
        if not match.endswith(ZH_SUFFIX):
            errors.append(f"SKILL_zh_cn.md references English runtime file: {match}")

    openai_yaml = (ROOT / "agents/openai.yaml").read_text(encoding="utf-8")
    short_description = re.search(r'^\s*short_description:\s*["\'](.+)["\']\s*$', openai_yaml, re.MULTILINE)
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

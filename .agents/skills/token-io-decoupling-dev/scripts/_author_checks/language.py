"""文档镜像与跨语言链接检查。"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from pathlib import PurePosixPath
from typing import Any

from .constants import (
    _LINK_RE,
    _MULTILINGUAL_FENCE_RE,
    _PAIR_ROOT_SET,
    _PAIR_ROOT_ZH_NAMES,
    PAIR_ROOTS,
    ZH_SUFFIX,
)
from .findings import _finding
from .links import normalize_multilingual_target
from .paths import counterpart, is_bilingual_document, mirror_path


def multilingual_mirror_issues(
    markdown_paths: Iterable[str],
    path_present: Callable[[str], bool | None],
) -> list[str]:
    """Mirror existence checks shared by the standalone CLI and candidate preflight."""
    paths = list(dict.fromkeys(markdown_paths))
    english_paths = list(PAIR_ROOTS)
    english_paths.extend(
        path
        for path in paths
        if path.startswith("instruction-compiler/sources/skill/references/")
        and not path.endswith(ZH_SUFFIX)
        and path not in _PAIR_ROOT_SET
    )
    issues: list[str] = []
    for english in english_paths:
        if path_present(english) is False:
            continue
        chinese = mirror_path(english)
        present = path_present(chinese)
        if present is False:
            issues.append(f"missing Chinese mirror: {chinese} for {english}")
    for chinese in (path for path in paths if path.endswith(ZH_SUFFIX)):
        if not (
            chinese.startswith("instruction-compiler/sources/skill/references/")
            or PurePosixPath(chinese).name in _PAIR_ROOT_ZH_NAMES
        ):
            continue
        english = mirror_path(chinese)
        present = path_present(english)
        if present is False:
            issues.append(f"missing English canonical file: {english} for {chinese}")
    return issues


def multilingual_cross_language_issues(documents: Mapping[str, str]) -> list[str]:
    """Return exact cross-language messages used by the standalone multilingual checker."""
    issues: list[str] = []
    for source_text, content in sorted(documents.items()):
        source = PurePosixPath(source_text)
        source_is_zh = source.name.endswith(ZH_SUFFIX)
        for _label, raw_target in _LINK_RE.findall(_MULTILINGUAL_FENCE_RE.sub("", content)):
            target = normalize_multilingual_target(source, raw_target)
            if target is None:
                continue
            target_is_zh = target.name.endswith(ZH_SUFFIX)
            if source_is_zh != target_is_zh and target != counterpart(source):
                issues.append(f"cross-language Markdown link: {source} -> {raw_target}")
    return issues


def candidate_mirror_finding(
    path: str,
    path_present: Callable[[str], bool | None],
    *,
    operation: str = "create",
) -> dict[str, Any]:
    if not is_bilingual_document(path):
        return _finding(
            "bilingual_mirror",
            "not_applicable",
            path,
            None,
            "path is outside the bilingual document set",
        )
    peer = mirror_path(path)
    present = path_present(peer)
    if present is None:
        return _finding(
            "bilingual_mirror",
            "unknown",
            path,
            None,
            "required mirror could not be safely verified",
            target_path=peer,
            evidence_missing=["safe UTF-8 read of the required bilingual mirror"],
        )
    if operation == "delete":
        if present:
            return _finding(
                "bilingual_mirror",
                "fail",
                path,
                None,
                "deleting this candidate would leave an orphaned bilingual mirror",
                target_path=peer,
                reason_code="bilingual_mirror_would_be_orphaned",
            )
        return _finding(
            "bilingual_mirror",
            "pass",
            path,
            None,
            "candidate and its mirror will both be absent after deletion",
            target_path=peer,
        )
    if present:
        return _finding(
            "bilingual_mirror",
            "pass",
            path,
            None,
            "same-language mirror exists",
            target_path=peer,
        )
    return _finding(
        "bilingual_mirror",
        "fail",
        path,
        None,
        "required same-language mirror is missing",
        target_path=peer,
    )

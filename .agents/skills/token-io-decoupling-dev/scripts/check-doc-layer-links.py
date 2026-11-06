#!/usr/bin/env python3
"""Validate Markdown dependency direction between Skill document layers."""

from __future__ import annotations

import re
import sys
from pathlib import Path, PurePosixPath

from markdown_discovery import discover_markdown
from compliance_core_loader import load_compliance_core

_COMPLIANCE_CORE = load_compliance_core()

ROOT = Path(__file__).resolve().parents[4]
LINK_RE = _COMPLIANCE_CORE._LINK_RE
INLINE_CODE_SPAN_RE = _COMPLIANCE_CORE._INLINE_CODE_RE
ROUTE_COORDINATE_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?:SM|MM|ER|SR|WD|SE|DE|VR|DOC|DA|S|M)[0-9]{2}(?![A-Za-z0-9_])"
)
LANGUAGE_SWITCH_LABELS = _COMPLIANCE_CORE._LANGUAGE_SWITCH_LABELS
NAVIGATION_MODULES = set(_COMPLIANCE_CORE._MODULES)


def layer(path: PurePosixPath) -> str:
    return _COMPLIANCE_CORE.path_layer(path)


def language(path: PurePosixPath) -> str:
    return _COMPLIANCE_CORE.path_language(path)


def is_language_switch(label: str) -> bool:
    return _COMPLIANCE_CORE.is_language_switch(label)


def is_navigation_document(path: PurePosixPath) -> bool:
    return _COMPLIANCE_CORE.is_navigation_document(path)


def counterpart(path: PurePosixPath) -> PurePosixPath:
    return _COMPLIANCE_CORE.counterpart(path)


def allowed(source: str, target: str, is_navigation: bool, source_path: PurePosixPath | None = None,
            target_path: PurePosixPath | None = None) -> bool:
    return _COMPLIANCE_CORE.allowed_link(
        source, target, is_navigation, source_path, target_path
    )


def iter_links(path: Path):
    grouped: dict[int, list[tuple[str, str]]] = {}
    for line_number, label, target in _COMPLIANCE_CORE.links_in_markdown(
        path.read_text(encoding="utf-8")
    ):
        grouped.setdefault(line_number, []).append((label, target))
    for line_number in sorted(grouped):
        yield line_number, grouped[line_number]


def from_line(line: str):
    return [(label, target) for _line, label, target in _COMPLIANCE_CORE.links_in_markdown(line)]


def iter_route_coordinates(path: Path):
    """Yield every concrete route coordinate in a Layer-03 Markdown file."""
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        for match in ROUTE_COORDINATE_RE.finditer(line):
            yield line_number, match.group(0)


def main(root: Path | None = None) -> int:
    root = Path(root or ROOT).absolute()
    errors: list[str] = []
    markdown_files = sorted(
        PurePosixPath(path.relative_to(root).as_posix()) for path in discover_markdown(root)
    )
    documents: dict[str, str] = {}

    for source in markdown_files:
        source_path = root / source
        content = source_path.read_text(encoding="utf-8")
        documents[source.as_posix()] = content
        if layer(source) == "layer-03":
            for line_number, coordinate in iter_route_coordinates(source_path):
                errors.append(
                    f"Layer-03 route coordinate dependency: {source}:{line_number} -> {coordinate}"
                )

    def target_present(target: str) -> bool:
        candidate = root
        for part in PurePosixPath(target).parts:
            candidate = candidate / part
            if candidate.is_symlink():
                return False
        return candidate.is_file()

    errors.extend(
        _COMPLIANCE_CORE.document_link_issues(documents, target_present=target_present)
    )
    if errors:
        print("Document layer validation failed:", file=sys.stderr)
        print("\n".join(f"- {error}" for error in errors), file=sys.stderr)
        return 1
    print(f"Document layer validation passed ({len(markdown_files)} Markdown files).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Pure-standard-library compliance rules shared by runtime and offline checkers."""

from __future__ import annotations

import posixpath
import re
from collections.abc import Callable, Iterable, Mapping, Sequence
from pathlib import PurePosixPath
from typing import Any

MAX_CANDIDATES = 64
MAX_PATH_CHARS = 512
MAX_FILE_CHARS = 131_072
MAX_BATCH_UTF8_BYTES = 524_288
MAX_DIRECT_TARGETS = 256
MAX_OUTPUT_CHECKS = 512
MAX_CHECK_MESSAGE_CHARS = 512

POLICY_VERSION = 1
POLICY_SCOPES = frozenset({"skill_maintenance", "generic_project"})
OPERATIONS = frozenset({"create", "replace", "delete"})
STATUS_VALUES = frozenset({"pass", "fail", "unknown", "not_applicable"})

PAIR_ROOTS = (
    "README.md",
    "docs/skill/SKILL.md",
    "AGENTS.md",
    "MULTI_LINGUAL.md",
    "docs/skill/workflows/coding.md",
    "docs/skill/WORKFLOW_ARCHITECTURE.md",
    "EXTERNAL_REFERENCES.md",
    "mcp/AGENTS.md",
    "mcp/CODEX_CALLER_CONTEXT.md",
    "mcp/CANDIDATE_COMPLIANCE.md",
    "mcp/OUTPUT_MATERIALIZATION.md",
    "mcp/DEVELOPMENT.md",
    "mcp/OPTIMIZATION_BENCHMARK.md",
    "mcp/TASK_PLAN_TOOLS.md",
    "mcp/WORKFLOW_ROUTING.md",
)
_PAIR_ROOT_SET = frozenset(PAIR_ROOTS)
ZH_SUFFIX = "_zh_cn.md"
_PAIR_ROOT_ZH_NAMES = frozenset(f"{PurePosixPath(path).stem}{ZH_SUFFIX}" for path in PAIR_ROOTS)

LAYER01_HEADINGS = {
    "en": (
        "General rules",
        "Codex CLI / ChatGPT Desktop optimizations",
        "Claude Code CLI / Claude Desktop optimizations",
    ),
    "zh": (
        "通用规范",
        "Codex CLI / ChatGPT Desktop 特别优化指令",
        "Claude Code CLI / Claude Desktop 特别优化指令",
    ),
}
LAYER01_NAVIGATION = {"en": "Related concepts", "zh": "相关概念"}
_HEADING_RE = re.compile(r"^## (.+?)\s*$")
_FENCE_RE = re.compile(r"^( {0,3})(`{3,}|~{3,})(.*)$")

_LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")
_INLINE_CODE_RE = re.compile(r"(`+)(.*?)\1")


def _advance_fence(line: str, fence_char: str = "", fence_width: int = 0) -> tuple[str, int]:
    """Update a CommonMark fenced-code state from one line."""
    match = _FENCE_RE.match(line.rstrip("\r\n"))
    if match is None:
        return fence_char, fence_width
    marker = match.group(2)
    info = match.group(3)
    char = marker[0]
    width = len(marker)
    if fence_char:
        if char == fence_char and width >= fence_width and not info.strip(" \t"):
            return "", 0
        return fence_char, fence_width
    if char == "`" and "`" in info:
        return "", 0
    return char, width


_MULTILINGUAL_FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
_LANGUAGE_SWITCH_LABELS = {"english", "简体中文"}

_MODULES = (
    "entry-readiness",
    "session-readiness",
    "work-definition",
    "single-execution",
    "delegated-execution",
    "verification-repair",
    "documentation",
    "delivery-acceptance",
)
_ROUTE_MODULES = {
    "coding-single-agent": (
        "entry-readiness",
        "session-readiness",
        "work-definition",
        "single-execution",
        "verification-repair",
        "documentation",
        "delivery-acceptance",
    ),
    "coding-multi-agent": (
        "entry-readiness",
        "session-readiness",
        "work-definition",
        "delegated-execution",
        "verification-repair",
        "documentation",
        "delivery-acceptance",
    ),
}


class ComplianceInputError(ValueError):
    """Raised when a caller-supplied candidate envelope exceeds its contract."""


def validate_relative_posix_path(value: Any) -> str:
    """Return a canonical repo-relative POSIX path or reject it without OS resolution."""
    if not isinstance(value, str) or not value or len(value) > MAX_PATH_CHARS:
        raise ComplianceInputError("candidate_path_invalid_length")
    if "\\" in value or "\x00" in value or value.startswith("/"):
        raise ComplianceInputError("candidate_path_not_relative_posix")
    parts = value.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise ComplianceInputError("candidate_path_not_canonical")
    path = PurePosixPath(value)
    if path.is_absolute() or path.as_posix() != value:
        raise ComplianceInputError("candidate_path_not_canonical")
    return value


def validate_candidate_list(candidates: Any) -> list[dict[str, Any]]:
    """Validate the bounded, provider-neutral candidate payload used by both callers."""
    if not isinstance(candidates, Sequence) or isinstance(candidates, (str, bytes)):
        raise ComplianceInputError("candidates_must_be_a_list")
    if not 1 <= len(candidates) <= MAX_CANDIDATES:
        raise ComplianceInputError("candidate_count_out_of_range")

    normalized: list[dict[str, Any]] = []
    paths: set[str] = set()
    batch_bytes = 0
    for candidate in candidates:
        if not isinstance(candidate, Mapping):
            raise ComplianceInputError("candidate_shape_invalid")
        path = validate_relative_posix_path(candidate.get("path"))
        if path in paths:
            raise ComplianceInputError("candidate_paths_must_be_unique")
        paths.add(path)
        operation = candidate.get("operation")
        baseline = candidate.get("baseline")
        content = candidate.get("content")
        if operation not in OPERATIONS or not isinstance(baseline, Mapping):
            raise ComplianceInputError("candidate_operation_or_baseline_invalid")
        state = baseline.get("state")
        digest = baseline.get("value")
        if operation == "create":
            if state != "absent" or digest is not None:
                raise ComplianceInputError("create_requires_absent_baseline")
        elif (
            state != "sha256"
            or not isinstance(digest, str)
            or not re.fullmatch(r"[0-9a-f]{64}", digest)
        ):
            raise ComplianceInputError("replace_delete_require_sha256_baseline")
        if operation == "delete":
            if content is not None:
                raise ComplianceInputError("delete_must_not_include_content")
        else:
            if not isinstance(content, str):
                raise ComplianceInputError("create_replace_require_content")
            if len(content) > MAX_FILE_CHARS:
                raise ComplianceInputError("candidate_content_char_limit_exceeded")
            try:
                encoded = content.encode("utf-8", errors="strict")
            except UnicodeEncodeError as exc:
                raise ComplianceInputError("candidate_content_not_valid_utf8") from exc
            batch_bytes += len(encoded)
            if batch_bytes > MAX_BATCH_UTF8_BYTES:
                raise ComplianceInputError("candidate_batch_byte_limit_exceeded")
        normalized.append(
            {
                "path": path,
                "operation": operation,
                "baseline": {"state": state, **({"value": digest} if digest is not None else {})},
                "content": content,
            }
        )
    return normalized


def path_layer(path: PurePosixPath) -> str:
    parts = path.parts
    if parts[:2] == ("docs", "skill"):
        parts = parts[2:]
    if parts[:3] == ("references", "coding", "layer-01-fundamental-concepts"):
        return "layer-01"
    if parts[:3] == ("references", "coding", "layer-02-workflow-concepts"):
        return "layer-02"
    if parts[:3] == ("references", "coding", "layer-03-workflow-checkpoints"):
        return "layer-03"
    if parts[:3] == ("references", "coding", "layer-04-workflows"):
        return "layer-04-module" if len(parts) > 3 and parts[3] == "modules" else "layer-04-route"
    if parts[:2] == ("references", "share"):
        return "shared-protocols"
    if parts and parts[0] == "references":
        return "references"
    if parts[:2] == ("workflows", "checkpoint"):
        return "checkpoint"
    if parts[:2] == ("workflows", "exist-workflow"):
        return "exist-workflow"
    if str(path) in {"docs/skill/workflows/coding.md", "docs/skill/workflows/coding_zh_cn.md"}:
        return "coding-selector"
    return "entry"


def path_language(path: PurePosixPath) -> str:
    return "zh" if path.parts[:2] == ("docs", "zh-cn") or path.name.endswith(ZH_SUFFIX) else "en"


def is_language_switch(label: str) -> bool:
    return label.strip().casefold() in _LANGUAGE_SWITCH_LABELS


def is_navigation_document(path: PurePosixPath) -> bool:
    return path.name in {"README.md", "README_zh_cn.md", "INDEX.md", "INDEX_zh_cn.md"}


def counterpart(path: PurePosixPath) -> PurePosixPath:
    if path.parts[:2] == ("docs", "zh-cn"):
        return PurePosixPath("docs", path.name)
    if path == PurePosixPath("docs/index.md"):
        return PurePosixPath("docs/zh-cn/index.md")
    if path.name.endswith(ZH_SUFFIX):
        return path.with_name(path.name.removesuffix(ZH_SUFFIX) + ".md")
    return path.with_name(path.stem + ZH_SUFFIX)


def allowed_link(
    source: str,
    target: str,
    is_navigation: bool,
    source_path: PurePosixPath | None = None,
    target_path: PurePosixPath | None = None,
) -> bool:
    same_layer_navigation = is_navigation and source == target
    if source in {"references", "layer-01"}:
        return same_layer_navigation or target == "layer-01"
    if source in {"checkpoint", "layer-02"}:
        return same_layer_navigation or target in {"references", "layer-01"}
    if source in {"exist-workflow", "layer-03"}:
        return same_layer_navigation or target in {"shared-protocols", "layer-01", "layer-02"}
    if source == "layer-04-route":
        module_root = PurePosixPath("docs/skill/references/coding/layer-04-workflows/modules")
        canonical_modules = {
            module_root / f"{module}{suffix}.md" for module in _MODULES for suffix in ("", "_zh_cn")
        }
        if is_navigation and target == "layer-04-module" and target_path is not None:
            return target_path.parent == module_root and target_path in canonical_modules
        if same_layer_navigation or target in {
            "shared-protocols",
            "layer-01",
            "layer-02",
            "layer-03",
        }:
            return True
        if target != "layer-04-module" or source_path is None or target_path is None:
            return False
        route_root = PurePosixPath("docs/skill/references/coding/layer-04-workflows")
        route_name = source_path.stem.removesuffix("_zh_cn")
        canonical_route = route_root / f"{route_name}.md"
        if source_path not in {canonical_route, route_root / f"{route_name}_zh_cn.md"}:
            return False
        if target_path.parent != module_root or target_path not in canonical_modules:
            return False
        return target_path.stem.removesuffix("_zh_cn") in _ROUTE_MODULES.get(route_name, ())
    if source in {"layer-04-module", "layer-04"}:
        return same_layer_navigation or target in {
            "shared-protocols",
            "layer-01",
            "layer-02",
            "layer-03",
        }
    if source == "coding-selector":
        return is_navigation or target in {
            "exist-workflow",
            "layer-01",
            "layer-02",
            "layer-03",
            "layer-04",
            "layer-04-route",
            "layer-04-module",
        }
    return True


def normalize_markdown_target(source: PurePosixPath, raw: str) -> str | None:
    target = raw.split("#", 1)[0].split("?", 1)[0]
    if (
        not target
        or "://" in target
        or target.startswith(("mailto:", "{{"))
        or not target.endswith(".md")
    ):
        return None
    if target.startswith("/") or "\\" in target or "\x00" in target:
        return ""
    normalized = posixpath.normpath(posixpath.join(source.parent.as_posix(), target))
    if normalized in {".", ".."} or normalized.startswith("../") or normalized.startswith("/"):
        return ""
    try:
        return validate_relative_posix_path(normalized)
    except ComplianceInputError:
        return ""


def normalize_multilingual_target(source: PurePosixPath, raw: str) -> PurePosixPath | None:
    """Preserve the standalone multilingual validator's anchor/path interpretation."""
    target = raw.split("#", 1)[0].split("?", 1)[0]
    if not target or "://" in target or target.startswith("mailto:") or not target.endswith(".md"):
        return None
    return PurePosixPath(source.parent, target)


def links_in_markdown(content: str) -> Iterable[tuple[int, str, str]]:
    fenced = False
    for line_number, line in enumerate(content.splitlines(), 1):
        if line.strip().startswith("```"):
            fenced = not fenced
            continue
        if fenced:
            continue
        for label, raw_target in _LINK_RE.findall(_INLINE_CODE_RE.sub("", line)):
            yield line_number, label, raw_target


def document_link_findings(
    path: str,
    content: str,
    target_present: Callable[[str], bool | None],
) -> list[dict[str, Any]]:
    """Return bounded-by-caller local link findings for one source document."""
    source = PurePosixPath(path)
    source_layer = path_layer(source)
    source_language = path_language(source)
    findings: list[dict[str, Any]] = []
    for line_number, label, raw_target in links_in_markdown(content):
        target_text = raw_target.split("#", 1)[0].split("?", 1)[0]
        if (
            not target_text
            or "://" in target_text
            or target_text.startswith(("mailto:", "{{"))
            or not target_text.endswith(".md")
        ):
            continue
        target = normalize_markdown_target(source, raw_target)
        if target == "":
            findings.append(
                _finding(
                    "markdown_link_target",
                    "fail",
                    path,
                    line_number,
                    "link target escapes the trusted repository root or is not a canonical "
                    "relative path",
                )
            )
            continue
        assert target is not None
        target_path = PurePosixPath(target)
        target_language = path_language(target_path)
        is_mirror = target_path == counterpart(source)
        if target_language != source_language and not (is_language_switch(label) and is_mirror):
            findings.append(
                _finding(
                    "markdown_link_language",
                    "fail",
                    path,
                    line_number,
                    "cross-language Markdown link is not the visible language switch",
                    target_path=target,
                )
            )
        target_layer = path_layer(target_path)
        is_navigation = (
            is_mirror
            or (target_path == source and is_language_switch(label))
            or is_navigation_document(source)
        )
        if not allowed_link(source_layer, target_layer, is_navigation, source, target_path):
            findings.append(
                _finding(
                    "markdown_link_layer",
                    "fail",
                    path,
                    line_number,
                    f"layer dependency is not allowed from {source_layer} to {target_layer}",
                    target_path=target,
                )
            )
        present = target_present(target)
        if present is False:
            findings.append(
                _finding(
                    "markdown_link_target",
                    "fail",
                    path,
                    line_number,
                    "local Markdown link target does not exist in the candidate overlay or "
                    "trusted root",
                    target_path=target,
                )
            )
        elif present is None:
            findings.append(
                _finding(
                    "markdown_link_target",
                    "unknown",
                    path,
                    line_number,
                    "local Markdown link target could not be safely verified",
                    target_path=target,
                    evidence_missing=[
                        "safe UTF-8 read of the linked Markdown target within configured limits"
                    ],
                )
            )
    return findings


def document_link_issues(documents: Mapping[str, str]) -> list[str]:
    """CLI-compatible messages for the full repository Markdown link validator."""
    present_paths = set(documents)
    issues: list[str] = []
    for path, content in sorted(documents.items()):
        source = PurePosixPath(path)
        source_layer = path_layer(source)
        source_language = path_language(source)
        for line_number, label, raw_target in links_in_markdown(content):
            target_text = raw_target.split("#", 1)[0].split("?", 1)[0]
            if (
                not target_text
                or "://" in target_text
                or target_text.startswith(("mailto:", "{{"))
                or not target_text.endswith(".md")
            ):
                continue
            target = normalize_markdown_target(source, raw_target)
            if target == "":
                issues.append(f"target escapes repository: {path}:{line_number} -> {target_text}")
                continue
            assert target is not None
            if target not in present_paths:
                issues.append(f"missing local target: {path}:{line_number} -> {target}")
                continue
            target_path = PurePosixPath(target)
            target_language = path_language(target_path)
            is_mirror = target_path == counterpart(source)
            if target_language != source_language and not (is_language_switch(label) and is_mirror):
                issues.append(f"cross-language dependency: {path}:{line_number} -> {target}")
            target_layer = path_layer(target_path)
            is_navigation = (
                is_mirror
                or (target_path == source and is_language_switch(label))
                or is_navigation_document(source)
            )
            if not allowed_link(source_layer, target_layer, is_navigation, source, target_path):
                issues.append(
                    f"layer violation: {path}:{line_number} ({source_layer}) -> "
                    f"{target} ({target_layer})"
                )
    return issues


def is_bilingual_document(path: str) -> bool:
    return (
        path in _PAIR_ROOT_SET
        or mirror_path(path) in _PAIR_ROOT_SET
        or path.startswith("docs/skill/references/")
    )


def mirror_path(path: str) -> str:
    pure = PurePosixPath(path)
    if pure.parts[:2] == ("docs", "zh-cn"):
        return PurePosixPath("docs", pure.name).as_posix()
    if path == "docs/index.md":
        return "docs/zh-cn/index.md"
    if pure.name.endswith(ZH_SUFFIX):
        return pure.with_name(pure.name.removesuffix(ZH_SUFFIX) + ".md").as_posix()
    return pure.with_name(pure.stem + ZH_SUFFIX).as_posix()


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
        if path.startswith("docs/skill/references/")
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
            chinese.startswith("docs/skill/references/")
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


def top_level_sections(content: str) -> list[tuple[int, str, int]]:
    """Return line number, heading text, and content offset outside fenced code."""
    sections: list[tuple[int, str, int]] = []
    fence_char = ""
    fence_width = 0
    offset = 0
    for number, line in enumerate(content.splitlines(keepends=True), 1):
        previous_fence_char = fence_char
        fence_char, fence_width = _advance_fence(line, fence_char, fence_width)
        if previous_fence_char or fence_char:
            offset += len(line)
            continue
        if match := _HEADING_RE.match(line.rstrip("\r\n")):
            sections.append((number, match.group(1), offset))
        offset += len(line)
    return sections


def layer01_section_issues(path: str, content: str) -> list[str]:
    relative = path
    language = "zh" if PurePosixPath(path).name.endswith(ZH_SUFFIX) else "en"
    expected = LAYER01_HEADINGS[language]
    sections = top_level_sections(content)
    errors: list[str] = []
    for heading in expected:
        occurrences = [(line, offset) for line, found, offset in sections if found == heading]
        if not occurrences:
            errors.append(f"{relative}: 缺少必需标题 `## {heading}`")
        elif len(occurrences) > 1:
            lines = ", ".join(str(line) for line, _ in occurrences)
            errors.append(f"{relative}: 标题 `## {heading}` 重复出现于第 {lines} 行")
    positions = [
        next((i for i, (_, found, _) in enumerate(sections) if found == heading), None)
        for heading in expected
    ]
    known_positions = [position for position in positions if position is not None]
    if len(known_positions) == len(positions) and known_positions != sorted(known_positions):
        errors.append(f"{relative}: 三个必需标题顺序错误；应为通用规范 → Codex → Claude Code")
    allowed = {*expected, LAYER01_NAVIGATION[language]}
    for line, heading, _offset in sections:
        if heading not in allowed:
            errors.append(
                f"{relative}:{line}: 非模块二级标题 `## {heading}`；概念子主题应使用 `###`"
            )
    for heading in expected:
        match = next(
            (
                (index, offset)
                for index, (_, found, offset) in enumerate(sections)
                if found == heading
            ),
            None,
        )
        if match is None:
            continue
        index, offset = match
        line_end = content.find("\n", offset)
        start = line_end + 1 if line_end >= 0 else len(content)
        end = sections[index + 1][2] if index + 1 < len(sections) else len(content)
        if not content[start:end].strip():
            errors.append(
                f"{relative}:{sections[index][0]}: 模块 `## {heading}` 为空；"
                "无特别优化时也须明确写明没有"
            )
    navigation = next(
        (
            index
            for index, (_, heading, _) in enumerate(sections)
            if heading == LAYER01_NAVIGATION[language]
        ),
        None,
    )
    if navigation is not None and positions[-1] is not None and navigation < positions[-1]:
        errors.append(f"{relative}: 导航章节必须位于三个内容模块之后")
    return errors


def is_layer01_path(path: str) -> bool:
    parts = PurePosixPath(path).parts
    if parts[:2] == ("docs", "skill"):
        parts = parts[2:]
    return parts[:3] == ("references", "coding", "layer-01-fundamental-concepts")


def evaluate_candidate_checks(
    policy_scope: str,
    candidates: Sequence[Mapping[str, Any]],
    baseline_checks: Sequence[Mapping[str, Any]],
    path_present: Callable[[str], bool | None],
    *,
    allowed_scope: bool,
    direct_targets_read: int = 0,
    target_limit_exceeded: bool = False,
) -> dict[str, Any]:
    """Evaluate candidate overlays and return compact checks without changing disk state."""
    normalized = validate_candidate_list(candidates)
    if policy_scope not in POLICY_SCOPES:
        raise ComplianceInputError("policy_scope_invalid")
    checks = [dict(item) for item in baseline_checks]
    present_overlay: dict[str, str] = {}
    deleted: set[str] = set()
    for candidate in normalized:
        if candidate["operation"] == "delete":
            deleted.add(candidate["path"])
        else:
            present_overlay[candidate["path"]] = candidate["content"]

    def overlay_presence(path: str) -> bool | None:
        if path in deleted:
            return False
        if path in present_overlay:
            return True
        return path_present(path)

    if allowed_scope:
        if policy_scope == "generic_project":
            for candidate in normalized:
                for rule in (
                    "bilingual_mirror",
                    "markdown_link_language",
                    "markdown_link_layer",
                    "markdown_link_target",
                    "layer01_structure",
                ):
                    checks.append(
                        _finding(
                            rule,
                            "not_applicable",
                            candidate["path"],
                            None,
                            "Skill-maintenance rules do not apply to generic project scope",
                        )
                    )
        else:
            for candidate in normalized:
                path = candidate["path"]
                operation = candidate["operation"]
                checks.append(candidate_mirror_finding(path, overlay_presence, operation=operation))
                if operation == "delete" or not path.endswith(".md"):
                    for rule in (
                        "markdown_link_language",
                        "markdown_link_layer",
                        "markdown_link_target",
                    ):
                        checks.append(
                            _finding(
                                rule,
                                "not_applicable",
                                path,
                                None,
                                "candidate has no Markdown content to inspect",
                            )
                        )
                else:
                    findings = document_link_findings(path, candidate["content"], overlay_presence)
                    for rule in (
                        "markdown_link_language",
                        "markdown_link_layer",
                        "markdown_link_target",
                    ):
                        if rule == "markdown_link_language" and not is_bilingual_document(path):
                            checks.append(
                                _finding(
                                    rule,
                                    "not_applicable",
                                    path,
                                    None,
                                    "language-isolation check covers the configured bilingual "
                                    "document set",
                                )
                            )
                            continue
                        rule_findings = [item for item in findings if item["rule_id"] == rule]
                        if rule_findings:
                            checks.extend(rule_findings)
                        else:
                            checks.append(
                                _finding(
                                    rule,
                                    "pass",
                                    path,
                                    None,
                                    "candidate links passed this local check",
                                )
                            )
                if operation == "delete" or not path.endswith(".md"):
                    checks.append(
                        _finding(
                            "layer01_structure",
                            "not_applicable",
                            path,
                            None,
                            "candidate has no Markdown content to inspect",
                        )
                    )
                elif is_layer01_path(path):
                    errors = layer01_section_issues(path, candidate["content"])
                    if errors:
                        for error in errors:
                            checks.append(_finding("layer01_structure", "fail", path, None, error))
                    else:
                        checks.append(
                            _finding(
                                "layer01_structure",
                                "pass",
                                path,
                                None,
                                "Layer-01 required sections and order are present",
                            )
                        )
                else:
                    checks.append(
                        _finding(
                            "layer01_structure",
                            "not_applicable",
                            path,
                            None,
                            "candidate is outside the Layer-01 owner directory",
                        )
                    )
    else:
        for candidate in normalized:
            checks.append(
                _finding(
                    "policy_scope",
                    "unknown",
                    candidate["path"],
                    None,
                    "requested scope is not enabled by the operator-configured service",
                    reason_code="policy_scope_not_allowed",
                    evidence_missing=["operator allowlist entry for the requested policy scope"],
                )
            )

    if target_limit_exceeded:
        checks.append(
            _finding(
                "direct_target_budget",
                "unknown",
                None,
                None,
                "direct link and mirror target read budget was exceeded; remaining targets "
                "were not probed",
                reason_code="direct_target_budget_exceeded",
                evidence_missing=[
                    "safe reads for targets beyond the configured direct-target budget"
                ],
            )
        )
    return build_result(
        policy_scope,
        checks,
        direct_targets_read=direct_targets_read,
        target_limit_exceeded=target_limit_exceeded,
    )


def build_result(
    policy_scope: str,
    checks: Sequence[Mapping[str, Any]],
    *,
    direct_targets_read: int = 0,
    target_limit_exceeded: bool = False,
) -> dict[str, Any]:
    all_statuses = [item.get("status") for item in checks if item.get("status") != "not_applicable"]
    bounded = [dict(item) for item in checks[:MAX_OUTPUT_CHECKS]]
    if len(checks) > MAX_OUTPUT_CHECKS:
        bounded[-1] = _finding(
            "output_check_budget",
            "unknown",
            None,
            None,
            "check output budget was exceeded; additional checks were omitted",
            reason_code="output_check_budget_exceeded",
            evidence_missing=["checks omitted after the configured output-check budget"],
        )
    status = (
        "fail"
        if "fail" in all_statuses
        else "unknown"
        if "unknown" in all_statuses
        else "pass"
        if "pass" in all_statuses
        else "not_applicable"
    )
    return {
        "status": status,
        "policy_scope": policy_scope,
        "policy_version": POLICY_VERSION,
        "checks": bounded,
        "not_evaluated": [
            "reverse inbound-link scans across unchanged documents",
            "semantic equivalence between English and Simplified Chinese mirrors",
            "full repository CI and final integration acceptance",
        ],
        "limits": {
            "max_candidates": MAX_CANDIDATES,
            "max_path_chars": MAX_PATH_CHARS,
            "max_file_chars": MAX_FILE_CHARS,
            "max_batch_utf8_bytes": MAX_BATCH_UTF8_BYTES,
            "max_direct_targets": MAX_DIRECT_TARGETS,
            "direct_targets_read": direct_targets_read,
            "direct_target_limit_exceeded": target_limit_exceeded,
            "max_checks": MAX_OUTPUT_CHECKS,
            "checks_returned": len(bounded),
            "checks_truncated": len(checks) > MAX_OUTPUT_CHECKS,
        },
    }


def _finding(
    rule: str,
    status: str,
    path: str | None,
    line: int | None,
    message: str,
    *,
    target_path: str | None = None,
    reason_code: str | None = None,
    evidence_missing: Sequence[str] | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "rule_id": rule,
        "status": status,
        "path": path,
        "line": line,
        "message": message[:MAX_CHECK_MESSAGE_CHARS],
        "evidence_missing": [
            item[:MAX_CHECK_MESSAGE_CHARS] for item in (evidence_missing or [])[:8]
        ],
    }
    if target_path is not None:
        result["target_path"] = target_path[:MAX_PATH_CHARS]
    if reason_code is not None:
        result["reason_code"] = reason_code
    return result

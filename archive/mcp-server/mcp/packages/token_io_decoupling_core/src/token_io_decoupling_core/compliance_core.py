"""Pure-standard-library compliance rules shared by runtime and offline checkers."""

from __future__ import annotations

import posixpath
import re
from collections.abc import Callable, Iterable, Mapping, Sequence
from pathlib import PurePosixPath
from typing import Any
from urllib.parse import unquote

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
    "skill/SKILL.md",
    "AGENTS.md",
    "docs/DOCUMENTATION_STANDARDS.md",
    "skill/workflows/coding.md",
    "docs/WORKFLOW_ARCHITECTURE.md",
    "docs/EXTERNAL_REFERENCES.md",
    "mcp/AGENTS.md",
    "docs/mcp/CANDIDATE_COMPLIANCE.md",
    "docs/mcp/OUTPUT_MATERIALIZATION.md",
    "docs/mcp/DEVELOPMENT.md",
)
_PAIR_ROOT_SET = frozenset(PAIR_ROOTS)
ZH_SUFFIX = "_zh_cn.md"
_PAIR_ROOT_ZH_NAMES = frozenset(f"{PurePosixPath(path).stem}{ZH_SUFFIX}" for path in PAIR_ROOTS)

LAYER01_HEADINGS = {
    "en": (
        "General rules",
        "Pi Coding Agent optimizations",
    ),
    "zh": (
        "通用规范",
        "Pi Coding Agent 优化指令",
    ),
}
LAYER01_NAVIGATION = {"en": "Related concepts", "zh": "相关概念"}
_HEADING_RE = re.compile(r"^## (.+?)\s*$")
_FENCE_RE = re.compile(r"^( {0,3})(`{3,}|~{3,})(.*)$")

_LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")
_INLINE_CODE_RE = re.compile(r"(`+)(.*?)\1")
_REFERENCE_LINK_RE = re.compile(r"^ {0,3}\[([^\]]+)\]:[ \t]*(<[^>]+>|[^\s]+)")
_EXTERNAL_LINK_RE = re.compile(r"^(?:[a-z][a-z0-9+.-]*:|//)", re.IGNORECASE)


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

_SKILL_LAYERS = {
    ("references", "coding", "layer-01-fundamental-concepts"): "layer-01",
    ("references", "coding", "layer-02-workflow-concepts"): "layer-02",
    ("references", "coding", "layer-03-workflow-checkpoints"): "layer-03",
    ("hooks",): "hook",
    ("workflows",): "workflows",
}
_LAYER_RANK = {layer: index for index, layer in enumerate(_SKILL_LAYERS.values())}

_ROUTE_HOOKS = {
    "coding-single-agent": (
        "entry", "session", "planning", "execution", "verification", "documentation", "delivery",
    ),
    "coding-multi-agent": (
        "entry", "session", "planning", "delegation", "verification", "documentation", "delivery",
    ),
}
_SHARED_ROUTE_HOOKS = {"README", "foundation", "recovery", "repair"}


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
    if parts and parts[0] in {"skill", "rules"}:
        parts = parts[1:]
    if len(parts) == 2 and parts[0] == "workflows" and parts[1] in {
        "coding.yaml", "coding.md", "coding_zh_cn.md",
    }:
        return "coding-selector"
    if parts[:2] == ("workflows", "checkpoint"):
        return "checkpoint"
    if parts[:2] == ("workflows", "exist-workflow"):
        return "exist-workflow"
    for prefix, layer in _SKILL_LAYERS.items():
        if parts[:len(prefix)] == prefix:
            return layer
    if parts[:2] == ("references", "share"):
        return "shared-protocols"
    if parts and parts[0] == "references":
        return "references"
    return "entry"


def is_reverse_dependency(source_layer: str, target_layer: str) -> bool:
    return (
        source_layer in _LAYER_RANK
        and target_layer in _LAYER_RANK
        and _LAYER_RANK[source_layer] < _LAYER_RANK[target_layer]
    )


def reverse_dependency_target(source: PurePosixPath, href: str) -> str | None:
    """识别跨层回链，包括目录链接和带转义的相对路径。"""
    if _EXTERNAL_LINK_RE.match(href):
        return None
    target = unquote(href.split("#", 1)[0].split("?", 1)[0])
    if not target:
        return None
    resolved = posixpath.normpath(posixpath.join(source.parent.as_posix(), target)).lstrip("/")
    if is_reverse_dependency(path_layer(source), path_layer(PurePosixPath(resolved))):
        return resolved
    return None


def path_language(path: PurePosixPath) -> str:
    return "zh"


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
    if is_reverse_dependency(source, target):
        return False
    same_layer_navigation = is_navigation and source == target
    if source in {"references", "layer-01"}:
        return same_layer_navigation or target == "layer-01"
    if source in {"checkpoint", "layer-02"}:
        return same_layer_navigation or target in {"references", "layer-01"}
    if source in {"exist-workflow", "layer-03"}:
        return same_layer_navigation or target in {"shared-protocols", "layer-01", "layer-02"}
    if source == "workflows":
        if same_layer_navigation or target in {
            "shared-protocols",
            "layer-01",
            "layer-02",
            "layer-03",
        }:
            return True
        if target != "hook" or source_path is None or target_path is None:
            return False
        hook_root = PurePosixPath("skill/hooks")
        if target_path.parent != hook_root or target_path.suffix != ".md":
            return False
        route_root = PurePosixPath("skill/workflows")
        if source_path.parent != route_root:
            return False
        if is_navigation:
            return any(target_path.stem in hooks for hooks in _ROUTE_HOOKS.values())
        if source_path.suffix != ".md":
            return False
        route_name = source_path.stem.removesuffix("_zh_cn")
        route_hooks = _ROUTE_HOOKS.get(route_name)
        return route_hooks is not None and (
            target_path.stem in route_hooks or target_path.stem in _SHARED_ROUTE_HOOKS
        )
    if source == "hook":
        return target != "layer-04"
    if source == "layer-04":
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
            "workflows",
            "hook",
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
    fence_char, fence_width = "", 0
    for line_number, line in enumerate(content.splitlines(), 1):
        previous = fence_char
        fence_char, fence_width = _advance_fence(line, fence_char, fence_width)
        if previous or fence_char:
            continue
        line = _INLINE_CODE_RE.sub("", line)
        links = _LINK_RE.findall(line)
        definition = _REFERENCE_LINK_RE.match(line)
        if definition:
            links.append(definition.groups())
        for label, raw in links:
            target = raw.strip()
            if target.startswith("<") and ">" in target:
                target = target[1:target.index(">")]
            elif target:
                target = target.split(maxsplit=1)[0]
            if target:
                yield line_number, label, target


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
        reverse = reverse_dependency_target(source, raw_target)
        if reverse is not None:
            findings.append(_finding(
                "markdown_link_layer", "fail", path, line_number,
                "reverse Skill layer dependency is not allowed", target_path=reverse,
            ))
            continue
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
            reverse = reverse_dependency_target(source, raw_target)
            if reverse is not None:
                issues.append(f"layer violation: {path}:{line_number} -> {reverse} (反向依赖)")
                continue
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
    """中文文档不再要求语言镜像。"""
    return False


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
    """兼容旧入口；中文单一来源没有镜像要求。"""
    return []


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
    expected = ("通用规范", "Pi Coding Agent 优化指令", "相关概念")
    sections = top_level_sections(content)
    errors: list[str] = []
    found = [heading for _line, heading, _offset in sections]
    if found != list(expected):
        errors.append(f"{path}: 二级标题必须唯一且按序为 " + " → ".join(expected))
    for index, (line, heading, offset) in enumerate(sections):
        start = content.find("\n", offset)
        start = len(content) if start < 0 else start + 1
        end = sections[index + 1][2] if index + 1 < len(sections) else len(content)
        if heading in expected and not content[start:end].strip():
            errors.append(f"{path}:{line}: 模块 `## {heading}` 为空")
    return errors


def is_layer01_path(path: str) -> bool:
    parts = PurePosixPath(path).parts
    if parts[:1] == ("skill",):
        parts = parts[1:]
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
            "中文指令的语义准确性与完整性",
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

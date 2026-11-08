"""根据候选覆盖层组合仓库维护政策检查。"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any

from .constants import POLICY_SCOPES
from .findings import _finding, build_result
from .language import candidate_mirror_finding
from .links import document_link_findings
from .paths import is_bilingual_document
from .sections import is_layer01_path, layer01_section_issues
from .validation import ComplianceInputError, validate_candidate_list


def _candidate_link_rule_checks(
    path: str, findings: list[dict[str, Any]], rule: str
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    if rule == "markdown_link_language" and not is_bilingual_document(path):
        checks.append(
            _finding(
                rule,
                "not_applicable",
                path,
                None,
                "language-isolation check covers the configured bilingual document set",
            )
        )
        return checks
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
    return checks


def _candidate_link_checks(
    candidate: Mapping[str, Any], overlay_presence: Callable[[str], bool | None]
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    path = candidate["path"]
    operation = candidate["operation"]
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
            checks.extend(_candidate_link_rule_checks(path, findings, rule))
    return checks


def _candidate_structure_checks(candidate: Mapping[str, Any]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    path = candidate["path"]
    operation = candidate["operation"]
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
    return checks


def _generic_candidate_findings(candidate: Mapping[str, Any]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
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
    return checks


def _candidate_scope_checks(
    policy_scope: str,
    normalized: list[dict[str, Any]],
    overlay_presence: Callable[[str], bool | None],
    allowed_scope: bool,
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    if allowed_scope:
        if policy_scope == "generic_project":
            for candidate in normalized:
                checks.extend(_generic_candidate_findings(candidate))
        else:
            for candidate in normalized:
                path = candidate["path"]
                operation = candidate["operation"]
                checks.append(candidate_mirror_finding(path, overlay_presence, operation=operation))
                checks.extend(_candidate_link_checks(candidate, overlay_presence))
                checks.extend(_candidate_structure_checks(candidate))
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

    return checks


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

    checks.extend(
        _candidate_scope_checks(policy_scope, normalized, overlay_presence, allowed_scope)
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

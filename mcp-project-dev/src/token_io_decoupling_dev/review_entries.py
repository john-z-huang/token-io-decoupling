"""Build non-publishable, source-backed runtime entry and owner-view proposals."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, cast

from token_io_decoupling_core.heading_parser import extract_heading

from .compiler import MAX_ARTIFACT_BYTES, MAX_ENTRY_CHARS, CompileError, _source_path
from .legacy import read_legacy_sources
from .review_draft import build_review_draft


def build_entry_review(root: Path) -> dict[str, Any]:
    """Return proposals and conservative diagnostics, never a compilable artifact."""
    root = root.resolve(strict=True)
    draft_path = root / "mcp-project-dev/legacy-mapping-review.v1.json"
    raw_draft = _source_path(root, "mcp-project-dev/legacy-mapping-review.v1.json").read_bytes()
    draft = json.loads(raw_draft)
    current = json.loads(json.dumps(build_review_draft(root), ensure_ascii=False))
    if draft != current:
        raise CompileError("review draft does not match current source files and classifications")
    legacy = read_legacy_sources(root)
    units = {unit["source_unit_id"]: unit for unit in draft["source_units"]}
    fragments = draft["legacy_bindings"]["fragments"]
    owners = draft["legacy_bindings"]["owners"]
    excerpts: dict[tuple[str, str], str] = {}
    by_path_heading: dict[tuple[str, str, str], str] = {}
    for unit_id, unit in units.items():
        for locale, source_key in (("en", "source_en"), ("zh_cn", "source_zh_cn")):
            source = unit[source_key]
            raw = _source_path(root, source["path"]).read_bytes()
            excerpt = extract_heading(raw.decode("utf-8"), source["heading"]).strip()
            if (
                hashlib.sha256(raw).hexdigest() != source["source_sha256"]
                or hashlib.sha256(excerpt.encode()).hexdigest() != source["excerpt_sha256"]
            ):
                raise CompileError(f"review source changed: {source['path']}")
            excerpts[(unit_id, locale)] = excerpt
            by_path_heading[(locale, source["path"], source["heading"])] = unit_id

    graph: dict[str, list[tuple[str, str, str]]] = {unit_id: [] for unit_id in units}
    for unit_id, unit in units.items():
        for reference in unit["references"]["en"]:
            kind = reference["candidate_class"]
            if kind == "unresolved":
                raise CompileError(f"unresolved reference in review graph: {unit_id}")
            if kind in {"required", "conditional"}:
                target = reference.get("target_source_unit_id")
                if target not in units:
                    raise CompileError(f"unbound candidate reference in review graph: {unit_id}")
                graph[unit_id].append((target, kind, reference["selector"]["raw"]))
        for edge in unit["semantic_dependencies"]["en"]:
            if edge["class"] in {"required", "conditional"}:
                target = edge["target_source_unit_id"]
                if target not in units:
                    raise CompileError(f"unbound candidate semantic dependency: {unit_id}")
                provenance = edge["provenance"]
                evidence = provenance.get("json_pointer") or provenance["selector"]["quote"]
                graph[unit_id].append((target, edge["class"], evidence))

    cycles: list[dict[str, Any]] = []
    visiting: list[str] = []
    visited: set[str] = set()

    def visit(unit_id: str) -> None:
        if unit_id in visiting:
            cycle = visiting[visiting.index(unit_id) :] + [unit_id]
            steps = []
            for source_id, target_id in zip(cycle, cycle[1:], strict=False):
                kind, evidence = next(
                    (kind, evidence)
                    for target, kind, evidence in graph[source_id]
                    if target == target_id
                )
                source = units[source_id]["source_en"]
                steps.append(
                    {
                        "source_unit_id": source_id,
                        "source_path": source["path"],
                        "heading": source["heading"],
                        "target_source_unit_id": target_id,
                        "class": kind,
                        "evidence": evidence,
                    }
                )
            cycles.append({"unit_path": cycle, "steps": steps})
            return
        if unit_id in visited:
            return
        visiting.append(unit_id)
        for target, _kind, _evidence in graph[unit_id]:
            visit(target)
        visiting.pop()
        visited.add(unit_id)

    for unit_id in sorted(graph):
        visit(unit_id)

    def closure_for(initial: list[str], locale: str) -> dict[str, Any]:
        closure: set[str] = set()
        pending = list(initial)
        provider_roots: set[str] = set()
        definition_roots: set[str] = set()
        unresolved: list[str] = []
        codex_heading = (
            "Codex CLI / ChatGPT Desktop optimizations"
            if locale == "en"
            else "Codex CLI / ChatGPT Desktop 特别优化指令"
        )
        source_key = "source_en" if locale == "en" else "source_zh_cn"
        while True:
            while pending:
                unit_id = pending.pop()
                if unit_id in closure:
                    continue
                closure.add(unit_id)
                pending.extend(target for target, _kind, _evidence in graph[unit_id])
                source = units[unit_id][source_key]
                if "/layer-01-fundamental-concepts/" in source["path"]:
                    provider = by_path_heading.get((locale, source["path"], codex_heading))
                    if provider is None:
                        unresolved.append(f"missing Codex optimization unit: {source['path']}")
                    elif provider not in closure:
                        provider_roots.add(provider)
                        pending.append(provider)
            required_definitions = {
                target
                for unit_id in closure
                for reference in units[unit_id]["references"][locale]
                if reference["candidate_class"] == "internal_already_included"
                for target in (
                    reference.get("target_source_unit_id"),
                    reference.get("included_in_source_unit_id"),
                )
                if target is not None and target not in closure
            }
            if not required_definitions:
                break
            definition_roots.update(required_definitions)
            pending.extend(sorted(required_definitions))
        text_chars = sum(len(excerpts[(unit_id, locale)]) for unit_id in closure)
        return {
            "closure_source_unit_ids": sorted(closure),
            "provider_source_roots": sorted(provider_roots - set(initial)),
            "definition_backref_roots": sorted(definition_roots - set(initial)),
            "unresolved": sorted(set(unresolved)),
            "budget": {
                "required_unicode_chars_lower_bound": text_chars,
                "allowed_unicode_chars": MAX_ENTRY_CHARS,
                "exact_required": None,
                "status": "provisional: final serialization and approval require review",
            },
        }

    def selector(unit_id: str, locale: str, quote: str) -> dict[str, Any]:
        if not quote or quote not in excerpts[(unit_id, locale)]:
            raise CompileError(f"review selector is not present in source: {unit_id} ({locale})")
        return {"source_unit_id": unit_id, "quote": quote, "occurrence": 0}

    def mapping_fields(node_id: str, branch: str, locale: str) -> dict[str, dict[str, Any]]:
        unit_id = "mapping." + node_id
        excerpt = excerpts[(unit_id, locale)]
        pattern = r"(?ms)^### " + re.escape(branch) + r"\s*$\n(.*?)(?=^### |\Z)"
        matches = re.findall(pattern, excerpt)
        if len(matches) != 1:
            raise CompileError(
                f"mapping branch is missing or duplicated: {node_id}/{branch} ({locale})"
            )
        labels = (
            {"trigger": "Trigger", "actions": "Action", "pass": "Pass", "failure": "Failure"}
            if locale == "en"
            else {"trigger": "触发", "actions": "动作", "pass": "通过", "failure": "失败"}
        )
        result = {}
        for field, label in labels.items():
            lines = [line for line in matches[0].splitlines() if line.startswith(f"- {label}: ")]
            if len(lines) != 1 or not lines[0].removeprefix(f"- {label}: ").strip():
                raise CompileError(
                    f"mapping field is missing or duplicated: {node_id}/{branch}/{field} ({locale})"
                )
            quote = lines[0]
            if excerpt.count(quote) != 1:
                raise CompileError(
                    f"mapping selector is ambiguous: {node_id}/{branch}/{field} ({locale})"
                )
            result[field] = selector(unit_id, locale, quote)
        return result

    fragments_by_node: dict[str, list[str]] = {}
    for fragment in draft["legacy_fragments"]:
        fragments_by_node.setdefault(fragment["node_id"], []).append(fragment["fragment_id"])
    nodes = {node["node_id"]: node for node in draft["legacy_node_metadata"]}
    entries: list[dict[str, Any]] = []
    all_reachable: set[tuple[str, str]] = set()
    incomplete_fields = 0
    for node in draft["legacy_context_nodes"]:
        node_id = node["node_id"]
        base_roots = [
            "mapping." + node_id,
            *dict.fromkeys(fragments[fragment] for fragment in node["default_fragment_ids"]),
        ]
        for locale in ("en", "zh_cn"):
            closure = closure_for(base_roots, locale)
            all_reachable.update(
                (source_id, locale) for source_id in closure["closure_source_unit_ids"]
            )
            mapping_id = "mapping." + node_id
            action_line = (
                "Entry action: Report the source-backed criteria for this bounded node; "
                "lookup performs no workflow effect."
                if locale == "en"
                else "入口动作：报告此有界节点的有源条件；查询本身不产生工作流效果。"
            )
            action_proposal = selector(mapping_id, locale, action_line)
            branches = []
            for original in nodes[node_id]["legal_branches"]:
                mapped = mapping_fields(node_id, original, locale)
                fields = {
                    field: {
                        "selector": chosen,
                        "status": "proposal_requires_root_review",
                        "source_candidates": [],
                    }
                    for field, chosen in mapped.items()
                }
                branch_id = re.sub(r"[^a-z0-9._-]+", "_", original.lower()).strip("_")
                branches.append({"id": branch_id, "legacy_branch": original, **fields})
            optional = [
                {
                    "legacy_fragment_id": fragment_id,
                    "source_unit_id": fragments[fragment_id],
                    "status": "condition_and_request_semantics_require_root_review",
                }
                for fragment_id in fragments_by_node[node_id]
                if fragment_id in legacy["optional_fragment_owner_bindings"]
            ]
            entries.append(
                {
                    "tool_id": "rules_get_context",
                    "node_id": node_id,
                    "stage_id": "context",
                    "locale": locale,
                    "source_unit_ids": base_roots,
                    "additional_provider_roots": closure["provider_source_roots"],
                    "proposed_definition_backref_roots": closure["definition_backref_roots"],
                    "actions": [action_proposal],
                    "actions_status": "proposal_requires_root_review",
                    "branches": branches,
                    "optional_fragment_candidates": optional,
                    "additional_owner_source_candidates": [],
                    "closure_diagnostic": closure,
                }
            )

    owner_views = []
    for owner_id in legacy["delegation_policy_owners"]:
        for locale in ("en", "zh_cn"):
            initial = [owners[owner_id]]
            closure = closure_for(initial, locale)
            all_reachable.update(
                (source_id, locale) for source_id in closure["closure_source_unit_ids"]
            )
            owner_views.append(
                {
                    "legacy_owner_id": owner_id,
                    "locale": locale,
                    "source_unit_ids": initial,
                    "additional_provider_roots": closure["provider_source_roots"],
                    "proposed_definition_backref_roots": closure["definition_backref_roots"],
                    "closure_diagnostic": closure,
                    "status": "proposal_requires_root_review",
                }
            )
    known_bytes = sum(len(excerpts[key].encode("utf-8")) for key in all_reachable)
    orphans = sorted(
        f"{unit_id}:{locale}"
        for unit_id in units
        for locale in ("en", "zh_cn")
        if (unit_id, locale) not in all_reachable
    )
    result: dict[str, Any] = {
        "format": "token-io-runtime-entry-review/v1",
        "complete": False,
        "review_status": "DRAFT_REQUIRES_ROOT_REVIEW_NOT_A_COMPILABLE_MANIFEST",
        "legacy_mapping_draft": str(draft_path.relative_to(root)),
        "legacy_mapping_draft_sha256": hashlib.sha256(raw_draft).hexdigest(),
        "legacy_source_hashes": legacy["source_hashes"],
        "tool_evidence": "rules_get_context is registered with "
        "RuleContextPayload/ActiveCheckpointNode; owner views are not tools",
        "runtime_entries": entries,
        "owner_views": owner_views,
        "diagnostics": {
            "cycles": cycles,
            "unreachable_source_units": orphans,
            "unresolved_branch_selector_fields": incomplete_fields,
            "known_excerpt_utf8_bytes_lower_bound": known_bytes,
            "artifact_bytes_allowed": MAX_ARTIFACT_BYTES,
            "artifact_bytes_exact": None,
            "status": (
                "mapping selectors, optional fragments, roots and serialization require review"
            ),
        },
    }
    # This validates the proposed explicit roots and all source bindings in
    # memory only. It neither approves them nor writes a complete artifact.
    from .review_diagnostics import diagnose_review

    diagnostics = cast("dict[str, Any]", result["diagnostics"])
    try:
        diagnostic = diagnose_review(root, draft, result)
    except CompileError as exc:
        diagnostics["in_memory_compile"] = {"status": "failed", "error": str(exc)}
    else:
        diagnostics["in_memory_compile"] = diagnostic
    return result

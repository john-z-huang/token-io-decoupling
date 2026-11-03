"""In-memory diagnostics for an unapproved source-backed review proposal.

No function in this module publishes a manifest or a compiled artifact.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .compiler import MAX_ARTIFACT_BYTES, MAX_ENTRY_CHARS, CompileError, _canonical
from .project_compiler import compile_project_manifest


def proposed_manifest(draft: dict[str, Any], review: dict[str, Any]) -> dict[str, Any]:
    """Translate explicit review proposals to an ephemeral manifest for validation."""
    if draft.get("complete") is not False or review.get("complete") is not False:
        raise CompileError("only unapproved review proposals may be diagnosed")
    source_units = []
    for unit in draft["source_units"]:
        for locale, source_key in (("en", "source_en"), ("zh_cn", "source_zh_cn")):
            source = unit[source_key]
            references = []
            for item in unit["references"][locale]:
                kind = item["candidate_class"]
                if kind not in {
                    "required",
                    "conditional",
                    "navigation",
                    "internal_already_included",
                }:
                    raise CompileError(f"unresolved review reference in {unit['source_unit_id']}")
                fields = ["selector", "label", "destination"]
                if kind in {"required", "conditional", "internal_already_included"}:
                    fields.append("target_source_unit_id")
                if kind == "conditional":
                    fields += ["condition_id", "trigger_selector"]
                if kind == "internal_already_included":
                    fields.append("included_in_source_unit_id")
                try:
                    references.append({"class": kind, **{field: item[field] for field in fields}})
                except KeyError as exc:
                    raise CompileError(
                        f"unbound review reference in {unit['source_unit_id']}"
                    ) from exc
            dependencies = []
            for item in unit["semantic_dependencies"][locale]:
                fields = ["class", "target_source_unit_id", "provenance"]
                if item["class"] == "conditional":
                    fields += ["condition_id", "trigger_selector"]
                dependencies.append({field: item[field] for field in fields})
            source_units.append(
                {
                    "source_unit_id": unit["source_unit_id"],
                    "source_kind": unit["source_kind"],
                    "locale": locale,
                    "source": {"path": source["path"], "heading": source["heading"]},
                    "expected_hashes": {
                        "source_sha256": source["source_sha256"],
                        "excerpt_sha256": source["excerpt_sha256"],
                    },
                    "references": references,
                    "semantic_dependencies": dependencies,
                }
            )

    def roots(item: dict[str, Any]) -> list[str]:
        # These are explicitly listed in the review proposal for human review.
        # The production compiler never invents or appends these roots.
        return list(
            dict.fromkeys(
                item["source_unit_ids"]
                + item["additional_provider_roots"]
                + item["proposed_definition_backref_roots"]
            )
        )

    entries = []
    for item in review["runtime_entries"]:
        branches = []
        for branch in item["branches"]:
            if any(
                branch[field]["selector"] is None
                for field in ("trigger", "actions", "pass", "failure")
            ):
                raise CompileError("review proposal has unresolved branch selectors")
            branches.append(
                {
                    "id": branch["id"],
                    "legacy_branch": branch["legacy_branch"],
                    **{
                        field: branch[field]["selector"]
                        for field in ("trigger", "actions", "pass", "failure")
                    },
                }
            )
        entries.append(
            {
                **{field: item[field] for field in ("tool_id", "node_id", "stage_id", "locale")},
                "source_unit_ids": roots(item),
                "actions": item["actions"],
                "branches": branches,
            }
        )
    views = [
        {
            "legacy_owner_id": item["legacy_owner_id"],
            "locale": item["locale"],
            "source_unit_ids": roots(item),
        }
        for item in review["owner_views"]
    ]
    return {
        "manifest_format": "token-io-runtime-instructions-manifest/v1",
        "policy_contract_version": 2,
        "legacy_context_index_version": 1,
        "legacy_source_hashes": draft["legacy_source_hashes"],
        "legacy_bindings": draft["legacy_bindings"],
        "budgets": {},
        "source_units": source_units,
        "runtime_entries": entries,
        "owner_views": views,
    }


def diagnose_review(root: Path, draft: dict[str, Any], review: dict[str, Any]) -> dict[str, Any]:
    """Run the real gate in memory and return sizes only, never a release artifact."""
    artifact = compile_project_manifest(root, proposed_manifest(draft, review))
    units = {(unit["source_unit_id"], unit["locale"]): unit for unit in artifact["source_units"]}
    result: dict[str, Any] = {
        "status": "provisional_in_memory_only_requires_root_review",
        "artifact_bytes_required": len(_canonical(artifact)) + 1,
        "artifact_bytes_allowed": MAX_ARTIFACT_BYTES,
        "source_unit_records_required": len(artifact["source_units"]),
        "source_unit_records_allowed": 512,
        "runtime_entries": [],
        "owner_views": [],
    }
    for category, singular in (("runtime_entries", "entry"), ("owner_views", "owner_view")):
        for item in artifact[category]:
            body = {key: value for key, value in item.items() if key != "content_sha256"}
            closure = [
                units[(source_id, item["locale"])] for source_id in item["closure_source_unit_ids"]
            ]
            size = len(_canonical({singular: body, "source_units": closure}).decode("utf-8"))
            identity = (
                {key: item[key] for key in ("tool_id", "node_id", "stage_id", "locale")}
                if singular == "entry"
                else {key: item[key] for key in ("legacy_owner_id", "locale")}
            )
            result[category].append(
                {
                    **identity,
                    "required_unicode_chars": size,
                    "allowed_unicode_chars": MAX_ENTRY_CHARS,
                    "source_unit_ids": item["source_unit_ids"],
                    "closure_source_unit_ids": item["closure_source_unit_ids"],
                }
            )
    return result

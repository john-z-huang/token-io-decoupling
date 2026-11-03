"""Strict project-specific gate in front of the generic compilation engine."""

from __future__ import annotations

from pathlib import Path, PurePosixPath
from typing import Any

from .compiler import (
    MAX_ARTIFACT_BYTES,
    CompileError,
    _canonical,
    _sha,
    _source_path,
    compile_manifest,
    validate_manifest,
)
from .legacy import read_legacy_sources
from .markdown_refs import markdown_heading_locations


def compile_project_manifest(root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    """Compile only after validating all real legacy sources and their bindings."""
    sources = read_legacy_sources(root)
    checked = validate_manifest(manifest)
    if checked["legacy_source_hashes"] != sources["source_hashes"]:
        raise CompileError("project legacy source hashes do not match all three actual sources")

    registry, index = sources["registry"], sources["index"]
    nodes = {node["node_id"]: node for node in registry["nodes"]}
    fragments = {fragment["fragment_id"]: fragment for fragment in index["fragments"]}
    owners = sources["owner_paths"]
    optional = sources["optional_fragment_owner_bindings"]
    if len(nodes) != 17 or len(fragments) != 44 or len(owners) != 8 or len(optional) != 3:
        raise CompileError("unsupported project legacy mapping coverage")
    bindings = checked["legacy_bindings"]
    if set(bindings["fragments"]) != set(fragments) or set(bindings["owners"]) != set(owners):
        raise CompileError("legacy bindings do not cover the actual fragment and owner IDs")

    for fragment_id, fragment in fragments.items():
        node = nodes[fragment["node_id"]]
        owner_id = optional.get(fragment_id, (None, None))[1]
        for locale in ("en", "zh_cn"):
            unit = checked["source_unit_map"][(bindings["fragments"][fragment_id], locale)]
            path = owners[owner_id] if owner_id else node["owner_path"]
            if locale == "zh_cn":
                path = (
                    path.removesuffix(".md") + "_zh_cn.md"
                    if owner_id
                    else node["owner_mirrors"]["zh_cn"]["path"]
                )
            heading = fragment["section_en" if locale == "en" else "section_zh_cn"]
            if unit["source"] != {"path": path, "heading": heading}:
                raise CompileError(
                    f"legacy fragment binding source mismatch: {fragment_id} ({locale})"
                )
        if owner_id and bindings["owners"][owner_id] != bindings["fragments"][fragment_id]:
            raise CompileError(
                f"optional fragment alias does not share its owner unit: {fragment_id}"
            )

    for owner_id, path in owners.items():
        for locale in ("en", "zh_cn"):
            unit = checked["source_unit_map"][(bindings["owners"][owner_id], locale)]
            expected_path = path if locale == "en" else path.removesuffix(".md") + "_zh_cn.md"
            expected_heading = "General rules" if locale == "en" else "通用规范"
            if unit["source"] != {"path": expected_path, "heading": expected_heading}:
                raise CompileError(f"legacy owner binding source mismatch: {owner_id} ({locale})")

    expected_edges = {
        (
            bindings["fragments"][fragment["fragment_id"]],
            bindings["fragments"][dependency],
            f"/fragments/{fragment_index}/dependencies/{dependency_index}",
        )
        for fragment_index, fragment in enumerate(index["fragments"])
        for dependency_index, dependency in enumerate(fragment.get("dependencies", []))
    }
    for locale in ("en", "zh_cn"):
        observed_edges = {
            (
                unit["source_unit_id"],
                edge["target_source_unit_id"],
                edge["provenance"]["json_pointer"],
            )
            for unit in checked["source_units"]
            if unit["locale"] == locale
            for edge in unit.get("semantic_dependencies", [])
            if edge["provenance"]["kind"] == "legacy_index_dependency"
        }
        if observed_edges != expected_edges:
            raise CompileError(f"legacy dependency graph coverage mismatch: {locale}")

    expected_owner_views = {
        (owner_id, locale)
        for owner_id in sources["delegation_policy_owners"]
        for locale in ("en", "zh_cn")
    }
    if set(checked["owner_view_map"]) != expected_owner_views:
        raise CompileError(
            "owner views do not cover the five actual delegation owners in both locales"
        )

    artifact = compile_manifest(root, manifest)
    entries = artifact["runtime_entries"]
    owner_views = artifact["owner_views"]
    defaults = {node["node_id"]: node["default_fragment_ids"] for node in index["nodes"]}
    source_units = checked["source_unit_map"]
    by_source = {
        (
            locale,
            PurePosixPath(unit["source"]["path"]).as_posix(),
            unit["source"]["heading"],
        ): source_id
        for (source_id, locale), unit in source_units.items()
    }
    headings_by_path: dict[str, list[tuple[int, int, int, str, str | None]]] = {}
    for locale in ("en", "zh_cn"):
        locale_entries = [entry for entry in entries if entry["locale"] == locale]
        if {entry["node_id"] for entry in locale_entries} != set(nodes):
            raise CompileError(f"runtime entries do not cover all legacy nodes: {locale}")
        codex_heading = (
            "Codex CLI / ChatGPT Desktop optimizations"
            if locale == "en"
            else "Codex CLI / ChatGPT Desktop 特别优化指令"
        )
        claude_heading = (
            "Claude Code CLI / Claude Desktop optimizations"
            if locale == "en"
            else "Claude Code CLI / Claude Desktop 特别优化指令"
        )
        for entry in locale_entries:
            if entry["tool_id"] != "rules_get_context":
                raise CompileError(
                    f"unsupported callable rule-context tool: {entry['tool_id']}; "
                    "owner policies are source units, not callable entries"
                )
            if entry["stage_id"] != "context":
                raise CompileError(f"unsupported rule-context stage: {entry['stage_id']}")
        locale_views = [view for view in owner_views if view["locale"] == locale]
        for material in [*locale_entries, *locale_views]:
            closure = set(material["closure_source_unit_ids"])
            for source_id in closure:
                unit = source_units[(source_id, locale)]
                path = PurePosixPath(unit["source"]["path"]).as_posix()
                if not path.startswith(
                    "docs/skill/references/coding/layer-01-fundamental-concepts/"
                ):
                    continue
                if path not in headings_by_path:
                    headings_by_path[path] = markdown_heading_locations(
                        _source_path(root, path).read_text(encoding="utf-8")
                    )
                headings = headings_by_path[path]
                selected = next(
                    (item for item in headings if item[3] == unit["source"]["heading"]), None
                )
                parent_sections = [
                    item
                    for item in headings
                    if selected is not None and item[0] <= selected[0] and item[2] == 2
                ]
                scope = parent_sections[-1][3] if parent_sections else None
                general_heading = "General rules" if locale == "en" else "通用规范"
                if scope == claude_heading or scope not in {general_heading, codex_heading}:
                    raise CompileError(
                        f"Layer-01 source section is outside the MCP boundary: {source_id}"
                    )
                codex_source = by_source.get((locale, path, codex_heading))
                if codex_source not in closure:
                    raise CompileError(
                        f"entry closure lacks the same-document Codex optimization: "
                        f"{source_id} ({locale})"
                    )
        for node_id, default_ids in defaults.items():
            required = {bindings["fragments"][fragment] for fragment in default_ids}
            expected_branches = set(nodes[node_id]["legal_branches"])
            for entry in (item for item in locale_entries if item["node_id"] == node_id):
                if not required <= set(entry["closure_source_unit_ids"]):
                    raise CompileError(f"context entry omits legacy defaults: {node_id} ({locale})")
                branches = entry["instructions"]["branches"]
                actual_branches = [branch.get("legacy_branch") for branch in branches]
                if (
                    len(actual_branches) != len(expected_branches)
                    or set(actual_branches) != expected_branches
                ):
                    raise CompileError(
                        f"legacy legal branch coverage mismatch in context entry: "
                        f"{entry['tool_id']}/{node_id}/{entry['stage_id']} ({locale})"
                    )
        for fragment_id, fragment in fragments.items():
            source_id = bindings["fragments"][fragment_id]
            if not any(
                entry["node_id"] == fragment["node_id"]
                and source_id in entry["closure_source_unit_ids"]
                for entry in locale_entries
            ):
                raise CompileError(
                    f"legacy fragment is absent from its node closure: {fragment_id} ({locale})"
                )

    artifact["legacy_metadata"] = {
        "nodes": registry["nodes"],
        "context_nodes": index["nodes"],
        "fragments": index["fragments"],
        "owner_paths": owners,
        "delegation_policy_owners": list(sources["delegation_policy_owners"]),
        "optional_fragment_owner_bindings": {
            fragment: {"node_id": node, "owner_id": owner}
            for fragment, (node, owner) in optional.items()
        },
    }
    artifact.pop("canonical_sha256")
    artifact["canonical_sha256"] = _sha(_canonical(artifact))
    allowed = checked["budgets"].get("artifact_bytes", MAX_ARTIFACT_BYTES)
    size = len(_canonical(artifact)) + 1
    if size > allowed:
        raise CompileError(f"artifact budget exceeded: required={size} allowed={allowed}")
    return artifact

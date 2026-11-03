"""Behavioral regressions for source closure integrity and artifact publication."""

from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
from typing import Any

import pytest

from token_io_decoupling_dev import compiler
from token_io_decoupling_dev.compiler import (
    CompileError,
    compile_manifest,
    fixed_output_path,
    load_json_strict,
    write_fixed_output,
)
from token_io_decoupling_dev.markdown_refs import extract_markdown_links


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _case(root: Path, edge_class: str = "required") -> dict[str, Any]:
    legacy = root / "mcp"
    legacy.mkdir()
    registry = legacy / "rule-registry.json"
    index = legacy / "rule-context-index.json"
    registry.write_text('{"contract_version":2}', encoding="utf-8")
    index.write_text('{"schema_version":1}', encoding="utf-8")
    source_units = []
    runtime_entries = []
    for stage in ("root", "dependency"):
        for locale in ("en", "zh_cn"):
            if locale == "en":
                trigger, action, passed, failed = (
                    "If selected.",
                    f"Execute {stage}.",
                    "Completed.",
                    "Otherwise stop.",
                )
                heading = "Rules"
                label = "Dependency"
            else:
                trigger, action, passed, failed = (
                    "如被选择。",
                    f"执行 {stage}。",
                    "完成。",
                    "否则停止。",
                )
                heading = "规则"
                label = "依赖"
            body_lines = [trigger, action, passed, failed]
            if stage == "root":
                body_lines.append(f"See [{label}](dependency.{locale}.md).")
            body = "\n".join(body_lines)
            path = root / f"{stage}.{locale}.md"
            raw = f"# Policy\n\n## {heading}\n\n{body}\n".encode()
            path.write_bytes(raw)
            refs: list[dict[str, Any]] = []
            if stage == "root":
                refs = [
                    {
                        "class": edge_class,
                        "selector": {
                            "raw": f"[{label}](dependency.{locale}.md)",
                            "occurrence": 0,
                        },
                        "label": label,
                        "destination": f"dependency.{locale}.md",
                        "target_source_unit_id": "dependency",
                    }
                ]
                if edge_class == "conditional":
                    refs[0].update(
                        condition_id="selected",
                        trigger_selector={
                            "source_unit_id": "root",
                            "quote": trigger,
                            "occurrence": 0,
                        },
                    )
            source_units.append(
                {
                    "source_unit_id": stage,
                    "source_kind": "fragment",
                    "legacy_id": stage,
                    "legacy_node_id": "contract",
                    "locale": locale,
                    "source": {"path": path.name, "heading": heading},
                    "expected_hashes": {
                        "source_sha256": _digest(raw),
                        "excerpt_sha256": _digest(body.encode()),
                    },
                    "references": refs,
                }
            )
            if stage == "root":
                runtime_entries.append(
                    {
                        "tool_id": "test_tool",
                        "node_id": "contract",
                        "stage_id": "root",
                        "locale": locale,
                        "source_unit_ids": ["root"],
                        "actions": [{"source_unit_id": "root", "quote": action, "occurrence": 0}],
                        "branches": [
                            {
                                "id": "ready",
                                "trigger": {
                                    "source_unit_id": "root",
                                    "quote": trigger,
                                    "occurrence": 0,
                                },
                                "actions": {
                                    "source_unit_id": "root",
                                    "quote": action,
                                    "occurrence": 0,
                                },
                                "pass": {
                                    "source_unit_id": "root",
                                    "quote": passed,
                                    "occurrence": 0,
                                },
                                "failure": {
                                    "source_unit_id": "root",
                                    "quote": failed,
                                    "occurrence": 0,
                                },
                            }
                        ],
                    }
                )
    return {
        "manifest_format": "token-io-runtime-instructions-manifest/v1",
        "policy_contract_version": 2,
        "legacy_context_index_version": 1,
        "legacy_source_hashes": {
            "registry_sha256": _digest(registry.read_bytes()),
            "context_index_sha256": _digest(index.read_bytes()),
        },
        "budgets": {},
        "source_units": source_units,
        "runtime_entries": runtime_entries,
    }


def _change_source(root: Path, manifest: dict[str, Any], stage: str) -> None:
    unit = next(
        item
        for item in manifest["source_units"]
        if item["source_unit_id"] == stage and item["locale"] == "en"
    )
    path = root / unit["source"]["path"]
    raw = path.read_bytes() + b"\nAdditional required guard.\n"
    path.write_bytes(raw)
    excerpt = raw.decode().split("## Rules\n\n", 1)[1].strip()
    unit["expected_hashes"] = {
        "source_sha256": _digest(raw),
        "excerpt_sha256": _digest(excerpt.encode()),
    }


def _entry(artifact: dict[str, Any], stage: str) -> dict[str, Any]:
    return next(
        entry
        for entry in artifact["runtime_entries"]
        if entry["stage_id"] == stage and entry["locale"] == "en"
    )


@pytest.mark.parametrize("edge_class", ["required", "conditional"])
def test_dependency_change_invalidates_parent_instruction_hash(
    tmp_path: Path, edge_class: str
) -> None:
    manifest = _case(tmp_path, edge_class)
    before = compile_manifest(tmp_path, manifest)
    _change_source(tmp_path, manifest, "dependency")
    after = compile_manifest(tmp_path, manifest)
    before_root = next(
        item
        for item in _entry(before, "root")["source_provenance"]
        if item["source_unit_id"] == "root"
    )
    after_root = next(
        item
        for item in _entry(after, "root")["source_provenance"]
        if item["source_unit_id"] == "root"
    )
    assert before_root == after_root
    assert _entry(before, "root")["content_sha256"] != _entry(after, "root")["content_sha256"]


def test_instruction_identity_is_bound_even_for_shared_sources(tmp_path: Path) -> None:
    manifest = _case(tmp_path)
    original = compile_manifest(tmp_path, manifest)
    changed = copy.deepcopy(manifest)
    for entry in changed["runtime_entries"]:
        entry["tool_id"] = "another_tool"
    alternative = compile_manifest(tmp_path, changed)
    assert (
        _entry(original, "root")["content_sha256"] != _entry(alternative, "root")["content_sha256"]
    )


def test_original_legacy_branch_value_is_preserved_and_hash_bound(tmp_path: Path) -> None:
    manifest = _case(tmp_path)
    for entry in manifest["runtime_entries"]:
        entry["branches"][0]["legacy_branch"] = "request evidence"
    first = compile_manifest(tmp_path, manifest)
    assert (
        _entry(first, "root")["instructions"]["branches"][0]["legacy_branch"] == "request evidence"
    )
    for entry in manifest["runtime_entries"]:
        entry["branches"][0]["legacy_branch"] = "not applicable with reason"
    second = compile_manifest(tmp_path, manifest)
    assert _entry(first, "root")["content_sha256"] != _entry(second, "root")["content_sha256"]


@pytest.mark.parametrize("identity_field", ["tool_id", "node_id"])
def test_same_stage_is_valid_for_distinct_tool_or_node(tmp_path: Path, identity_field: str) -> None:
    manifest = _case(tmp_path)
    additional = copy.deepcopy(manifest["runtime_entries"])
    for entry in additional:
        entry[identity_field] = "another"
    manifest["runtime_entries"].extend(additional)
    artifact = compile_manifest(tmp_path, manifest)
    assert len(artifact["runtime_entries"]) == 4
    assert {entry["stage_id"] for entry in artifact["runtime_entries"]} == {"root"}


def test_budget_includes_output_instructions_beyond_source_excerpts(tmp_path: Path) -> None:
    manifest = _case(tmp_path)
    manifest["budgets"]["entry_closure_unicode_chars"] = 2000
    unit = next(
        item
        for item in manifest["source_units"]
        if item["source_unit_id"] == "root" and item["locale"] == "en"
    )
    path = tmp_path / unit["source"]["path"]
    raw = path.read_bytes() + ("A" * 1500 + "\n").encode()
    path.write_bytes(raw)
    excerpt = raw.decode().split("## Rules\n\n", 1)[1].strip()
    unit["expected_hashes"] = {
        "source_sha256": _digest(raw),
        "excerpt_sha256": _digest(excerpt.encode()),
    }
    selector = {"source_unit_id": "root", "quote": "A" * 1500, "occurrence": 0}
    manifest["runtime_entries"][0]["actions"] = [selector]
    manifest["runtime_entries"][0]["branches"][0]["actions"] = selector
    with pytest.raises(CompileError, match="budget"):
        compile_manifest(tmp_path, manifest)
    assert not fixed_output_path(tmp_path).exists()


@pytest.mark.parametrize(
    "field,value",
    [
        ("legacy_context_index_version", True),
        ("legacy_context_index_version", 1.0),
        ("legacy_context_index_version", "1"),
        ("policy_contract_version", 2.0),
        ("policy_contract_version", "2"),
    ],
)
def test_manifest_version_is_an_exact_integer(tmp_path: Path, field: str, value: Any) -> None:
    manifest = _case(tmp_path)
    manifest[field] = value
    with pytest.raises(CompileError):
        compile_manifest(tmp_path, manifest)


def test_duplicate_dependency_declarations_are_rejected(tmp_path: Path) -> None:
    manifest = _case(tmp_path)
    for unit in manifest["source_units"]:
        if unit["source_unit_id"] == "root":
            unit["references"].append(dict(unit["references"][0]))
    with pytest.raises(CompileError, match="duplicate"):
        compile_manifest(tmp_path, manifest)


def test_missing_markdown_reference_classification_fails_closed(tmp_path: Path) -> None:
    manifest = _case(tmp_path)
    for unit in manifest["source_units"]:
        if unit["source_unit_id"] == "root":
            unit["references"] = []
    with pytest.raises(CompileError, match="coverage"):
        compile_manifest(tmp_path, manifest)


def _redirect_reference(root: Path, unit: dict[str, Any], destination: str) -> None:
    from token_io_decoupling_core.heading_parser import extract_heading

    reference = unit["references"][0]
    old = reference["selector"]["raw"]
    new = f"[{reference['label']}]({destination})"
    path = root / unit["source"]["path"]
    source = path.read_text(encoding="utf-8").replace(old, new, 1)
    path.write_text(source, encoding="utf-8")
    reference["selector"]["raw"] = new
    reference["destination"] = destination
    unit["expected_hashes"] = {
        "source_sha256": _digest(source.encode()),
        "excerpt_sha256": _digest(
            extract_heading(source, unit["source"]["heading"]).strip().encode()
        ),
    }


@pytest.mark.parametrize("trigger_target", ["self", "forward"])
def test_conditional_trigger_resolves_after_all_units_are_loaded(
    tmp_path: Path, trigger_target: str
) -> None:
    manifest = _case(tmp_path, "conditional")
    if trigger_target == "forward":
        renamed = {"root": "aaa", "dependency": "zzz"}
        for unit in manifest["source_units"]:
            unit["source_unit_id"] = renamed[unit["source_unit_id"]]
            for reference in unit["references"]:
                reference["target_source_unit_id"] = renamed[reference["target_source_unit_id"]]
                reference["trigger_selector"]["source_unit_id"] = "zzz"
        for entry in manifest["runtime_entries"]:
            entry["source_unit_ids"] = ["aaa"]
            for selector in [
                *entry["actions"],
                *(entry["branches"][0][name] for name in ("trigger", "actions", "pass", "failure")),
            ]:
                selector["source_unit_id"] = "aaa"
    artifact = compile_manifest(tmp_path, manifest)
    root_id = "aaa" if trigger_target == "forward" else "root"
    unit = next(
        u
        for u in artifact["source_units"]
        if u["source_unit_id"] == root_id and u["locale"] == "en"
    )
    assert unit["references"][0]["trigger_text"]["source_unit_id"] == (
        "zzz" if trigger_target == "forward" else "root"
    )
    assert unit["references"][0]["trigger_text"]["text"] == "If selected."


@pytest.mark.parametrize("field", ["action", "trigger", "actions", "pass", "failure"])
def test_entry_instructions_reject_quotes_missing_from_the_source(
    tmp_path: Path, field: str
) -> None:
    manifest = _case(tmp_path)
    entry = next(entry for entry in manifest["runtime_entries"] if entry["locale"] == "en")
    selector = entry["actions"][0] if field == "action" else entry["branches"][0][field]
    selector["quote"] = "This text does not occur in the source."
    with pytest.raises(CompileError, match="source quote selector did not match"):
        compile_manifest(tmp_path, manifest)


def test_quote_occurrence_must_exist_in_source(tmp_path: Path) -> None:
    manifest = _case(tmp_path)
    for entry in manifest["runtime_entries"]:
        entry["actions"][0]["occurrence"] = 1
    with pytest.raises(CompileError, match="source quote selector did not match"):
        compile_manifest(tmp_path, manifest)


def test_conditional_trigger_must_be_in_the_entry_closure(tmp_path: Path) -> None:
    manifest = _case(tmp_path, "conditional")
    dependencies = [
        unit for unit in manifest["source_units"] if unit["source_unit_id"] == "dependency"
    ]
    for dependency in dependencies:
        outside = copy.deepcopy(dependency)
        outside["source_unit_id"] = "outside"
        outside["source"]["path"] = f"outside.{outside['locale']}.md"
        (tmp_path / outside["source"]["path"]).write_bytes(
            (tmp_path / dependency["source"]["path"]).read_bytes()
        )
        manifest["source_units"].append(outside)
    for unit in manifest["source_units"]:
        if unit["source_unit_id"] == "root":
            unit["references"][0]["trigger_selector"]["source_unit_id"] = "outside"
    with pytest.raises(
        CompileError, match="conditional trigger source is outside the entry closure"
    ):
        compile_manifest(tmp_path, manifest)


def _semantic_case(root: Path, edge_class: str = "required") -> dict[str, Any]:
    manifest = _case(root, "navigation")
    for unit in manifest["source_units"]:
        if unit["source_unit_id"] != "root":
            continue
        trigger = "If selected." if unit["locale"] == "en" else "如被选择。"
        selector = {"source_unit_id": "root", "quote": trigger, "occurrence": 0}
        edge: dict[str, Any] = {
            "class": edge_class,
            "target_source_unit_id": "dependency",
            "provenance": {"kind": "markdown_quote", "selector": dict(selector)},
        }
        if edge_class == "conditional":
            edge.update(condition_id="selected", trigger_selector=dict(selector))
        unit["semantic_dependencies"] = [edge]
    return manifest


@pytest.mark.parametrize("edge_class", ["required", "conditional"])
def test_sourced_non_link_dependency_enters_closure_and_hash(
    tmp_path: Path, edge_class: str
) -> None:
    manifest = _semantic_case(tmp_path, edge_class)
    first = compile_manifest(tmp_path, manifest)
    assert set(_entry(first, "root")["closure_source_unit_ids"]) == {"root", "dependency"}
    _change_source(tmp_path, manifest, "dependency")
    second = compile_manifest(tmp_path, manifest)
    assert _entry(first, "root")["content_sha256"] != _entry(second, "root")["content_sha256"]


@pytest.mark.parametrize("mutation", ["missing_quote", "wrong_unit", "bad_trigger", "duplicate"])
def test_semantic_dependency_requires_valid_source_provenance(
    tmp_path: Path, mutation: str
) -> None:
    manifest = _semantic_case(tmp_path, "conditional")
    for unit in manifest["source_units"]:
        if unit["source_unit_id"] != "root":
            continue
        edge = unit["semantic_dependencies"][0]
        if mutation == "missing_quote":
            edge["provenance"]["selector"]["quote"] = "not in the source"
        elif mutation == "wrong_unit":
            edge["provenance"]["selector"]["source_unit_id"] = "dependency"
        elif mutation == "bad_trigger":
            edge["trigger_selector"]["source_unit_id"] = "dependency"
        else:
            unit["semantic_dependencies"].append(copy.deepcopy(edge))
    with pytest.raises(CompileError):
        compile_manifest(tmp_path, manifest)


def test_semantic_edges_participate_in_cycle_detection(tmp_path: Path) -> None:
    manifest = _semantic_case(tmp_path)
    for unit in manifest["source_units"]:
        if unit["source_unit_id"] == "dependency":
            quote = "If selected." if unit["locale"] == "en" else "如被选择。"
            unit["semantic_dependencies"] = [
                {
                    "class": "required",
                    "target_source_unit_id": "root",
                    "provenance": {
                        "kind": "markdown_quote",
                        "selector": {
                            "source_unit_id": "dependency",
                            "quote": quote,
                            "occurrence": 0,
                        },
                    },
                }
            ]
    with pytest.raises(CompileError, match="cycle"):
        compile_manifest(tmp_path, manifest)


def _legacy_semantic_case(root: Path) -> dict[str, Any]:
    manifest = _case(root, "navigation")
    index = {
        "schema_version": 1,
        "fragments": [{"fragment_id": "root.a", "dependencies": ["dep.a"]}],
    }
    raw = json.dumps(index).encode()
    (root / "mcp/rule-context-index.json").write_bytes(raw)
    digest = _digest(raw)
    manifest["legacy_source_hashes"]["context_index_sha256"] = digest
    manifest["legacy_bindings"] = {
        "fragments": {"root.a": "root", "root.alias": "root", "dep.a": "dependency"},
        "owners": {},
    }
    for unit in manifest["source_units"]:
        if unit["source_unit_id"] == "root":
            unit["semantic_dependencies"] = [
                {
                    "class": "required",
                    "target_source_unit_id": "dependency",
                    "provenance": {
                        "kind": "legacy_index_dependency",
                        "json_pointer": "/fragments/0/dependencies/0",
                        "fragment_id": "root.a",
                        "dependency_fragment_id": "dep.a",
                        "source_sha256": digest,
                    },
                }
            ]
    return manifest


def test_legacy_alias_and_json_dependency_bindings_are_compiled(tmp_path: Path) -> None:
    manifest = _legacy_semantic_case(tmp_path)
    artifact = compile_manifest(tmp_path, manifest)
    assert artifact["legacy_bindings"]["fragments"]["root.a"] == "root"
    assert artifact["legacy_bindings"]["fragments"]["root.alias"] == "root"
    assert set(_entry(artifact, "root")["closure_source_unit_ids"]) == {"root", "dependency"}


def _owner_view_case(root: Path) -> dict[str, Any]:
    manifest = _case(root, "navigation")
    manifest["legacy_bindings"] = {"fragments": {}, "owners": {"policy": "dependency"}}
    manifest["owner_views"] = [
        {"legacy_owner_id": "policy", "locale": locale, "source_unit_ids": ["dependency"]}
        for locale in ("en", "zh_cn")
    ]
    return manifest


def test_owner_view_precomputes_complete_source_closure_without_a_callable_branch(
    tmp_path: Path,
) -> None:
    manifest = _owner_view_case(tmp_path)
    first = compile_manifest(tmp_path, manifest)
    owner = next(view for view in first["owner_views"] if view["locale"] == "en")
    assert owner["legacy_owner_id"] == "policy"
    assert owner["closure_source_unit_ids"] == ["dependency"]
    assert owner["source_provenance"][0]["source_unit_id"] == "dependency"
    assert "tool_id" not in owner and "instructions" not in owner
    assert "dependency" not in _entry(first, "root")["closure_source_unit_ids"]
    _change_source(tmp_path, manifest, "dependency")
    second = compile_manifest(tmp_path, manifest)
    changed = next(view for view in second["owner_views"] if view["locale"] == "en")
    assert owner["content_sha256"] != changed["content_sha256"]
    assert _entry(first, "root")["content_sha256"] == _entry(second, "root")["content_sha256"]


def test_owner_view_hash_binds_identity_version_and_legacy_hash(
    tmp_path: Path, monkeypatch: Any
) -> None:
    manifest = _owner_view_case(tmp_path)
    manifest["legacy_bindings"]["owners"]["another"] = "dependency"
    manifest["owner_views"].extend(
        [
            {"legacy_owner_id": "another", "locale": locale, "source_unit_ids": ["dependency"]}
            for locale in ("en", "zh_cn")
        ]
    )
    first = compile_manifest(tmp_path, manifest)
    policy = next(
        view
        for view in first["owner_views"]
        if view["legacy_owner_id"] == "policy" and view["locale"] == "en"
    )
    other = next(
        view
        for view in first["owner_views"]
        if view["legacy_owner_id"] == "another" and view["locale"] == "en"
    )
    assert policy["content_sha256"] != other["content_sha256"]
    monkeypatch.setattr(compiler, "COMPILER_VERSION", 2)
    changed = compile_manifest(tmp_path, manifest)
    assert (
        policy["content_sha256"]
        != next(
            view
            for view in changed["owner_views"]
            if view["legacy_owner_id"] == "policy" and view["locale"] == "en"
        )["content_sha256"]
    )
    registry = tmp_path / "mcp/rule-registry.json"
    registry.write_text('{"contract_version":2,"change":true}', encoding="utf-8")
    manifest["legacy_source_hashes"]["registry_sha256"] = _digest(registry.read_bytes())
    again = compile_manifest(tmp_path, manifest)
    assert (
        next(
            view
            for view in changed["owner_views"]
            if view["legacy_owner_id"] == "policy" and view["locale"] == "en"
        )["content_sha256"]
        != next(
            view
            for view in again["owner_views"]
            if view["legacy_owner_id"] == "policy" and view["locale"] == "en"
        )["content_sha256"]
    )


def test_owner_view_hash_binds_transitive_dependency(tmp_path: Path) -> None:
    manifest = _semantic_case(tmp_path, "conditional")
    manifest["legacy_bindings"] = {"fragments": {}, "owners": {"policy": "root"}}
    manifest["owner_views"] = [
        {"legacy_owner_id": "policy", "locale": locale, "source_unit_ids": ["root"]}
        for locale in ("en", "zh_cn")
    ]
    first = compile_manifest(tmp_path, manifest)
    before = next(view for view in first["owner_views"] if view["locale"] == "en")
    assert set(before["closure_source_unit_ids"]) == {"root", "dependency"}
    _change_source(tmp_path, manifest, "dependency")
    second = compile_manifest(tmp_path, manifest)
    after = next(view for view in second["owner_views"] if view["locale"] == "en")
    assert before["content_sha256"] != after["content_sha256"]


def test_owner_view_missing_internal_backreference_is_not_auto_added(tmp_path: Path) -> None:
    manifest = _case(tmp_path, "internal_already_included")
    manifest["legacy_bindings"] = {"fragments": {}, "owners": {"policy": "root"}}
    for unit in manifest["source_units"]:
        if unit["source_unit_id"] == "root":
            unit["references"][0]["included_in_source_unit_id"] = "dependency"
    for entry in manifest["runtime_entries"]:
        entry["source_unit_ids"].append("dependency")
    views: list[dict[str, Any]] = [
        {"legacy_owner_id": "policy", "locale": locale, "source_unit_ids": ["root"]}
        for locale in ("en", "zh_cn")
    ]
    manifest["owner_views"] = views
    with pytest.raises(CompileError, match="internal back-reference"):
        compile_manifest(tmp_path, manifest)
    for view in views:
        view["source_unit_ids"].append("dependency")
    assert len(compile_manifest(tmp_path, manifest)["owner_views"]) == 2


def test_owner_view_closure_uses_same_budget_as_entries(tmp_path: Path) -> None:
    manifest = _owner_view_case(tmp_path)
    manifest["budgets"]["entry_closure_unicode_chars"] = 10000
    assert len(compile_manifest(tmp_path, manifest)["owner_views"]) == 2
    unit = next(
        u
        for u in manifest["source_units"]
        if u["source_unit_id"] == "dependency" and u["locale"] == "en"
    )
    path = tmp_path / unit["source"]["path"]
    raw = path.read_bytes() + ("\n" + "x" * 12000 + "\n").encode()
    path.write_bytes(raw)
    unit["expected_hashes"] = {
        "source_sha256": _digest(raw),
        "excerpt_sha256": _digest(raw.decode().split("## Rules\n\n", 1)[1].strip().encode()),
    }
    with pytest.raises(CompileError, match="owner view closure budget exceeded"):
        compile_manifest(tmp_path, manifest)


@pytest.mark.parametrize("mutation", ["missing_pair", "wrong_root", "duplicate", "callable_field"])
def test_owner_view_binding_and_non_callable_shape_are_strict(
    tmp_path: Path, mutation: str
) -> None:
    manifest = _owner_view_case(tmp_path)
    if mutation == "missing_pair":
        manifest["owner_views"].pop()
    elif mutation == "wrong_root":
        for view in manifest["owner_views"]:
            view["source_unit_ids"] = ["root"]
    elif mutation == "duplicate":
        manifest["owner_views"].append(copy.deepcopy(manifest["owner_views"][0]))
    else:
        for view in manifest["owner_views"]:
            view["tool_id"] = "invented"
    with pytest.raises(CompileError, match="owner view"):
        compile_manifest(tmp_path, manifest)


def test_source_aliases_must_use_bindings_not_duplicate_paths_or_hardlinks(tmp_path: Path) -> None:
    manifest = _case(tmp_path)
    root = next(
        unit
        for unit in manifest["source_units"]
        if unit["source_unit_id"] == "root" and unit["locale"] == "en"
    )
    dependency = next(
        unit
        for unit in manifest["source_units"]
        if unit["source_unit_id"] == "dependency" and unit["locale"] == "en"
    )
    root["source"]["path"] = "./" + dependency["source"]["path"]
    with pytest.raises(CompileError, match="unsafe source path"):
        compile_manifest(tmp_path, manifest)
    hardlink = tmp_path / "same-file.md"
    os.link(tmp_path / dependency["source"]["path"], hardlink)
    root["source"]["path"] = hardlink.name
    root["expected_hashes"] = dict(dependency["expected_hashes"])
    with pytest.raises(CompileError, match="duplicate actual source selector"):
        compile_manifest(tmp_path, manifest)


def test_manifest_schemas_expose_engine_and_project_requirements(tmp_path: Path) -> None:
    from jsonschema import Draft202012Validator

    from token_io_decoupling_dev.schema import MANIFEST_SCHEMA, PROJECT_MANIFEST_SCHEMA

    Draft202012Validator.check_schema(MANIFEST_SCHEMA)
    Draft202012Validator.check_schema(PROJECT_MANIFEST_SCHEMA)
    manifest = _legacy_semantic_case(tmp_path)
    assert not list(Draft202012Validator(MANIFEST_SCHEMA).iter_errors(manifest))
    errors = list(Draft202012Validator(PROJECT_MANIFEST_SCHEMA).iter_errors(manifest))
    assert any("owner_paths_sha256" in error.message for error in errors)
    assert any("legacy_branch" in error.message for error in errors)


@pytest.mark.parametrize("mutation", ["wrong_pointer", "wrong_target_alias", "wrong_hash"])
def test_legacy_dependency_pointer_and_aliases_cannot_be_forged(
    tmp_path: Path, mutation: str
) -> None:
    manifest = _legacy_semantic_case(tmp_path)
    if mutation == "wrong_target_alias":
        manifest["legacy_bindings"]["fragments"]["dep.a"] = "root"
    else:
        for unit in manifest["source_units"]:
            if unit["source_unit_id"] == "root":
                provenance = unit["semantic_dependencies"][0]["provenance"]
                if mutation == "wrong_pointer":
                    provenance["json_pointer"] = "/fragments/0/dependencies/9"
                else:
                    provenance["source_sha256"] = "0" * 64
    with pytest.raises(CompileError):
        compile_manifest(tmp_path, manifest)


def _copy_actual_legacy_sources(root: Path) -> dict[str, str]:
    from token_io_decoupling_dev.legacy import OWNER_SOURCE

    repo = Path(__file__).resolve().parents[2]
    hashes = {}
    for relative, key in (
        ("mcp/rule-registry.json", "registry_sha256"),
        ("mcp/rule-context-index.json", "context_index_sha256"),
        (OWNER_SOURCE, "owner_paths_sha256"),
    ):
        data = (repo / relative).read_bytes()
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        hashes[key] = _digest(data)
    return hashes


def test_owner_mapping_is_literal_parsed_without_executing_python(tmp_path: Path) -> None:
    from token_io_decoupling_dev.legacy import OWNER_SOURCE, read_legacy_sources

    _copy_actual_legacy_sources(tmp_path)
    marker = tmp_path / "should-not-be-created"
    path = tmp_path / OWNER_SOURCE
    path.write_text(
        path.read_text(encoding="utf-8")
        + f"\nfrom pathlib import Path\nPath({str(marker)!r}).write_text('unsafe')\n",
        encoding="utf-8",
    )
    sources = read_legacy_sources(tmp_path)
    assert len(sources["registry"]["nodes"]) == 17
    assert len(sources["index"]["fragments"]) == 44
    assert len(sources["owner_paths"]) == 8
    assert len(sources["optional_fragment_owner_bindings"]) == 3
    assert not marker.exists()


def test_owner_mapping_hash_change_invalidates_compilation(tmp_path: Path) -> None:
    from token_io_decoupling_dev.legacy import OWNER_SOURCE

    manifest = _case(tmp_path)
    manifest["legacy_source_hashes"] = _copy_actual_legacy_sources(tmp_path)
    owner = tmp_path / OWNER_SOURCE
    owner.write_bytes(owner.read_bytes() + b"\n# Changed mapping source.\n")
    with pytest.raises(CompileError, match="stale legacy source hash: owner_paths"):
        compile_manifest(tmp_path, manifest)


def test_synthetic_manifest_cannot_pass_real_project_binding_gate(tmp_path: Path) -> None:
    from token_io_decoupling_dev.project_compiler import compile_project_manifest

    manifest = _case(tmp_path)
    manifest["legacy_source_hashes"] = _copy_actual_legacy_sources(tmp_path)
    with pytest.raises(CompileError, match="legacy bindings do not cover"):
        compile_project_manifest(tmp_path, manifest)


def _unapproved_real_binding_candidate(root: Path) -> dict[str, Any]:
    from token_io_decoupling_core.heading_parser import extract_heading

    from token_io_decoupling_dev.legacy import read_legacy_sources
    from token_io_decoupling_dev.review_draft import build_review_draft

    repo = Path(__file__).resolve().parents[2]
    draft = build_review_draft(repo)
    layer_one = "docs/skill/references/coding/layer-01-fundamental-concepts/"
    en_codex = "Codex CLI / ChatGPT Desktop optimizations"
    zh_codex = "Codex CLI / ChatGPT Desktop 特别优化指令"
    selected_paths = {
        item["source_en"]["path"]
        for item in draft["source_units"]
        if item["source_en"]["path"].startswith(layer_one)
    }
    present_codex_paths = {
        item["source_en"]["path"]
        for item in draft["source_units"]
        if item["source_en"]["heading"] == en_codex
    }
    for path in sorted(selected_paths - present_codex_paths):
        unit_id = "fixture.codex." + _digest(path.encode())[:16]
        candidate_unit: dict[str, Any] = {
            "source_unit_id": unit_id,
            "source_kind": "semantic_owner",
        }
        for locale, key, actual_path, heading in (
            ("en", "source_en", path, en_codex),
            ("zh_cn", "source_zh_cn", path.removesuffix(".md") + "_zh_cn.md", zh_codex),
        ):
            raw = (repo / actual_path).read_bytes()
            candidate_unit[key] = {
                "locale": locale,
                "path": actual_path,
                "heading": heading,
                "source_sha256": _digest(raw),
                "excerpt_sha256": _digest(extract_heading(raw.decode(), heading).encode()),
            }
        draft["source_units"].append(candidate_unit)
    units = []
    for item in draft["source_units"]:
        for locale, key in (("en", "source_en"), ("zh_cn", "source_zh_cn")):
            src = item[key]
            if src["path"].startswith(layer_one):
                target = root / src["path"]
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((repo / src["path"]).read_bytes())
            units.append(
                {
                    "source_unit_id": item["source_unit_id"],
                    "source_kind": item["source_kind"],
                    "locale": locale,
                    "source": {"path": src["path"], "heading": src["heading"]},
                    "expected_hashes": {
                        "source_sha256": src["source_sha256"],
                        "excerpt_sha256": src["excerpt_sha256"],
                    },
                    "references": [],
                }
            )
    entries = []
    for locale in ("en", "zh_cn"):
        selector = {
            "source_unit_id": units[0]["source_unit_id"],
            "quote": "unapproved",
            "occurrence": 0,
        }
        entries.append(
            {
                "tool_id": "draft",
                "node_id": "contract",
                "stage_id": "draft",
                "locale": locale,
                "source_unit_ids": [selector["source_unit_id"]],
                "actions": [dict(selector)],
                "branches": [
                    {
                        "id": "draft",
                        **{
                            field: dict(selector)
                            for field in ("trigger", "actions", "pass", "failure")
                        },
                    }
                ],
            }
        )
    return {
        "manifest_format": "token-io-runtime-instructions-manifest/v1",
        "policy_contract_version": 2,
        "legacy_context_index_version": 1,
        "legacy_source_hashes": _copy_actual_legacy_sources(root),
        "legacy_bindings": draft["legacy_bindings"],
        "budgets": {},
        "source_units": units,
        "runtime_entries": entries,
        "owner_views": [
            {
                "legacy_owner_id": owner_id,
                "locale": locale,
                "source_unit_ids": [draft["legacy_bindings"]["owners"][owner_id]],
            }
            for owner_id in read_legacy_sources(repo)["delegation_policy_owners"]
            for locale in ("en", "zh_cn")
        ],
    }


def test_real_project_gate_rejects_missing_legacy_edges(tmp_path: Path) -> None:
    from token_io_decoupling_dev.project_compiler import compile_project_manifest

    candidate = _unapproved_real_binding_candidate(tmp_path)
    with pytest.raises(CompileError, match="legacy dependency graph coverage mismatch"):
        compile_project_manifest(tmp_path, candidate)
    assert not (tmp_path / "mcp-project-dev/generated").exists()


def test_real_project_gate_rejects_misbound_fragment_alias(tmp_path: Path) -> None:
    from token_io_decoupling_dev.project_compiler import compile_project_manifest

    candidate = _unapproved_real_binding_candidate(tmp_path)
    candidate["legacy_bindings"]["fragments"]["contract.actions"] = candidate["legacy_bindings"][
        "fragments"
    ]["mode.actions"]
    with pytest.raises(CompileError, match="legacy fragment binding source mismatch"):
        compile_project_manifest(tmp_path, candidate)


@pytest.mark.parametrize(
    "mutation",
    [
        "none",
        "missing_owner",
        "missing_branch",
        "unknown_branch",
        "missing_codex",
        "owner_missing_codex",
        "claude_section",
        "split_stage",
        "split_tool",
        "unsupported_tool",
        "unsupported_stage",
    ],
)
def test_project_gate_preserves_legacy_metadata_and_checks_branch_coverage(
    tmp_path: Path, monkeypatch: Any, mutation: str
) -> None:
    from token_io_decoupling_dev import project_compiler
    from token_io_decoupling_dev.review_draft import build_review_draft

    repo = Path(__file__).resolve().parents[2]
    draft = build_review_draft(repo)
    candidate = _unapproved_real_binding_candidate(tmp_path)
    units = {(unit["source_unit_id"], unit["locale"]): unit for unit in candidate["source_units"]}
    for unit in draft["source_units"]:
        for locale in ("en", "zh_cn"):
            units[(unit["source_unit_id"], locale)]["semantic_dependencies"] = [
                {key: value for key, value in edge.items() if key != "review_status"}
                for edge in unit["semantic_dependencies"][locale]
                if edge["provenance"]["kind"] == "legacy_index_dependency"
            ]
    if mutation == "missing_owner":
        owner_id = candidate["owner_views"][0]["legacy_owner_id"]
        candidate["owner_views"] = [
            view for view in candidate["owner_views"] if view["legacy_owner_id"] != owner_id
        ]
    if mutation == "claude_section":
        from token_io_decoupling_core.heading_parser import extract_heading

        original = next(
            unit
            for unit in candidate["source_units"]
            if unit["locale"] == "en" and unit["source"]["path"].endswith("child-role-selection.md")
        )
        english_path = original["source"]["path"]
        for locale, path, heading in (
            ("en", english_path, "Claude Code CLI / Claude Desktop optimizations"),
            (
                "zh_cn",
                english_path.removesuffix(".md") + "_zh_cn.md",
                "Claude Code CLI / Claude Desktop 特别优化指令",
            ),
        ):
            raw = (repo / path).read_bytes()
            candidate["source_units"].append(
                {
                    "source_unit_id": "fixture.claude",
                    "source_kind": "semantic_owner",
                    "locale": locale,
                    "source": {"path": path, "heading": heading},
                    "expected_hashes": {
                        "source_sha256": _digest(raw),
                        "excerpt_sha256": _digest(extract_heading(raw.decode(), heading).encode()),
                    },
                    "references": [],
                }
            )
    closure = sorted({unit["source_unit_id"] for unit in candidate["source_units"]})
    entries: list[dict[str, Any]] = [
        {
            "tool_id": "rules_get_context",
            "stage_id": "context",
            "node_id": node["node_id"],
            "locale": locale,
            "closure_source_unit_ids": list(closure),
            "instructions": {
                "branches": [{"legacy_branch": branch} for branch in node["legal_branches"]]
            },
        }
        for node in draft["legacy_node_metadata"]
        for locale in ("en", "zh_cn")
    ]
    owner_views = [
        {
            "legacy_owner_id": view["legacy_owner_id"],
            "locale": view["locale"],
            "closure_source_unit_ids": list(closure),
        }
        for view in candidate["owner_views"]
    ]
    if mutation == "missing_branch":
        entries[0]["instructions"]["branches"].pop()
    elif mutation == "unknown_branch":
        entries[0]["instructions"]["branches"].append({"legacy_branch": "invented"})
    elif mutation in {"missing_codex", "owner_missing_codex"}:
        source_id = next(
            unit["source_unit_id"]
            for unit in candidate["source_units"]
            if unit["locale"] == "en"
            and unit["source"]["heading"] == "Codex CLI / ChatGPT Desktop optimizations"
        )
        target = entries[0] if mutation == "missing_codex" else owner_views[0]
        target["closure_source_unit_ids"].remove(source_id)
    elif mutation in {"split_stage", "split_tool"}:
        second = copy.deepcopy(entries[0])
        second["stage_id"] = "another_context"
        if mutation == "split_tool":
            second["tool_id"] = "invented_owner_policy"
        second["instructions"]["branches"] = [entries[0]["instructions"]["branches"].pop()]
        entries.append(second)
    elif mutation == "unsupported_tool":
        entries[0]["tool_id"] = "invented_owner_policy"
    elif mutation == "unsupported_stage":
        entries[0]["stage_id"] = "unrelated"
    # Isolate the real-source gate; never write the mocked output.
    monkeypatch.setattr(
        project_compiler,
        "compile_manifest",
        lambda _root, _manifest: {
            "runtime_entries": entries,
            "owner_views": owner_views,
            "canonical_sha256": "stub",
        },
    )
    if mutation != "none":
        expected = {
            "missing_codex": "lacks the same-document Codex",
            "owner_missing_codex": "lacks the same-document Codex",
            "claude_section": "outside the MCP boundary",
            "unsupported_tool": "unsupported callable rule-context tool",
            "unsupported_stage": "unsupported rule-context stage",
            "split_stage": "unsupported rule-context stage",
            "split_tool": "unsupported callable rule-context tool",
            "missing_owner": "owner views do not cover",
        }.get(mutation, "legacy legal branch coverage mismatch")
        with pytest.raises(CompileError, match=expected):
            project_compiler.compile_project_manifest(tmp_path, candidate)
    else:
        artifact = project_compiler.compile_project_manifest(tmp_path, candidate)
        metadata = artifact["legacy_metadata"]
        assert len(metadata["nodes"]) == 17
        assert len(metadata["fragments"]) == 44
        assert len(metadata["owner_paths"]) == 8
        assert len(metadata["optional_fragment_owner_bindings"]) == 3
        assert metadata["context_nodes"] == draft["legacy_context_nodes"]
    assert not (tmp_path / "mcp-project-dev/generated").exists()


def test_review_draft_matches_actual_bilingual_sources_and_preclassified_edges() -> None:
    from token_io_decoupling_core.heading_parser import extract_heading

    from token_io_decoupling_dev.review_draft import build_review_draft

    repo = Path(__file__).resolve().parents[2]
    draft = build_review_draft(repo)
    stored = json.loads((repo / "mcp-project-dev/legacy-mapping-review.v1.json").read_text())
    assert json.loads(json.dumps(draft, ensure_ascii=False)) == stored
    assert draft["complete"] is False
    assert len(draft["legacy_node_metadata"]) == 17
    assert len(draft["legacy_bindings"]["fragments"]) == 44
    assert len(draft["legacy_bindings"]["owners"]) == 8
    assert len(draft["optional_fragment_owner_bindings"]) == 3
    assert draft["required_legacy_dependency_records_per_locale"] == 29
    assert all(
        draft["candidate_reference_counts"][kind] > 0
        for kind in (
            "required",
            "conditional",
            "navigation",
            "internal_already_included",
        )
    )
    aliases = draft["legacy_bindings"]["fragments"]
    assert aliases["contract.actions"] == aliases["contract_change.actions"]
    for unit in draft["source_units"]:
        for locale, source_key in (("en", "source_en"), ("zh_cn", "source_zh_cn")):
            source = unit[source_key]
            text = extract_heading((repo / source["path"]).read_text(), source["heading"])
            links = extract_markdown_links(text)
            observed = [(link.raw, link.occurrence, link.label, link.destination) for link in links]
            declared = [
                (
                    item["selector"]["raw"],
                    item["selector"]["occurrence"],
                    item["label"],
                    item["destination"],
                )
                for item in unit["references"][locale]
            ]
            assert declared == observed
            for edge in unit["semantic_dependencies"][locale]:
                if edge["provenance"]["kind"] == "markdown_quote":
                    assert edge["provenance"]["selector"]["quote"] in text
                    if edge["class"] == "conditional":
                        assert edge["trigger_selector"]["quote"] in text
            for reference in unit["references"][locale]:
                if reference["candidate_class"] == "conditional":
                    selector = reference["trigger_selector"]
                    assert selector["source_unit_id"] == unit["source_unit_id"]
                    assert selector["quote"] in text
                    assert text.count(selector["quote"]) > selector["occurrence"]
    assert draft["budget_diagnostics"]["source_unit_records"] <= 512


def test_entry_review_is_current_sourced_and_never_claims_completeness() -> None:
    from token_io_decoupling_core.heading_parser import extract_heading

    from token_io_decoupling_dev.review_entries import build_entry_review

    repo = Path(__file__).resolve().parents[2]
    review = build_entry_review(repo)
    stored = json.loads((repo / "mcp-project-dev/compiler-manifest.review.v1.json").read_text())
    assert json.loads(json.dumps(review, ensure_ascii=False)) == stored
    assert review["complete"] is False
    assert len(review["runtime_entries"]) == 34
    assert len(review["owner_views"]) == 10
    assert not review["diagnostics"]["cycles"]
    assert review["diagnostics"]["unresolved_branch_selector_fields"] == 0
    assert review["diagnostics"]["artifact_bytes_exact"] is None
    diagnostic = review["diagnostics"]["in_memory_compile"]
    assert diagnostic["status"] == "provisional_in_memory_only_requires_root_review"
    assert diagnostic["artifact_bytes_required"] <= diagnostic["artifact_bytes_allowed"]
    assert len(diagnostic["runtime_entries"]) == 34
    assert len(diagnostic["owner_views"]) == 10
    assert all(
        item["required_unicode_chars"] <= item["allowed_unicode_chars"]
        for item in diagnostic["runtime_entries"] + diagnostic["owner_views"]
    )
    draft = json.loads((repo / "mcp-project-dev/legacy-mapping-review.v1.json").read_text())
    units = {unit["source_unit_id"]: unit for unit in draft["source_units"]}
    nodes = {node["node_id"]: node for node in draft["legacy_node_metadata"]}
    for entry in review["runtime_entries"]:
        assert entry["tool_id"] == "rules_get_context" and entry["stage_id"] == "context"
        assert [branch["legacy_branch"] for branch in entry["branches"]] == nodes[entry["node_id"]][
            "legal_branches"
        ]
        assert entry["actions"][0]["source_unit_id"] == "mapping." + entry["node_id"]
        source_key = "source_en" if entry["locale"] == "en" else "source_zh_cn"
        selectors = list(entry["actions"])
        for branch in entry["branches"]:
            for field in ("trigger", "actions", "pass", "failure"):
                assert branch[field]["selector"]["source_unit_id"] == "mapping." + entry["node_id"]
                assert branch[field]["status"] == "proposal_requires_root_review"
                selectors.append(branch[field]["selector"])
                selectors.extend(branch[field]["source_candidates"])
        for selector in selectors:
            source = units[selector["source_unit_id"]][source_key]
            excerpt = extract_heading((repo / source["path"]).read_text(), source["heading"])
            assert excerpt.count(selector["quote"]) > selector["occurrence"]
    for view in review["owner_views"]:
        assert "tool_id" not in view and "branches" not in view and "actions" not in view
        assert view["closure_diagnostic"]["budget"]["exact_required"] is None


@pytest.mark.parametrize("mutation", ["mapping_target", "missing_branch", "missing_provider"])
def test_real_review_proposal_is_rejected_when_required_bindings_are_removed(mutation: str) -> None:
    from token_io_decoupling_dev.project_compiler import compile_project_manifest
    from token_io_decoupling_dev.review_diagnostics import proposed_manifest

    repo = Path(__file__).resolve().parents[2]
    draft = json.loads((repo / "mcp-project-dev/legacy-mapping-review.v1.json").read_text())
    review = json.loads((repo / "mcp-project-dev/compiler-manifest.review.v1.json").read_text())
    manifest = proposed_manifest(draft, review)
    if mutation == "mapping_target":
        for unit in manifest["source_units"]:
            if unit["source_unit_id"] == "mapping.contract":
                unit["references"][0]["target_source_unit_id"] = "mode.actions"
        expected = "destination does not match target source unit"
    elif mutation == "missing_branch":
        for entry in manifest["runtime_entries"]:
            if entry["node_id"] == "contract":
                entry["branches"].pop()
        expected = "legacy legal branch coverage mismatch"
    else:
        for entry in manifest["runtime_entries"]:
            if entry["node_id"] == "output_class":
                entry["source_unit_ids"].remove("owner.session-role-ownership.codex")
        expected = "lacks the same-document Codex"
    with pytest.raises(CompileError, match=expected):
        compile_project_manifest(repo, manifest)


@pytest.mark.parametrize(
    "reference_class", ["required", "conditional", "internal_already_included"]
)
def test_reference_target_must_bind_linked_path_and_anchor(
    tmp_path: Path, reference_class: str
) -> None:
    manifest = _case(tmp_path, reference_class)
    for unit in manifest["source_units"]:
        if unit["source_unit_id"] == "root":
            if reference_class == "internal_already_included":
                unit["references"][0]["included_in_source_unit_id"] = "dependency"
            unit["references"][0]["target_source_unit_id"] = "root"
    with pytest.raises(CompileError, match="does not match target source unit"):
        compile_manifest(tmp_path, manifest)


def test_anchor_must_belong_to_target_source_section(tmp_path: Path) -> None:
    from token_io_decoupling_core.heading_parser import extract_heading

    manifest = _case(tmp_path)
    for unit in manifest["source_units"]:
        if unit["source_unit_id"] == "dependency":
            path = tmp_path / unit["source"]["path"]
            text = path.read_text(encoding="utf-8") + "\n## Unrelated\nDifferent section.\n"
            path.write_text(text, encoding="utf-8")
            unit["expected_hashes"] = {
                "source_sha256": _digest(text.encode()),
                "excerpt_sha256": _digest(
                    extract_heading(text, unit["source"]["heading"]).encode()
                ),
            }
        elif unit["source_unit_id"] == "root":
            _redirect_reference(tmp_path, unit, f"dependency.{unit['locale']}.md#unrelated")
    with pytest.raises(CompileError, match="does not match target source unit"):
        compile_manifest(tmp_path, manifest)


def test_internal_reference_can_point_to_a_unit_already_in_the_entry_closure(
    tmp_path: Path,
) -> None:
    manifest = _case(tmp_path, "internal_already_included")
    for unit in manifest["source_units"]:
        if unit["source_unit_id"] == "root":
            unit["references"][0]["included_in_source_unit_id"] = "dependency"
    for entry in manifest["runtime_entries"]:
        entry["source_unit_ids"].append("dependency")
    assert compile_manifest(tmp_path, manifest)["complete"] is True
    for entry in manifest["runtime_entries"]:
        entry["source_unit_ids"].remove("dependency")
    with pytest.raises(CompileError, match="not already in the final entry closure"):
        compile_manifest(tmp_path, manifest)


def test_local_relative_link_and_nested_anchor_are_accepted(tmp_path: Path) -> None:
    from token_io_decoupling_core.heading_parser import extract_heading

    manifest = _case(tmp_path)
    (tmp_path / "nested").mkdir()
    for unit in manifest["source_units"]:
        path = tmp_path / unit["source"]["path"]
        if unit["source_unit_id"] == "dependency":
            text = path.read_text(encoding="utf-8") + "\n### Detailed checks\nMore required text.\n"
            path.write_text(text, encoding="utf-8")
            unit["expected_hashes"] = {
                "source_sha256": _digest(text.encode()),
                "excerpt_sha256": _digest(
                    extract_heading(text, unit["source"]["heading"]).encode()
                ),
            }
        else:
            new_path = tmp_path / "nested" / path.name
            path.rename(new_path)
            unit["source"]["path"] = new_path.relative_to(tmp_path).as_posix()
            _redirect_reference(
                tmp_path, unit, f"../dependency.{unit['locale']}.md#detailed-checks"
            )
    assert compile_manifest(tmp_path, manifest)["complete"] is True


def test_reference_style_heading_uses_its_visible_text_for_anchor(tmp_path: Path) -> None:
    from token_io_decoupling_core.heading_parser import extract_heading

    manifest = _case(tmp_path)
    for unit in manifest["source_units"]:
        if unit["source_unit_id"] == "dependency":
            path = tmp_path / unit["source"]["path"]
            text = path.read_text(encoding="utf-8")
            text += "\n### [Intro][ref]\nDetails.\n\n[ref]: https://example.com/policy\n"
            path.write_text(text, encoding="utf-8")
            unit["expected_hashes"] = {
                "source_sha256": _digest(text.encode()),
                "excerpt_sha256": _digest(
                    extract_heading(text, unit["source"]["heading"]).encode()
                ),
            }
            unit["references"] = [
                {
                    "class": "navigation",
                    "selector": {"raw": "[Intro][ref]", "occurrence": 0},
                    "label": "Intro",
                    "destination": "https://example.com/policy",
                }
            ]
        else:
            _redirect_reference(tmp_path, unit, f"dependency.{unit['locale']}.md#intro")
    assert compile_manifest(tmp_path, manifest)["complete"] is True
    for unit in manifest["source_units"]:
        if unit["source_unit_id"] == "root":
            _redirect_reference(tmp_path, unit, f"dependency.{unit['locale']}.md#introref")
    with pytest.raises(CompileError, match="anchor is unavailable"):
        compile_manifest(tmp_path, manifest)


def test_ambiguous_image_heading_does_not_claim_an_anchor(tmp_path: Path) -> None:
    manifest = _case(tmp_path, "navigation")
    (tmp_path / "section.md").write_text("## ![Alt](image.png) Heading\nText.\n", encoding="utf-8")
    for entry in manifest["runtime_entries"]:
        entry["source_unit_ids"].append("dependency")
    for unit in manifest["source_units"]:
        if unit["source_unit_id"] == "root":
            unit["references"][0].pop("target_source_unit_id")
            _redirect_reference(tmp_path, unit, "section.md#alt-heading")
    with pytest.raises(CompileError, match="anchor is unavailable"):
        compile_manifest(tmp_path, manifest)


@pytest.mark.parametrize("bad_target", ["missing.md", "dependency.en.md#absent", "../escape.md"])
def test_navigation_local_target_must_exist_and_stay_inside_root(
    tmp_path: Path, bad_target: str
) -> None:
    manifest = _case(tmp_path, "navigation")
    for entry in manifest["runtime_entries"]:
        entry["source_unit_ids"].append("dependency")
    unit = next(
        u for u in manifest["source_units"] if u["source_unit_id"] == "root" and u["locale"] == "en"
    )
    unit["references"][0].pop("target_source_unit_id")
    # Keep the graph shape equal while exercising navigation without a target unit.
    other = next(
        u
        for u in manifest["source_units"]
        if u["source_unit_id"] == "root" and u["locale"] == "zh_cn"
    )
    other["references"][0].pop("target_source_unit_id")
    _redirect_reference(tmp_path, unit, bad_target)
    with pytest.raises(CompileError, match="destination"):
        compile_manifest(tmp_path, manifest)


def test_local_reference_cannot_traverse_symlink(tmp_path: Path) -> None:
    manifest = _case(tmp_path)
    outside = tmp_path.parent / f"{tmp_path.name}-outside.md"
    outside.write_text("## Rules\nOutside.\n", encoding="utf-8")
    (tmp_path / "linked.md").symlink_to(outside)
    unit = next(
        u for u in manifest["source_units"] if u["source_unit_id"] == "root" and u["locale"] == "en"
    )
    _redirect_reference(tmp_path, unit, "linked.md")
    with pytest.raises(CompileError, match="symlink"):
        compile_manifest(tmp_path, manifest)


def test_percent_encoded_local_path_and_unicode_anchor(tmp_path: Path) -> None:
    manifest = _case(tmp_path)
    for unit in manifest["source_units"]:
        if unit["source_unit_id"] == "dependency":
            path = tmp_path / unit["source"]["path"]
            renamed = tmp_path / f"dependency {unit['locale']}.md"
            path.rename(renamed)
            unit["source"]["path"] = renamed.name
        else:
            anchor = "rules" if unit["locale"] == "en" else "%E8%A7%84%E5%88%99"
            _redirect_reference(tmp_path, unit, f"dependency%20{unit['locale']}.md#{anchor}")
    assert compile_manifest(tmp_path, manifest)["complete"] is True


@pytest.mark.parametrize("destination", ["", "section.md#section", "https://example.com/policy"])
def test_navigation_accepts_same_file_setext_anchor_and_external_links(
    tmp_path: Path, destination: str
) -> None:
    manifest = _case(tmp_path, "navigation")
    (tmp_path / "section.md").write_text("Section\n=======\nText.\n", encoding="utf-8")
    for entry in manifest["runtime_entries"]:
        entry["source_unit_ids"].append("dependency")
    for unit in manifest["source_units"]:
        if unit["source_unit_id"] == "root":
            unit["references"][0].pop("target_source_unit_id")
            _redirect_reference(tmp_path, unit, destination)
    assert compile_manifest(tmp_path, manifest)["complete"] is True


def test_external_link_cannot_be_bound_as_execution_dependency(tmp_path: Path) -> None:
    manifest = _case(tmp_path)
    for unit in manifest["source_units"]:
        if unit["source_unit_id"] == "root":
            _redirect_reference(tmp_path, unit, "https://example.com/policy")
    with pytest.raises(CompileError, match="does not match target source unit"):
        compile_manifest(tmp_path, manifest)


def test_large_dependency_is_counted_in_closure_budget(tmp_path: Path) -> None:
    manifest = _case(tmp_path)
    manifest["budgets"]["entry_closure_unicode_chars"] = 10000
    assert compile_manifest(tmp_path, manifest)["complete"] is True
    unit = next(
        u
        for u in manifest["source_units"]
        if u["source_unit_id"] == "dependency" and u["locale"] == "en"
    )
    path = tmp_path / unit["source"]["path"]
    raw = path.read_bytes() + ("\n" + "x" * 12000 + "\n").encode()
    path.write_bytes(raw)
    unit["expected_hashes"] = {
        "source_sha256": _digest(raw),
        "excerpt_sha256": _digest(raw.decode().split("## Rules\n\n", 1)[1].strip().encode()),
    }
    with pytest.raises(CompileError, match="entry closure budget exceeded"):
        compile_manifest(tmp_path, manifest)


@pytest.mark.parametrize(
    "source_name,hash_key",
    [
        ("rule-registry.json", "registry_sha256"),
        ("rule-context-index.json", "context_index_sha256"),
    ],
)
def test_entry_hash_binds_legacy_sources(tmp_path: Path, source_name: str, hash_key: str) -> None:
    manifest = _case(tmp_path)
    before = compile_manifest(tmp_path, manifest)
    path = tmp_path / "mcp" / source_name
    raw = path.read_bytes().replace(b"}", b',"extra":"changed"}')
    path.write_bytes(raw)
    manifest["legacy_source_hashes"][hash_key] = _digest(raw)
    after = compile_manifest(tmp_path, manifest)
    assert _entry(before, "root")["content_sha256"] != _entry(after, "root")["content_sha256"]
    assert _entry(after, "root")["legacy_source_hashes"][hash_key] == _digest(raw)


@pytest.mark.parametrize(
    "constant,new_value",
    [("FORMAT", "new-format/v2"), ("COMPILER_VERSION", 2), ("MANIFEST_FORMAT", "new-manifest/v2")],
)
def test_entry_hash_binds_compilation_format_and_version(
    tmp_path: Path, monkeypatch: Any, constant: str, new_value: Any
) -> None:
    manifest = _case(tmp_path)
    before = compile_manifest(tmp_path, manifest)
    monkeypatch.setattr(compiler, constant, new_value)
    if constant == "MANIFEST_FORMAT":
        manifest["manifest_format"] = new_value
    after = compile_manifest(tmp_path, manifest)
    assert _entry(before, "root")["content_sha256"] != _entry(after, "root")["content_sha256"]


@pytest.mark.parametrize(
    "constant,manifest_field,file_name,version_field,hash_key",
    [
        (
            "POLICY_CONTRACT_VERSION",
            "policy_contract_version",
            "rule-registry.json",
            "contract_version",
            "registry_sha256",
        ),
        (
            "LEGACY_CONTEXT_INDEX_VERSION",
            "legacy_context_index_version",
            "rule-context-index.json",
            "schema_version",
            "context_index_sha256",
        ),
    ],
)
def test_entry_hash_binds_policy_and_context_versions(
    tmp_path: Path,
    monkeypatch: Any,
    constant: str,
    manifest_field: str,
    file_name: str,
    version_field: str,
    hash_key: str,
) -> None:
    manifest = _case(tmp_path)
    before = compile_manifest(tmp_path, manifest)
    version = getattr(compiler, constant) + 1
    monkeypatch.setattr(compiler, constant, version)
    manifest[manifest_field] = version
    path = tmp_path / "mcp" / file_name
    path.write_text(json.dumps({version_field: version}), encoding="utf-8")
    manifest["legacy_source_hashes"][hash_key] = _digest(path.read_bytes())
    after = compile_manifest(tmp_path, manifest)
    assert _entry(before, "root")["content_sha256"] != _entry(after, "root")["content_sha256"]
    assert _entry(after, "root")[manifest_field] == version


def test_related_concepts_links_are_not_hidden() -> None:
    links = extract_markdown_links("## Related concepts\nSee [Owner](owner.md).\n")
    assert [(link.label, link.destination) for link in links] == [("Owner", "owner.md")]


def test_nonexclusive_language_pair_and_reference_definitions_are_inventoried() -> None:
    text = (
        "Read [English](en.md) | [简体中文](zh.md) for more.\n"
        "[Path][ref]\n\n[ref]: <file&amp;name.md>\n[ref]: ignored.md\n"
    )
    assert [(link.label, link.destination) for link in extract_markdown_links(text)] == [
        ("English", "en.md"),
        ("简体中文", "zh.md"),
        ("Path", "file&name.md"),
    ]


@pytest.mark.parametrize(
    "text",
    [
        "```invalid ` info\n[Required](required.md)\n",
        "``unclosed ``` still visible [Required](required.md) ` end\n",
        "[ref]:\n\n[Required](required.md)\n",
        "[ref]: path garbage [Required](required.md)\n",
        r"\\[Required](required.md)" + "\n",
    ],
)
def test_invalid_code_or_reference_syntax_cannot_hide_real_links(text: str) -> None:
    assert any(link.destination == "required.md" for link in extract_markdown_links(text))


@pytest.mark.parametrize(
    "text",
    [
        "```invalid ` info\n[Unclassified](extra.md)\n",
        "``unclosed ``` still visible [Unclassified](extra.md) ` end\n",
        "[ref]:\n\n[Unclassified](extra.md)\n",
    ],
)
def test_unclassified_links_in_invalid_code_or_reference_syntax_fail_compilation(
    tmp_path: Path, text: str
) -> None:
    from token_io_decoupling_core.heading_parser import extract_heading

    manifest = _case(tmp_path)
    unit = next(
        item
        for item in manifest["source_units"]
        if item["source_unit_id"] == "root" and item["locale"] == "en"
    )
    path = tmp_path / unit["source"]["path"]
    updated = path.read_text(encoding="utf-8") + "\n" + text
    path.write_text(updated, encoding="utf-8")
    unit["expected_hashes"] = {
        "source_sha256": _digest(updated.encode()),
        "excerpt_sha256": _digest(extract_heading(updated, unit["source"]["heading"]).encode()),
    }
    with pytest.raises(CompileError, match="coverage"):
        compile_manifest(tmp_path, manifest)


def test_language_mentions_do_not_hide_required_markdown_links() -> None:
    source = "## Actions\nUse English / 简体中文 and [Required](required.md) before proceeding.\n"
    links = extract_markdown_links(source)
    assert [(link.raw, link.label, link.destination) for link in links] == [
        ("[Required](required.md)", "Required", "required.md")
    ]


def test_only_a_standalone_paired_language_switch_is_ignored() -> None:
    source = (
        "[English](SKILL.md) | [简体中文](SKILL_zh_cn.md)\n"
        "## Actions\n"
        "English guidance links to [Evidence](evidence.md).\n"
    )
    links = extract_markdown_links(source)
    assert [(link.label, link.destination) for link in links] == [("Evidence", "evidence.md")]


@pytest.mark.parametrize(
    "row",
    [
        "[English](required.md) | [简体中文](unrelated.md)",
        "[English](a/owner.md) | [简体中文](b/owner_zh_cn.md)",
        "[English](https://example.com/owner.md) | [简体中文](https://example.com/owner_zh_cn.md)",
    ],
)
def test_only_corresponding_local_mirror_paths_are_exempt_language_switches(row: str) -> None:
    assert len(extract_markdown_links(row + "\n")) == 2


def test_markdown_autolinks_are_in_the_reference_inventory() -> None:
    links = extract_markdown_links("Read <https://example.com/policy> and <agent@example.com>.\n")
    assert [link.destination for link in links] == [
        "https://example.com/policy",
        "agent@example.com",
    ]


@pytest.mark.parametrize("token", ["NaN", "Infinity", "-Infinity"])
def test_strict_json_rejects_non_json_numeric_constants(tmp_path: Path, token: str) -> None:
    path = tmp_path / "input.json"
    path.write_text('{"value":' + token + "}", encoding="utf-8")
    with pytest.raises(CompileError):
        load_json_strict(path)


@pytest.mark.parametrize("value", [True, 1.0, "1"])
def test_publication_rejects_non_integer_compiler_version_even_with_matching_hash(
    tmp_path: Path, value: Any
) -> None:
    artifact = compile_manifest(tmp_path, _case(tmp_path))
    artifact["compiler_version"] = value
    body = {key: item for key, item in artifact.items() if key != "canonical_sha256"}
    artifact["canonical_sha256"] = compiler._sha(compiler._canonical(body))
    with pytest.raises(CompileError, match="artifact format"):
        write_fixed_output(tmp_path, artifact)
    assert not (tmp_path / "mcp-project-dev/generated").exists()


def test_wrong_baseline_cannot_be_bypassed_by_identical_content(tmp_path: Path) -> None:
    artifact = compile_manifest(tmp_path, _case(tmp_path))
    path = write_fixed_output(tmp_path, artifact)
    before = path.stat()
    raw = path.read_bytes()
    with pytest.raises(CompileError, match="baseline"):
        write_fixed_output(tmp_path, artifact, expected_baseline_sha256="0" * 64)
    assert path.read_bytes() == raw
    assert path.stat().st_ino == before.st_ino
    assert path.stat().st_mtime_ns == before.st_mtime_ns


def test_expected_existing_baseline_cannot_create_missing_target(tmp_path: Path) -> None:
    artifact = compile_manifest(tmp_path, _case(tmp_path))
    with pytest.raises(CompileError, match="baseline"):
        write_fixed_output(
            tmp_path, artifact, expected_baseline_sha256=artifact["canonical_sha256"]
        )
    assert not fixed_output_path(tmp_path).exists()


def test_identical_artifact_is_a_no_op(tmp_path: Path) -> None:
    artifact = compile_manifest(tmp_path, _case(tmp_path))
    path = write_fixed_output(tmp_path, artifact)
    before = path.stat()
    assert write_fixed_output(tmp_path, artifact) == path
    assert path.stat().st_ino == before.st_ino
    assert path.stat().st_mtime_ns == before.st_mtime_ns


@pytest.mark.parametrize("mutation", ["incomplete", "hash", "entry"])
def test_invalid_artifact_is_rejected_before_output_creation(tmp_path: Path, mutation: str) -> None:
    artifact = compile_manifest(tmp_path, _case(tmp_path))
    if mutation == "incomplete":
        artifact["complete"] = False
    elif mutation == "hash":
        artifact["canonical_sha256"] = "0" * 64
    else:
        artifact["runtime_entries"][0]["instructions"]["actions"] = [
            {"text": "unverified replacement"}
        ]
    with pytest.raises(CompileError):
        write_fixed_output(tmp_path, artifact)
    assert not (tmp_path / "mcp-project-dev/generated").exists()


@pytest.mark.parametrize("kind", ["source_unit", "entry", "owner_view"])
def test_publication_rejects_nested_tampering_even_with_rehashed_envelope(
    tmp_path: Path, kind: str
) -> None:
    artifact = compile_manifest(tmp_path, _owner_view_case(tmp_path))
    if kind == "source_unit":
        artifact["source_units"][0]["excerpt"] += " unverified"
    elif kind == "entry":
        artifact["runtime_entries"][0]["tool_id"] = "tampered"
    else:
        artifact["owner_views"][0]["legacy_owner_id"] = "tampered"
    body = {key: value for key, value in artifact.items() if key != "canonical_sha256"}
    artifact["canonical_sha256"] = compiler._sha(compiler._canonical(body))
    with pytest.raises(CompileError, match="integrity"):
        write_fixed_output(tmp_path, artifact)
    assert not (tmp_path / "mcp-project-dev/generated").exists()


@pytest.mark.parametrize("category", ["runtime_entries", "owner_views"])
def test_publication_rejects_wrong_closure_hash_even_with_rehashed_containers(
    tmp_path: Path, category: str
) -> None:
    artifact = compile_manifest(tmp_path, _owner_view_case(tmp_path))
    item = artifact[category][0]
    item["closure_sha256"] = "0" * 64
    body = {key: value for key, value in item.items() if key != "content_sha256"}
    item["content_sha256"] = compiler._sha(compiler._canonical(body))
    envelope = {key: value for key, value in artifact.items() if key != "canonical_sha256"}
    artifact["canonical_sha256"] = compiler._sha(compiler._canonical(envelope))
    with pytest.raises(CompileError, match="transitive closure integrity"):
        write_fixed_output(tmp_path, artifact)
    assert not (tmp_path / "mcp-project-dev/generated").exists()


def test_symbolic_link_output_is_never_followed(tmp_path: Path) -> None:
    artifact = compile_manifest(tmp_path, _case(tmp_path))
    output = fixed_output_path(tmp_path)
    output.parent.mkdir(parents=True)
    outside = tmp_path / "outside.json"
    outside.write_text("private synthetic data", encoding="utf-8")
    output.symlink_to(outside)
    with pytest.raises(CompileError):
        write_fixed_output(tmp_path, artifact)
    assert outside.read_text() == "private synthetic data"
    assert output.is_symlink()


def test_special_output_is_rejected_without_reading_it(tmp_path: Path) -> None:
    artifact = compile_manifest(tmp_path, _case(tmp_path))
    output = fixed_output_path(tmp_path)
    output.mkdir(parents=True)
    with pytest.raises(CompileError):
        write_fixed_output(tmp_path, artifact)
    assert output.is_dir()


def test_foreign_temporary_file_is_preserved(tmp_path: Path) -> None:
    artifact = compile_manifest(tmp_path, _case(tmp_path))
    output = fixed_output_path(tmp_path)
    output.parent.mkdir(parents=True)
    temporary = output.with_name(output.name + ".tmp")
    temporary.write_bytes(b"another operation owns this file")
    with pytest.raises(CompileError):
        write_fixed_output(tmp_path, artifact)
    assert temporary.read_bytes() == b"another operation owns this file"
    assert not output.exists()


def test_failed_atomic_replace_preserves_prior_artifact(tmp_path: Path, monkeypatch: Any) -> None:
    manifest = _case(tmp_path)
    artifact = compile_manifest(tmp_path, manifest)
    output = write_fixed_output(tmp_path, artifact)
    raw = output.read_bytes()
    _change_source(tmp_path, manifest, "dependency")
    replacement = compile_manifest(tmp_path, manifest)

    def fail(*_args: Any, **_kwargs: Any) -> None:
        raise OSError("synthetic publication failure")

    monkeypatch.setattr(compiler.os, "replace", fail)
    with pytest.raises(CompileError):
        write_fixed_output(
            tmp_path, replacement, expected_baseline_sha256=artifact["canonical_sha256"]
        )
    assert output.read_bytes() == raw
    assert not output.with_name(output.name + ".tmp").exists()


def test_absent_baseline_does_not_overwrite_a_racing_creator(
    tmp_path: Path, monkeypatch: Any
) -> None:
    artifact = compile_manifest(tmp_path, _case(tmp_path))
    original_link = os.link

    def race(source: str, destination: str, **kwargs: Any) -> None:
        fd = os.open(
            destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=kwargs["dst_dir_fd"]
        )
        with os.fdopen(fd, "wb") as stream:
            stream.write(b"concurrent creator")
        original_link(source, destination, **kwargs)

    monkeypatch.setattr(compiler.os, "link", race)
    with pytest.raises(CompileError):
        write_fixed_output(tmp_path, artifact)
    output = fixed_output_path(tmp_path)
    assert output.read_bytes() == b"concurrent creator"
    assert not output.with_name(output.name + ".tmp").exists()

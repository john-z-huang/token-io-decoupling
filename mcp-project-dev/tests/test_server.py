from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from mcp import Client, StdioServerParameters
from mcp.types import TextContent

from token_io_decoupling_dev.compiler import (
    CompileError,
    compile_manifest,
    fixed_output_path,
    load_json_strict,
    write_fixed_output,
)
from token_io_decoupling_dev.legacy import build_legacy_mapping_draft
from token_io_decoupling_dev.server import (
    SERVER_DESCRIPTION,
    SERVER_INSTRUCTIONS,
    SERVER_NAME,
    TOOL_DESCRIPTION,
    create_server,
    dev_capabilities,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PROJECT_ROOT / "src"


def _result_payload(result: Any) -> dict[str, Any]:
    structured = getattr(result, "structured_content", None)
    if structured is not None:
        return structured
    for item in result.content:
        if isinstance(item, TextContent):
            return json.loads(item.text)
    raise AssertionError("tool result contained neither structured content nor JSON text")


def test_capability_inventory_is_stable_truthful_and_fresh() -> None:
    first = dev_capabilities()
    first["unavailable"].clear()

    second = dev_capabilities()
    assert second["status"] == "unconfigured"
    assert [item["id"] for item in second["implemented"]] == ["dev_capabilities"]
    assert {item["id"] for item in second["unavailable"]} == {
        "project_compliance_checks",
        "output_materialization",
        "rule_compiler",
    }
    assert all(item["status"] == "unavailable" for item in second["unavailable"])
    assert second["side_effects"] == {
        "network": False,
        "openai_api": False,
        "filesystem_read": False,
        "filesystem_write": False,
        "git_or_github": False,
        "memory_read_or_write": False,
    }


def test_in_process_server_exposes_only_no_argument_capability_tool() -> None:
    async def inspect_server() -> None:
        async with Client(create_server(), mode="auto") as client:
            assert client.server_info is not None
            assert client.server_info.name == SERVER_NAME
            assert client.server_info.version == "0.1.0"
            assert client.server_info.description == SERVER_DESCRIPTION
            assert client.instructions == SERVER_INSTRUCTIONS

            listed = await client.list_tools()
            assert [tool.name for tool in listed.tools] == ["dev_capabilities"]
            tool = listed.tools[0]
            assert tool.input_schema["additionalProperties"] is False
            assert tool.description == TOOL_DESCRIPTION
            assert tool.annotations is not None
            assert tool.annotations.read_only_hint is True
            assert tool.annotations.destructive_hint is False
            assert tool.annotations.idempotent_hint is True
            assert tool.annotations.open_world_hint is False
            assert tool.input_schema["properties"] == {}
            assert tool.input_schema.get("required", []) == []

            result = await client.call_tool("dev_capabilities", {})
            assert not result.is_error
            assert _result_payload(result) == dev_capabilities()

    asyncio.run(inspect_server())


def test_negotiated_stdio_startup_and_call_without_project_side_effects(tmp_path: Path) -> None:
    async def inspect_stdio() -> None:
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "token_io_decoupling_dev", "--stdio"],
            env={
                **os.environ,
                "PYTHONPATH": str(SOURCE_ROOT),
                "PYTHONDONTWRITEBYTECODE": "1",
                "HOME": str(tmp_path / "home"),
            },
            cwd=str(tmp_path),
        )
        async with Client(params, mode="auto") as client:
            assert client.server_info is not None
            assert client.server_info.name == SERVER_NAME
            assert client.instructions == SERVER_INSTRUCTIONS
            listed = await client.list_tools()
            assert [tool.name for tool in listed.tools] == ["dev_capabilities"]
            tool = listed.tools[0]
            assert tool.annotations is not None
            assert tool.annotations.read_only_hint is True
            assert tool.annotations.destructive_hint is False
            assert tool.annotations.idempotent_hint is True
            assert tool.annotations.open_world_hint is False
            result = await client.call_tool("dev_capabilities", {})
            assert not result.is_error
            assert _result_payload(result)["status"] == "unconfigured"
            assert (await client.call_tool("dev_capabilities", {"root": "/tmp/other"})).is_error

    asyncio.run(inspect_stdio())
    assert list(tmp_path.iterdir()) == []


def test_cli_help_version_and_default_stdio_contract() -> None:
    env = {
        **os.environ,
        "PYTHONPATH": str(SOURCE_ROOT),
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    help_result = subprocess.run(
        [sys.executable, "-m", "token_io_decoupling_dev", "--help"],
        cwd=PROJECT_ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert help_result.returncode == 0
    assert "--stdio" in help_result.stdout
    assert "--project-root" in help_result.stdout
    assert "stdio" in help_result.stdout

    version_result = subprocess.run(
        [sys.executable, "-m", "token_io_decoupling_dev", "--version"],
        cwd=PROJECT_ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert version_result.returncode == 0
    assert version_result.stdout.strip() == "0.1.0"


def test_cli_rejects_relative_or_invalid_project_roots(tmp_path: Path) -> None:
    env = {**os.environ, "PYTHONPATH": str(SOURCE_ROOT), "PYTHONDONTWRITEBYTECODE": "1"}
    for root in ("relative-root", str(tmp_path)):
        result = subprocess.run(
            [sys.executable, "-m", "token_io_decoupling_dev", "--project-root", root],
            cwd=tmp_path,
            env=env,
            check=False,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 2
        assert "project root" in result.stderr


def test_real_cli_stdio_configured_root_exposes_fixed_argument_tools(tmp_path: Path) -> None:
    _manifest(tmp_path)

    async def inspect_stdio() -> None:
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "token_io_decoupling_dev", "--project-root", str(tmp_path)],
            env={**os.environ, "PYTHONPATH": str(SOURCE_ROOT), "PYTHONDONTWRITEBYTECODE": "1"},
            cwd=str(tmp_path),
        )
        async with Client(params, mode="auto") as client:
            listed = await client.list_tools()
            assert [tool.name for tool in listed.tools] == [
                "dev_capabilities",
                "compile_runtime_instructions",
                "check_runtime_instructions_freshness",
            ]
            assert all(tool.input_schema["properties"] == {} for tool in listed.tools)
            assert all(tool.input_schema["additionalProperties"] is False for tool in listed.tools)
            assert listed.tools[1].annotations is not None
            assert listed.tools[1].annotations.destructive_hint is True
            for tool in listed.tools:
                rejected = await client.call_tool(tool.name, {"project_root": "/tmp/other"})
                assert rejected.is_error
            capabilities = _result_payload(await client.call_tool("dev_capabilities", {}))
            assert capabilities["configured_root"] is True
            result = _result_payload(await client.call_tool("compile_runtime_instructions", {}))
            assert result["status"] == "failed"
            assert result["partial_artifact"] is False
            result = _result_payload(
                await client.call_tool("check_runtime_instructions_freshness", {})
            )
            assert result["status"] == "failed"
            assert result["fresh"] is False

    asyncio.run(inspect_stdio())
    assert not (tmp_path / "mcp-project-dev/generated").exists()


def test_project_root_identity_is_pinned(tmp_path: Path) -> None:
    from token_io_decoupling_dev.project_root import PinnedProjectRoot

    root = tmp_path / "project"
    root.mkdir()
    manifest, _ = _manifest(root)
    artifact = compile_manifest(root, manifest)
    pinned = PinnedProjectRoot.open(root)
    root.rename(tmp_path / "original")
    root.mkdir()
    with pytest.raises(CompileError, match="identity changed"):
        pinned.verify()
    with pytest.raises(CompileError, match="identity changed"):
        write_fixed_output(root, artifact, expected_root_identity=pinned.identity)
    assert not (root / "mcp-project-dev").exists()


def test_freshness_reports_missing_fresh_stale_and_unsafe_output(
    tmp_path: Path, monkeypatch: Any
) -> None:
    import token_io_decoupling_dev.server as server_module

    manifest, _ = _manifest(tmp_path)
    artifact = compile_manifest(tmp_path, manifest)
    path = tmp_path / "mcp-project-dev/compiler-manifest.v1.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    # This isolates status/read behavior; the actual project gate is tested separately.
    monkeypatch.setattr(
        server_module, "compile_project_manifest", lambda _root, _manifest: artifact
    )

    async def exercise() -> None:
        async with Client(create_server(tmp_path), mode="auto") as client:

            async def status() -> str:
                return _result_payload(
                    await client.call_tool("check_runtime_instructions_freshness", {})
                )["status"]

            assert await status() == "missing"
            output = write_fixed_output(tmp_path, artifact)
            assert await status() == "fresh"
            output.write_text("{}", encoding="utf-8")
            assert await status() == "stale"
            output.unlink()
            outside = tmp_path / "outside.json"
            outside.write_text("{}", encoding="utf-8")
            output.symlink_to(outside)
            assert await status() == "failed"
            assert outside.read_text(encoding="utf-8") == "{}"

    asyncio.run(exercise())


def test_runtime_dependency_boundary_is_standalone() -> None:
    import tomllib

    project = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text())
    dependencies = project["project"]["dependencies"]
    assert dependencies == ["mcp>=2.3,<3", "token-io-decoupling-core==0.1.0"]
    assert project["project"]["name"] == "token-io-decoupling-dev"
    assert project["project"]["scripts"]["token-io-decoupling-dev"] == (
        "token_io_decoupling_dev.cli:main"
    )


def test_source_imports_do_not_depend_on_product_runtime() -> None:
    import ast

    forbidden = {
        "token_io_decoupling",
        "token_io_decoupling_state",
        "token_io_decoupling_workflow",
        "token_io_decoupling_root",
        "token_io_decoupling_worker",
    }
    for source in (PROJECT_ROOT / "src").rglob("*.py"):
        tree = ast.parse(source.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                roots = {alias.name.split(".", 1)[0] for alias in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                roots = {node.module.split(".", 1)[0]}
            else:
                continue
            assert roots.isdisjoint(forbidden), f"product runtime import in {source}: {roots}"


def _manifest(tmp_path: Path) -> tuple[dict[str, Any], Path]:
    import hashlib

    marker = tmp_path / "mcp-project-dev/pyproject.toml"
    marker.parent.mkdir()
    marker.write_text('[project]\nname = "token-io-decoupling-dev"\n', encoding="utf-8")
    owner_relative = (
        "mcp/packages/token_io_decoupling_core/src/token_io_decoupling_core/owner_paths.py"
    )
    owner = tmp_path / owner_relative
    owner.parent.mkdir(parents=True)
    owner.write_bytes((PROJECT_ROOT.parent / owner_relative).read_bytes())
    legacy_dir = tmp_path / "mcp"
    legacy_dir.mkdir(exist_ok=True)
    registry = legacy_dir / "rule-registry.json"
    context_index = legacy_dir / "rule-context-index.json"
    registry.write_text('{"contract_version":2}', encoding="utf-8")
    context_index.write_text('{"schema_version":1}', encoding="utf-8")
    units = []
    entries = []
    for locale, path, heading, text in (
        ("en", "source.md", "Rules", "Do the action."),
        ("zh_cn", "source_zh.md", "规则", "执行动作。"),
    ):
        raw = f"# Source\n\n## {heading}\n\n{text}\n".encode()
        (tmp_path / path).write_bytes(raw)
        selector = {"source_unit_id": "source", "quote": text, "occurrence": 0}
        units.append(
            {
                "source_unit_id": "source",
                "source_kind": "fragment",
                "locale": locale,
                "source": {"path": path, "heading": heading},
                "expected_hashes": {
                    "source_sha256": hashlib.sha256(raw).hexdigest(),
                    "excerpt_sha256": hashlib.sha256(text.encode()).hexdigest(),
                },
                "references": [],
            }
        )
        entries.append(
            {
                "tool_id": "test_tool",
                "node_id": "contract",
                "stage_id": "stage_a",
                "locale": locale,
                "source_unit_ids": ["source"],
                "actions": [dict(selector)],
                "branches": [
                    {
                        "id": "ready",
                        "trigger": dict(selector),
                        "actions": dict(selector),
                        "pass": dict(selector),
                        "failure": dict(selector),
                    }
                ],
            }
        )
    manifest = {
        "manifest_format": "token-io-runtime-instructions-manifest/v1",
        "policy_contract_version": 2,
        "legacy_context_index_version": 1,
        "legacy_source_hashes": {
            "registry_sha256": hashlib.sha256(registry.read_bytes()).hexdigest(),
            "context_index_sha256": hashlib.sha256(context_index.read_bytes()).hexdigest(),
        },
        "budgets": {},
        "source_units": units,
        "runtime_entries": entries,
    }
    return manifest, tmp_path


def _append_bilingual_reference(manifest: dict[str, Any], reference: dict[str, Any]) -> None:
    for unit in manifest["source_units"]:
        unit["references"] = [*unit["references"], dict(reference)]


def _update_source(root: Path, unit: dict[str, Any], body: str) -> None:
    import hashlib

    raw = f"# Source\n\n## {unit['source']['heading']}\n\n{body}\n".encode()
    (root / unit["source"]["path"]).write_bytes(raw)
    unit["expected_hashes"] = {
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "excerpt_sha256": hashlib.sha256(body.encode()).hexdigest(),
    }


def _self_conditional_cycle(manifest: dict[str, Any], root: Path) -> None:
    for unit, entry in zip(manifest["source_units"], manifest["runtime_entries"], strict=True):
        anchor = "rules" if unit["locale"] == "en" else "规则"
        destination = f"{unit['source']['path']}#{anchor}"
        raw = f"[Self]({destination})"
        _update_source(root, unit, entry["actions"][0]["quote"] + "\n" + raw)
        unit["references"] = [
            {
                "class": "conditional",
                "selector": {"raw": raw, "occurrence": 0},
                "label": "Self",
                "destination": destination,
                "target_source_unit_id": "source",
                "condition_id": "always",
                "trigger_selector": dict(entry["actions"][0]),
            }
        ]


def test_compiler_is_deterministic_and_hash_binds_provenance(tmp_path: Path) -> None:
    import copy

    manifest, root = _manifest(tmp_path)
    first = compile_manifest(root, manifest)
    second = compile_manifest(root, manifest)
    assert first == second
    reordered = copy.deepcopy(manifest)
    reordered["source_units"].reverse()
    reordered["runtime_entries"].reverse()
    assert compile_manifest(root, reordered) == first
    entry = first["runtime_entries"][0]
    unit = first["source_units"][0]
    assert unit["source"]["path"] == "source.md"
    assert unit["excerpt"] == "Do the action."
    assert len(unit["source_sha256"]) == 64
    assert len(unit["excerpt_sha256"]) == 64
    assert len(entry["content_sha256"]) == 64
    assert first["format"] == "token-io-runtime-instructions/v1"
    assert first["complete"] is True


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda m, r: m.update(manifest_format="unknown/v9"), "unsupported manifest format"),
        (lambda m, r: m.update(policy_contract_version=3), "unsupported policy contract"),
        (lambda m, r: m.update(legacy_context_index_version=9), "unsupported legacy context-index"),
        (
            lambda m, r: m["legacy_source_hashes"].update(registry_sha256="0" * 64),
            "stale legacy source hash",
        ),
        (lambda m, r: _append_bilingual_reference(m, {"target": "missing"}), "unclassified"),
        (
            lambda m, r: _append_bilingual_reference(
                m,
                {
                    "class": "required",
                    "selector": {"raw": "[Missing](missing.md)", "occurrence": 0},
                    "label": "Missing",
                    "destination": "missing.md",
                    "target_source_unit_id": "missing",
                },
            ),
            "missing referenced source unit",
        ),
        (
            lambda m, r: _self_conditional_cycle(m, r),
            "execution source-unit cycle",
        ),
        (
            lambda m, r: _append_bilingual_reference(
                m,
                {
                    "class": "conditional",
                    "selector": {"raw": "[Self](#rules)", "occurrence": 0},
                    "label": "Self",
                    "destination": "#rules",
                    "target_source_unit_id": "source",
                    "condition_id": "",
                    "trigger_selector": {
                        "source_unit_id": "source",
                        "quote": "Do the action.",
                        "occurrence": 0,
                    },
                },
            ),
            "stable ID",
        ),
        (
            lambda m, r: m["runtime_entries"][0]["branches"].append(
                dict(m["runtime_entries"][0]["branches"][0])
            ),
            "duplicate branch ID",
        ),
        (
            lambda m, r: m["source_units"][0]["source"].update(path="../outside.md"),
            "unsafe source path",
        ),
        (
            lambda m, r: m["source_units"][0]["expected_hashes"].update(source_sha256="0" * 64),
            "stale source hashes",
        ),
        (
            lambda m, r: m["budgets"].update(entry_closure_unicode_chars=2),
            "entry closure budget exceeded",
        ),
        (lambda m, r: m["budgets"].update(artifact_bytes=10), "artifact budget exceeded"),
        (lambda m, r: m["budgets"].update(source_unit_records=1), "source unit budget exceeded"),
    ],
)
def test_compiler_fails_closed_for_invalid_input(
    tmp_path: Path, mutation: Any, message: str
) -> None:
    manifest, root = _manifest(tmp_path)
    mutation(manifest, root)
    with pytest.raises(CompileError, match=message):
        compile_manifest(root, manifest)


def test_duplicate_json_keys_are_rejected(tmp_path: Path) -> None:
    path = tmp_path / "duplicate.json"
    path.write_text('{"schema_version":1,"schema_version":1}', encoding="utf-8")
    with pytest.raises(CompileError, match="duplicate JSON key"):
        load_json_strict(path)


def test_symlink_source_escape_is_rejected(tmp_path: Path) -> None:
    manifest, root = _manifest(tmp_path)
    outside = tmp_path.parent / "outside-source.md"
    outside.write_text("## Rules\nsource", encoding="utf-8")
    link = root / "linked.md"
    link.symlink_to(outside)
    manifest["source_units"][0]["source"]["path"] = "linked.md"
    with pytest.raises(CompileError, match="symlink"):
        compile_manifest(root, manifest)


def test_fixed_output_baseline_and_parent_symlinks_are_checked(tmp_path: Path) -> None:
    manifest, root = _manifest(tmp_path)
    original = compile_manifest(root, manifest)
    write_fixed_output(root, original)
    source = root / "source.md"
    source.write_text("# Source\n\n## Rules\n\nChanged action.\n", encoding="utf-8")
    import hashlib

    manifest["source_units"][0]["expected_hashes"] = {
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "excerpt_sha256": hashlib.sha256(b"Changed action.").hexdigest(),
    }
    for entry in manifest["runtime_entries"]:
        if entry["locale"] == "en":
            entry["actions"][0]["quote"] = "Changed action."
            for selector in entry["branches"][0].values():
                if isinstance(selector, dict):
                    selector["quote"] = "Changed action."
    changed = compile_manifest(root, manifest)
    with pytest.raises(CompileError, match="baseline conflict"):
        write_fixed_output(root, changed)
    write_fixed_output(root, changed, expected_baseline_sha256=original["canonical_sha256"])
    assert load_json_strict(fixed_output_path(root)) == changed

    escape_root = tmp_path / "escape-root"
    escape_root.mkdir()
    outside = tmp_path / "outside-generated"
    outside.mkdir()
    project_dir = escape_root / "mcp-project-dev"
    project_dir.mkdir()
    (project_dir / "generated").symlink_to(outside, target_is_directory=True)
    with pytest.raises(CompileError, match="symlink"):
        write_fixed_output(escape_root, changed)


def test_legacy_adapter_emits_review_draft_for_all_stable_ids() -> None:
    root = PROJECT_ROOT.parent
    draft = build_legacy_mapping_draft(root)
    assert draft["review_status"] == "DRAFT_REQUIRES_ROOT_REVIEW"
    assert len(draft["nodes"]) == 17
    assert len(draft["fragments"]) == 44
    assert len(draft["owner_mappings"]) == 8
    assert all(
        item["reference_classification"] == "UNCLASSIFIED_REQUIRES_ROOT_REVIEW"
        for item in draft["fragments"]
    )
    from token_io_decoupling_core.heading_parser import extract_heading
    from token_io_decoupling_core.owner_paths import OWNER_PATHS

    optional_sources = {
        "decision.workflow_routing_advice": OWNER_PATHS["workflow-routing-advice"],
        "implementation.candidate_compliance": OWNER_PATHS["candidate-compliance"],
        "implementation.output_materialization": OWNER_PATHS["output-materialization"],
    }
    for item in draft["fragments"]:
        if item["legacy_fragment_id"] in optional_sources:
            assert item["source_en"]["path"] == optional_sources[item["legacy_fragment_id"]]
            assert (
                item["source_zh_cn"]["path"]
                == optional_sources[item["legacy_fragment_id"]].removesuffix(".md") + "_zh_cn.md"
            )
        for locale_key in ("source_en", "source_zh_cn"):
            source = item[locale_key]
            text = (root / source["path"]).read_text(encoding="utf-8")
            assert extract_heading(text, source["heading"]).strip()
            assert len(source["source_sha256"]) == 64
            assert len(source["excerpt_sha256"]) == 64


def test_navigation_cycles_are_not_execution_cycles(tmp_path: Path) -> None:
    import copy

    manifest, root = _manifest(tmp_path)
    for unit, entry in list(
        zip(manifest["source_units"], manifest["runtime_entries"], strict=True)
    ):
        second = copy.deepcopy(unit)
        second["source_unit_id"] = "other"
        second["source"]["path"] = f"other.{unit['locale']}.md"
        anchor = "rules" if unit["locale"] == "en" else "规则"
        original_dest = f"{unit['source']['path']}#{anchor}"
        other_dest = f"{second['source']['path']}#{anchor}"
        for current, destination, target_id in (
            (unit, other_dest, "other"),
            (second, original_dest, "source"),
        ):
            raw = f"[Link]({destination})"
            _update_source(root, current, entry["actions"][0]["quote"] + "\n" + raw)
            current["references"] = [
                {
                    "class": "navigation",
                    "selector": {"raw": raw, "occurrence": 0},
                    "label": "Link",
                    "destination": destination,
                    "target_source_unit_id": target_id,
                }
            ]
        second_entry = copy.deepcopy(entry)
        second_entry["stage_id"] = "stage_b"
        second_entry["source_unit_ids"] = ["other"]
        for selector in [
            *second_entry["actions"],
            *(
                second_entry["branches"][0][field]
                for field in ("trigger", "actions", "pass", "failure")
            ),
        ]:
            selector["source_unit_id"] = "other"
        manifest["source_units"].append(second)
        manifest["runtime_entries"].append(second_entry)
    artifact = compile_manifest(root, manifest)
    assert artifact["complete"] is True
    assert len(artifact["runtime_entries"]) == 4


def test_duplicate_entry_and_branch_ids_are_rejected(tmp_path: Path) -> None:
    import copy

    manifest, root = _manifest(tmp_path)
    manifest["runtime_entries"].append(copy.deepcopy(manifest["runtime_entries"][0]))
    with pytest.raises(CompileError, match="duplicate runtime entry ID"):
        compile_manifest(root, manifest)


def test_configured_server_registers_fixed_no_argument_tools(tmp_path: Path) -> None:
    manifest, _ = _manifest(tmp_path)
    config_dir = tmp_path / "mcp-project-dev"
    config_dir.mkdir(exist_ok=True)
    (config_dir / "compiler-manifest.v1.json").write_text(json.dumps(manifest), encoding="utf-8")

    async def exercise() -> None:
        async with Client(create_server(tmp_path), mode="auto") as client:
            assert client.server_info is not None
            assert client.server_info.name == SERVER_NAME
            assert client.server_info.version == "0.1.0"
            assert client.server_info.description == SERVER_DESCRIPTION
            assert client.instructions == SERVER_INSTRUCTIONS
            listed = await client.list_tools()
            assert [tool.name for tool in listed.tools] == [
                "dev_capabilities",
                "compile_runtime_instructions",
                "check_runtime_instructions_freshness",
            ]
            assert all(tool.input_schema["properties"] == {} for tool in listed.tools)
            compile_metadata, freshness_metadata = listed.tools[1:]
            assert compile_metadata.description and len(compile_metadata.description) > 200
            assert compile_metadata.annotations is not None
            assert compile_metadata.annotations.read_only_hint is False
            assert compile_metadata.annotations.destructive_hint is True
            assert compile_metadata.annotations.idempotent_hint is True
            assert compile_metadata.annotations.open_world_hint is False
            assert freshness_metadata.description and len(freshness_metadata.description) > 200
            assert freshness_metadata.annotations is not None
            assert freshness_metadata.annotations.read_only_hint is True
            cap = _result_payload(await client.call_tool("dev_capabilities", {}))
            assert cap["configured_root"] is True
            assert cap["compiler_manifest_schema"]["properties"]["source_units"]
            assert cap["compiler_manifest_schema"]["properties"]["runtime_entries"]
            schema = cap["compiler_manifest_schema"]
            assert "legacy_bindings" in schema["required"]
            assert "owner_views" in schema["required"]
            assert "owner_paths_sha256" in schema["properties"]["legacy_source_hashes"]["required"]
            assert (
                "legacy_branch"
                in schema["$defs"]["runtime_entry"]["properties"]["branches"]["items"]["required"]
            )
            assert cap["side_effects"]["filesystem_read"] is True
            assert cap["side_effects"]["filesystem_write"] is True
            compiled = _result_payload(await client.call_tool("compile_runtime_instructions", {}))
            assert compiled["status"] == "failed"
            assert compiled["partial_artifact"] is False
            fresh = _result_payload(
                await client.call_tool("check_runtime_instructions_freshness", {})
            )
            assert fresh["status"] == "failed"
            assert not (config_dir / "generated/runtime-instructions.v1.json").exists()

    asyncio.run(exercise())

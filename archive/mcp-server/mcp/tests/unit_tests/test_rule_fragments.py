from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import TypeAdapter, ValidationError
from token_io_decoupling_core.context_index_contract import validate_context_index
from token_io_decoupling_core.heading_parser import (
    DuplicateHeadingError,
    HeadingNotFoundError,
    extract_heading,
)
from token_io_decoupling_core.rules import (
    IncompatibleRuleContractError,
    RuleLoader,
    RuleLoadError,
    UnsafeRulePathError,
)
from token_io_decoupling_core.workflow_models import CheckpointNode
from token_io_decoupling_transport.payloads import RuleContextPayload


def _repository(tmp_path: Path) -> Path:
    root = tmp_path / "repository"
    (root / "mcp").mkdir(parents=True)
    (root / "owners").mkdir()
    mcp_root = Path(__file__).parents[2]
    registry = json.loads((mcp_root / "rule-registry.json").read_text(encoding="utf-8"))
    contract = next(node for node in registry["nodes"] if node["node_id"] == "contract")
    contract["owner_path"] = "owners/en.md"
    contract["owner_section"] = "Actions"
    contract["owner_mirrors"] = {"zh_cn": {"path": "owners/zh.md", "section": "动作"}}
    (root / "mcp/rule-registry.json").write_text(
        json.dumps(registry, ensure_ascii=False), encoding="utf-8"
    )
    index = json.loads((mcp_root / "rule-context-index.json").read_text(encoding="utf-8"))
    sections = {
        "contract.actions": "Actions",
        "contract.pass": "Pass condition",
        "contract.boundary": "Boundary",
    }
    for fragment in index["fragments"]:
        if fragment["fragment_id"] in sections:
            fragment["section_en"] = sections[fragment["fragment_id"]]
    (root / "mcp/rule-context-index.json").write_text(
        json.dumps(index, ensure_ascii=False), encoding="utf-8"
    )
    return root


def _owner(
    actions: str = "Do the action.",
    passed: str = "Pass when done.",
    boundary: str = "Stop on failure.",
) -> str:
    return f"## Actions\n{actions}\n\n## Pass condition\n{passed}\n\n## Boundary\n{boundary}\n"


def _write_contract_owners(root: Path, *, english: str | None = None) -> None:
    (root / "owners/en.md").write_text(english or _owner(), encoding="utf-8")
    chinese = "## 动作\n执行动作。\n\n## 通过条件\n完成时通过。\n\n## 边界\n失败时停止。\n"
    (root / "owners/zh.md").write_text(chinese, encoding="utf-8")


def test_versioned_bundle_has_explicit_closure_and_bilingual_hashes(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    _write_contract_owners(root, english=_owner("Do the action. [Related](related.md#rules)."))
    loader = RuleLoader(repository_root=root)
    english = loader.load_context_bundle("contract", language="en")
    chinese = loader.load_context_bundle("contract", language="zh_cn")

    assert english.complete and english.status == "complete"
    assert english.required_fragment_ids == [
        "contract.actions",
        "contract.pass",
        "contract.boundary",
    ]
    assert [item.owner_section for item in english.fragments] == [
        "Actions",
        "Pass condition",
        "Boundary",
    ]
    assert english.fragments[0].text.startswith("Do the action.")
    assert chinese.fragments[0].text == "执行动作。"
    assert english.context_hash != chinese.context_hash
    assert all(len(item.text_sha256) == 64 for item in english.fragments)
    assert "owner_text" not in english.node_metadata.model_dump()
    assert [(item.path, item.section) for item in english.remaining_owner_refs] == [
        ("owners/related.md", "rules")
    ]
    assert english.remaining_owner_refs_truncated is False


def test_controlled_optional_owner_fragments_preserve_default_and_load_bilingual() -> None:
    workspace = Path(__file__).parents[2]
    loader = RuleLoader(repository_root=workspace.parent)
    optional_ids = {
        "decision.workflow_routing_advice",
        "implementation.candidate_compliance",
        "implementation.output_materialization",
    }

    defaults = {
        node_id: loader.load_context_bundle(node_id).required_fragment_ids
        for node_id in ("decision", "implementation")
    }
    assert optional_ids.isdisjoint(defaults["decision"])
    assert optional_ids.isdisjoint(defaults["implementation"])

    cases = (
        ("decision", "decision.workflow_routing_advice", "workflow-routing-advice.md"),
        ("implementation", "implementation.candidate_compliance", "candidate-compliance.md"),
        ("implementation", "implementation.output_materialization", "output-materialization.md"),
    )
    bundles = {
        (node_id, fragment_id, language): loader.load_context_bundle(
            node_id, language=language, fragment_ids=[fragment_id]
        )
        for node_id, fragment_id, _owner in cases
        for language in ("en", "zh_cn")
    }
    for node_id, fragment_id, owner_filename in cases:
        english = bundles[(node_id, fragment_id, "en")]
        chinese = bundles[(node_id, fragment_id, "zh_cn")]
        assert english.complete and chinese.complete
        english_fragment = next(
            item for item in english.fragments if item.fragment_id == fragment_id
        )
        chinese_fragment = next(
            item for item in chinese.fragments if item.fragment_id == fragment_id
        )
        owner_base = (
            "skill/references/coding/layer-01-fundamental-concepts/execution-planning/"
        )
        assert english_fragment.owner_path == owner_base + owner_filename
        assert chinese_fragment.owner_path == owner_base + owner_filename
        assert english_fragment.owner_section == "通用规范"
        assert chinese_fragment.owner_section == "通用规范"
        assert len(english_fragment.text_sha256) == 64
        assert len(chinese_fragment.text_sha256) == 64
        assert english.context_hash != chinese.context_hash

    output_ids = bundles[
        ("implementation", "implementation.output_materialization", "en")
    ].required_fragment_ids
    assert "implementation.candidate_compliance" in output_ids
    assert "implementation.output_materialization" in output_ids


def test_context_hash_binds_the_canonical_context_index(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    _write_contract_owners(root)
    index_path = root / "mcp/rule-context-index.json"
    loader = RuleLoader(repository_root=root)
    before = loader.load_context_bundle("contract")
    index = json.loads(index_path.read_text(encoding="utf-8"))
    git_actions = next(item for item in index["fragments"] if item["fragment_id"] == "git.actions")
    git_actions["dependencies"] = ["git.pass"]
    index_path.write_text(json.dumps(index), encoding="utf-8")
    after = loader.load_context_bundle("contract")
    assert before.required_fragment_ids == after.required_fragment_ids
    assert before.index_sha256 != after.index_sha256
    assert before.context_hash != after.context_hash


def test_versioned_budget_omits_whole_fragments_and_reports_missing(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    _write_contract_owners(root, english=_owner("a" * 120, "b" * 120, "c" * 120))
    result = RuleLoader(repository_root=root).load_context_bundle("contract", max_chars=256)

    assert not result.complete
    assert result.status == "incomplete_budget"
    assert result.text_characters <= result.text_budget == 256
    assert result.required_text_characters == 360
    assert [item.fragment_id for item in result.fragments] == ["contract.actions", "contract.pass"]
    assert [item.fragment_id for item in result.missing_fragments] == ["contract.boundary"]
    assert result.missing_fragments[0].reason == "text_budget_exceeded"
    assert result.fragments[1].text == "b" * 120


def test_remaining_owner_refs_are_bounded_and_ignore_fenced_examples(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    links = " ".join(f"[owner {number}](owner-{number}.md#actions)" for number in range(18))
    body = (
        f"{links}\n\n```markdown\n[fenced](ignore.md)\n```"
        "\n\n~~~markdown\n~~~ ~\n[fenced tilde](ignore-tilde.md#actions)\n~~~"
    )
    _write_contract_owners(root, english=_owner(body))
    result = RuleLoader(repository_root=root).load_context_bundle("contract")
    assert len(result.remaining_owner_refs) == 16
    assert result.remaining_owner_refs_truncated is True
    assert all("ignore.md" not in item.path for item in result.remaining_owner_refs)
    assert all("ignore-tilde.md" not in item.path for item in result.remaining_owner_refs)


def test_unanchored_owner_link_remains_when_a_section_of_same_file_is_returned(
    tmp_path: Path,
) -> None:
    root = _repository(tmp_path)
    _write_contract_owners(root, english=_owner("Actions.", "[Entire owner](en.md)", "Boundary."))
    result = RuleLoader(repository_root=root).load_context_bundle("contract")
    assert ("owners/en.md", None) in {
        (item.path, item.section) for item in result.remaining_owner_refs
    }


def test_anchored_owner_links_use_exact_returned_section_coverage(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    _write_contract_owners(
        root,
        english=_owner("[Returned section](en.md#actions) [Unreturned section](en.md#unloaded)"),
    )
    result = RuleLoader(repository_root=root).load_context_bundle("contract")
    remaining = {(item.path, item.section) for item in result.remaining_owner_refs}

    assert ("owners/en.md", "actions") not in remaining
    assert ("owners/en.md", "unloaded") in remaining


def test_missing_owner_heading_is_an_explicit_incomplete_result(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    _write_contract_owners(root, english="## Actions\nDo it.\n\n## Pass condition\nReady.\n")
    result = RuleLoader(repository_root=root).load_context_bundle("contract")
    assert not result.complete
    assert result.status == "incomplete_content"
    assert result.missing_fragments[0].fragment_id == "contract.boundary"
    assert result.missing_fragments[0].reason == "owner_heading_missing_or_empty"


def test_duplicate_real_owner_heading_fails_closed(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    _write_contract_owners(
        root,
        english=_owner() + "\n## Boundary\nA second real boundary.\n",
    )
    with pytest.raises(RuleLoadError, match="duplicate indexed owner heading"):
        RuleLoader(repository_root=root).load_context_bundle("contract")


def test_fragment_selection_requires_version_and_known_unique_ids(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="require context_version=1"):
        RuleContextPayload.model_validate(
            {"node_id": CheckpointNode.CONTRACT, "fragment_ids": ["contract.actions"]}
        )
    with pytest.raises(ValidationError, match="duplicates"):
        RuleContextPayload.model_validate(
            {
                "node_id": CheckpointNode.CONTRACT,
                "context_version": 1,
                "fragment_ids": ["contract.actions", "contract.actions"],
            }
        )
    adapter = TypeAdapter(RuleContextPayload)
    for version in ("true", "1.0", "2", '"1"'):
        with pytest.raises(ValidationError, match="context_version"):
            adapter.validate_json('{"node_id":"contract","context_version":' + version + "}")
    assert adapter.validate_json('{"node_id":"contract","context_version":1}').context_version == 1
    with pytest.raises(ValidationError, match="at most 128"):
        RuleContextPayload.model_validate(
            {
                "node_id": CheckpointNode.CONTRACT,
                "context_version": 1,
                "fragment_ids": [f"fragment-{index}" for index in range(129)],
            }
        )
    with pytest.raises(ValidationError, match="at most 128"):
        RuleContextPayload.model_validate(
            {
                "node_id": CheckpointNode.CONTRACT,
                "context_version": 1,
                "fragment_ids": ["x" * 129],
            }
        )
    root = _repository(tmp_path)
    _write_contract_owners(root)
    with pytest.raises(RuleLoadError, match="unknown context fragment"):
        RuleLoader(repository_root=root).load_context_bundle("contract", fragment_ids=["made.up"])


def test_index_cycles_and_duplicate_fragment_ids_fail_closed(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    _write_contract_owners(root)
    index_path = root / "mcp/rule-context-index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    first = next(item for item in index["fragments"] if item["fragment_id"] == "contract.actions")
    first["dependencies"] = ["contract.pass"]
    second = next(item for item in index["fragments"] if item["fragment_id"] == "contract.pass")
    second["dependencies"] = ["contract.actions"]
    index_path.write_text(json.dumps(index), encoding="utf-8")
    with pytest.raises(IncompatibleRuleContractError, match="cycle"):
        RuleLoader(repository_root=root).load_context_bundle("contract")

    index["fragments"].append(dict(first))
    index_path.write_text(json.dumps(index), encoding="utf-8")
    with pytest.raises(IncompatibleRuleContractError, match="duplicate context fragment_id"):
        RuleLoader(repository_root=root).load_context_bundle("contract")


def test_build_and_runtime_use_the_same_index_contract_validator(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    _write_contract_owners(root)
    registry = json.loads((root / "mcp/rule-registry.json").read_text(encoding="utf-8"))
    index_path = root / "mcp/rule-context-index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    validate_context_index(index, registry)

    changed = json.loads(json.dumps(index))
    changed["fragments"][0]["dependencies"] = ["missing.fragment"]
    with pytest.raises(ValueError, match="unknown dependency"):
        validate_context_index(changed, registry)
    index_path.write_text(json.dumps(changed), encoding="utf-8")
    with pytest.raises(IncompatibleRuleContractError, match="unknown dependency"):
        RuleLoader(repository_root=root).load_context_bundle("contract")

    cross_node_default = json.loads(json.dumps(index))
    contract = next(item for item in cross_node_default["nodes"] if item["node_id"] == "contract")
    contract["default_fragment_ids"] = ["mode.actions"]
    with pytest.raises(ValueError, match="does not belong to node contract"):
        validate_context_index(cross_node_default, registry)
    index_path.write_text(json.dumps(cross_node_default), encoding="utf-8")
    with pytest.raises(IncompatibleRuleContractError, match="does not belong to node contract"):
        RuleLoader(repository_root=root).load_context_bundle("contract")

    wrong_section_default = json.loads(json.dumps(index))
    wrong_section_default["fragments"].append(
        {
            "fragment_id": "contract.wrong-section",
            "node_id": "contract",
            "section_en": "Not the owner section",
            "section_zh_cn": "不是所有者章节",
        }
    )
    contract = next(
        item for item in wrong_section_default["nodes"] if item["node_id"] == "contract"
    )
    contract["default_fragment_ids"] = ["contract.wrong-section"]
    with pytest.raises(ValueError, match="do not include registry owner sections"):
        validate_context_index(wrong_section_default, registry)
    index_path.write_text(json.dumps(wrong_section_default), encoding="utf-8")
    with pytest.raises(
        IncompatibleRuleContractError, match="do not include registry owner sections"
    ):
        RuleLoader(repository_root=root).load_context_bundle("contract")


def test_controlled_owner_fragments_reject_wrong_node_and_section(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    _write_contract_owners(root)
    registry = json.loads((root / "mcp/rule-registry.json").read_text(encoding="utf-8"))
    index_path = root / "mcp/rule-context-index.json"
    original = json.loads(index_path.read_text(encoding="utf-8"))

    wrong_node = json.loads(json.dumps(original))
    candidate = next(
        item
        for item in wrong_node["fragments"]
        if item["fragment_id"] == "implementation.candidate_compliance"
    )
    candidate["node_id"] = "decision"
    with pytest.raises(ValueError, match="must belong to node implementation"):
        validate_context_index(wrong_node, registry)
    index_path.write_text(json.dumps(wrong_node), encoding="utf-8")
    with pytest.raises(IncompatibleRuleContractError, match="must belong to node implementation"):
        RuleLoader(repository_root=root).load_context_bundle("implementation")

    wrong_section = json.loads(json.dumps(original))
    candidate = next(
        item
        for item in wrong_section["fragments"]
        if item["fragment_id"] == "implementation.candidate_compliance"
    )
    candidate["section_en"] = "Actions"
    with pytest.raises(ValueError, match="must select General rules sections"):
        validate_context_index(wrong_section, registry)
    index_path.write_text(json.dumps(wrong_section), encoding="utf-8")
    with pytest.raises(IncompatibleRuleContractError, match="must select General rules sections"):
        RuleLoader(repository_root=root).load_context_bundle("implementation")


def test_indexed_owner_paths_reject_traversal_and_symlink_escape(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    _write_contract_owners(root)
    registry_path = root / "mcp/rule-registry.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    contract = next(node for node in registry["nodes"] if node["node_id"] == "contract")
    contract["owner_path"] = "..\\outside.md"
    registry_path.write_text(json.dumps(registry), encoding="utf-8")
    with pytest.raises(UnsafeRulePathError):
        RuleLoader(repository_root=root).load_context_bundle("contract")

    contract["owner_path"] = "owners/link.md"
    registry_path.write_text(json.dumps(registry), encoding="utf-8")
    outside = tmp_path / "outside.md"
    outside.write_text("## Actions\nsecret\n", encoding="utf-8")
    (root / "owners/link.md").symlink_to(outside)
    with pytest.raises(UnsafeRulePathError):
        RuleLoader(repository_root=root).load_context_bundle("contract")


def test_parser_ignores_fenced_headings_and_rejects_real_duplicates() -> None:
    source = (
        "## Actions\n"
        "```markdown\n## Pass condition\nignored\n```\n"
        "Actions body.\n"
        "## Pass condition\nreal body\n"
        "~~~text\n~~~ ~\n## Fake tilde heading\n"
        "[fenced link](ignore-tilde.md#actions)\n## Boundary\nignored\n~~~\n"
        "## Boundary\nactual boundary\n"
    )
    assert "## Pass condition\nignored" in extract_heading(source, "Actions")
    assert extract_heading(source, "Pass condition") == (
        "real body\n~~~text\n~~~ ~\n## Fake tilde heading\n"
        "[fenced link](ignore-tilde.md#actions)\n## Boundary\nignored\n~~~"
    )
    assert extract_heading(source, "Boundary") == "actual boundary"
    with pytest.raises(HeadingNotFoundError):
        extract_heading(source, "Fake tilde heading")
    with pytest.raises(HeadingNotFoundError):
        extract_heading("## Actions#\nmisindexed body\n", "Actions")
    assert extract_heading("## Actions#\nmisindexed body\n", "Actions#") == "misindexed body"
    with pytest.raises(DuplicateHeadingError):
        extract_heading(source + "\n## Actions\nsecond\n", "Actions")
    with pytest.raises(HeadingNotFoundError):
        extract_heading(source, "Missing")

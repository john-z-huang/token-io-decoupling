from __future__ import annotations

import json
from pathlib import Path

import pytest
from token_io_decoupling_core.owner_paths import OWNER_PATHS
from token_io_decoupling_core.rules import (
    IncompatibleRuleContractError,
    RuleLoader,
    UnknownRuleNodeError,
    UnsafeRulePathError,
)


def _repo(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "repository"
    (root / "mcp").mkdir(parents=True)
    (root / "owners").mkdir()
    (root / "owners" / "en.md").write_text(
        "# Owner\n\n## Scope\nEnglish rules.\n", encoding="utf-8"
    )
    (root / "owners" / "zh.md").write_text("# Owner\n\n## 范围\n中文规则。\n", encoding="utf-8")
    canonical_registry = Path(__file__).parents[2] / "rule-registry.json"
    registry = json.loads(canonical_registry.read_text(encoding="utf-8"))
    contract = next(node for node in registry["nodes"] if node["node_id"] == "contract")
    contract["owner_path"] = "owners/en.md"
    contract["owner_section"] = "Scope"
    contract["owner_mirrors"] = {"zh_cn": {"path": "owners/zh.md", "section": "范围"}}
    registry_path = root / "mcp" / "rule-registry.json"
    registry_path.write_text(json.dumps(registry, ensure_ascii=False), encoding="utf-8")
    return root, registry_path


def test_loader_reads_bilingual_owner_sections_and_recomputes_hash(tmp_path: Path) -> None:
    root, _ = _repo(tmp_path)
    loader = RuleLoader(repository_root=root)
    english = loader.load_context("contract")
    chinese = loader.load_context("contract", language="zh_cn")
    assert "English rules." in english.owner_text
    assert "中文规则。" in chinese.owner_text
    assert english.owner_path == "owners/en.md"
    assert chinese.owner_path == "owners/zh.md"
    before = english.context_hash
    with (root / "owners" / "en.md").open("a", encoding="utf-8") as source:
        source.write("Updated rule.\n")
    after = loader.load_context("contract").context_hash
    assert after != before


def test_environment_checkpoint_is_not_registered_and_contract_leads_to_mode() -> None:
    loader = RuleLoader(repository_root=Path(__file__).parents[3])
    contract = loader.load_context("contract")
    assert contract.next_checkpoint_ids == ["mode"]
    with pytest.raises(UnknownRuleNodeError, match="environment"):
        loader.load_context("environment")


@pytest.mark.parametrize("contract_version", [1, 3])
def test_loader_rejects_unknown_nodes_and_incompatible_contract(
    tmp_path: Path, contract_version: int
) -> None:
    root, registry_path = _repo(tmp_path)
    loader = RuleLoader(repository_root=root)
    with pytest.raises(UnknownRuleNodeError):
        loader.load_context("missing")
    registry = json.loads(registry_path.read_text())
    registry["contract_version"] = contract_version
    registry_path.write_text(json.dumps(registry), encoding="utf-8")
    with pytest.raises(IncompatibleRuleContractError):
        loader.load_context("contract")


def test_same_version_program_contract_change_is_rejected_but_text_is_dynamic(
    tmp_path: Path,
) -> None:
    root, registry_path = _repo(tmp_path)
    loader = RuleLoader(repository_root=root)
    before = loader.load_context("contract").context_hash
    owner = root / "owners" / "en.md"
    owner.write_text("# Owner\n\n## Scope\nUpdated prose only.\n", encoding="utf-8")
    assert loader.load_context("contract").context_hash != before

    registry = json.loads(registry_path.read_text())
    contract = next(node for node in registry["nodes"] if node["node_id"] == "contract")
    contract["legal_branches"] = ["pass", "changed"]
    registry_path.write_text(json.dumps(registry), encoding="utf-8")
    with pytest.raises(IncompatibleRuleContractError, match="legal branches changed"):
        loader.load_context("contract")


@pytest.mark.parametrize(
    ("field", "replacement"),
    [("required_facts", []), ("required_evidence", ["different evidence"])],
)
def test_same_version_requirement_changes_are_rejected(
    tmp_path: Path, field: str, replacement: list[str]
) -> None:
    root, registry_path = _repo(tmp_path)
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    contract = next(node for node in registry["nodes"] if node["node_id"] == "contract")
    contract[field] = replacement
    registry_path.write_text(json.dumps(registry), encoding="utf-8")

    with pytest.raises(IncompatibleRuleContractError, match="required facts or evidence changed"):
        RuleLoader(repository_root=root).load_context("contract")


def test_loader_rejects_traversal_and_symlink_escape(tmp_path: Path) -> None:
    root, registry_path = _repo(tmp_path)
    registry = json.loads(registry_path.read_text())
    contract = next(node for node in registry["nodes"] if node["node_id"] == "contract")
    contract["owner_path"] = "../../outside.md"
    registry_path.write_text(json.dumps(registry), encoding="utf-8")
    with pytest.raises(UnsafeRulePathError):
        RuleLoader(repository_root=root).load_context("contract")

    contract["owner_path"] = "owners/link.md"
    registry_path.write_text(json.dumps(registry), encoding="utf-8")
    outside = tmp_path / "outside.md"
    outside.write_text("## Scope\nsecret", encoding="utf-8")
    (root / "owners" / "link.md").symlink_to(outside)
    with pytest.raises(UnsafeRulePathError):
        RuleLoader(repository_root=root).load_context("contract")


def test_delegation_policy_uses_shared_owner_path_map(tmp_path: Path) -> None:
    root, _ = _repo(tmp_path)
    owner_path = root / Path(OWNER_PATHS["child-role-selection"])
    owner_path.parent.mkdir(parents=True)
    owner_path.write_text("# Owner\n\n## General rules\nMapped policy.\n", encoding="utf-8")
    loaded, _ = RuleLoader(repository_root=root).load_delegation_policy("child-role-selection")
    assert "Mapped policy." in loaded

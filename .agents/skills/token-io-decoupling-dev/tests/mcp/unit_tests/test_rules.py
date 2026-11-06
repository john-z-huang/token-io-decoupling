from __future__ import annotations

from pathlib import Path

import pytest
from support.compiled_resources import CompiledResources

from token_io_decoupling_workflow.rules import (
    IncompatibleRuleContractError,
    RuleLoader,
    RuleLoadError,
    UnknownRuleNodeError,
)


def test_bilingual_compiled_contexts_have_build_identity_and_inline_instructions() -> None:
    loader = RuleLoader()
    english = loader.load_context("contract")
    chinese = loader.load_context("contract", language="zh_cn")
    assert english.schema_version == 2
    assert english.build_id == chinese.build_id
    assert english.owner_path == "compiled:contract:en"
    assert chinese.owner_path == "compiled:contract:zh_cn"
    assert english.owner_text and chinese.owner_text
    assert english.context_hash != chinese.context_hash
    assert english.required_facts
    assert english.next_checkpoint_ids == ["mode"]
    with pytest.raises(UnknownRuleNodeError):
        loader.load_context("environment")


def test_repository_argument_cannot_select_author_documents(tmp_path: Path) -> None:
    before = RuleLoader().load_context("contract")
    nonexistent = tmp_path / "no-author-tree"
    assert RuleLoader(repository_root=nonexistent).load_context("contract") == before


def test_missing_compiled_resource_does_not_fall_back_to_sources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    staged = CompiledResources(tmp_path, monkeypatch)
    (staged.resources / "instructions.json").unlink()
    with pytest.raises(RuleLoadError, match="compiled instruction"):
        RuleLoader(repository_root=tmp_path).load_context("contract")


@pytest.mark.parametrize("field", ["schema", "build", "manifest_hash", "text_hash"])
def test_corrupt_or_incompatible_resources_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    staged = CompiledResources(tmp_path, monkeypatch)
    if field == "schema":
        staged.document["schema_version"] = 1
    elif field == "build":
        staged.document["build_id"] = "0" * 64
    elif field == "text_hash":
        staged.document["nodes"]["contract"]["en"]["text"] += " changed"
    staged.save()
    if field == "manifest_hash":
        (staged.resources / "instructions.json").write_text("{}", encoding="utf-8")
    with pytest.raises(RuleLoadError):
        RuleLoader().load_context("contract")


def test_registry_semantics_cannot_change_without_consumer_contract_update(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    staged = CompiledResources(tmp_path, monkeypatch)
    staged.document["registry"]["nodes"][0]["required_facts"] = ["invented_requirement"]
    staged.save()
    with pytest.raises(IncompatibleRuleContractError):
        RuleLoader().load_context("contract")


def test_policy_sections_and_choices_are_compiled_data_and_hash_bound(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    staged = CompiledResources(tmp_path, monkeypatch)
    before = RuleLoader().load_delegation_policy("task-assignment")
    heading = "Executor Decisions instructions"
    staged.document["policies"]["task-assignment"]["en"]["sections"][heading] = (
        "Use this compiled instruction directly."
    )
    staged.save()
    after = RuleLoader().load_delegation_policy("task-assignment")
    assert after.text == before.text
    assert after.content_sha256 != before.content_sha256
    assert after.sections[heading] == "Use this compiled instruction directly."
    assert after.choices["Executor choice descriptions"]

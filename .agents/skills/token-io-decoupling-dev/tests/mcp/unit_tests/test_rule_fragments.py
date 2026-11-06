from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError
from support.compiled_resources import CompiledResources

from token_io_decoupling_core.rules import RuleLoader, RuleLoadError
from token_io_decoupling_transport.payloads import RuleContextPayload


def test_default_bundle_and_internal_checkpoint_use_one_instruction_hash() -> None:
    loader = RuleLoader()
    for language in ("en", "zh_cn"):
        bundle = loader.load_context_bundle("contract", language=language, max_chars=60_000)
        context = loader.load_context("contract", language=language)
        assert bundle.schema_version == 2
        assert bundle.complete
        assert bundle.context_hash == context.context_hash
        assert bundle.fragments[0].text == context.owner_text
        assert bundle.build_id == context.build_id
        assert bundle.remaining_owner_refs == []
        assert bundle.remaining_owner_refs_truncated is False
        assert bundle.fragments[0].owner_path.startswith("compiled:")


def test_budget_failure_returns_no_executable_partial_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    staged = CompiledResources(tmp_path, monkeypatch)
    staged.set_text("nodes", "contract", "en", ("Complete action and gates. " * 40).strip())
    loader = RuleLoader()
    small = loader.load_context_bundle("contract", max_chars=256)
    sufficient = loader.load_context_bundle("contract", max_chars=60_000)
    assert small.status == "incomplete_budget"
    assert not small.complete
    assert small.fragments == []
    assert small.text_characters == 0
    assert small.missing_fragments
    assert small.required_text_characters > small.text_budget
    assert small.context_hash == sufficient.context_hash
    assert sufficient.complete


def test_optional_selection_returns_complete_units_with_distinct_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    staged = CompiledResources(tmp_path, monkeypatch)
    fragment_id = next(iter(staged.document["fragments"]))
    loader = RuleLoader()
    default = loader.load_context_bundle("contract", max_chars=60_000)
    selected = loader.load_context_bundle("contract", fragment_ids=[fragment_id], max_chars=60_000)
    assert selected.complete
    assert default.required_fragment_ids == ["contract.compiled"]
    assert selected.required_fragment_ids == [fragment_id]
    assert len(selected.fragments) == 1
    assert selected.fragments[0].text == staged.document["fragments"][fragment_id]["en"]["text"]
    assert default.context_hash != selected.context_hash
    with pytest.raises(RuleLoadError, match="duplicates"):
        loader.load_context_bundle("contract", fragment_ids=[fragment_id, fragment_id])
    with pytest.raises(RuleLoadError, match="missing compiled"):
        loader.load_context_bundle("contract", fragment_ids=["does.not.exist"])


def test_payload_defaults_to_compiled_schema_and_rejects_retired_version() -> None:
    payload = RuleContextPayload.model_validate_json('{"node_id":"contract"}')
    assert payload.context_version == 2
    assert (
        RuleContextPayload.model_validate_json('{"node_id":"contract","max_chars":256}').max_chars
        == 256
    )
    for version in ("1", "true", "null", '"2"', "3"):
        with pytest.raises(ValidationError, match="context_version"):
            RuleContextPayload.model_validate_json(
                '{"node_id":"contract","context_version":' + version + "}"
            )
    with pytest.raises(ValidationError, match="duplicates"):
        RuleContextPayload.model_validate_json(
            '{"node_id":"contract","fragment_ids":["same","same"]}'
        )

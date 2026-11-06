"""Shared instruction delivery must remain executable and fail closed."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from support.compiled_resources import CompiledResources

from token_io_decoupling_workflow.rules import RuleLoader, RuleLoadError


@pytest.mark.parametrize("language", ["en", "zh_cn"])
def test_explicit_shared_fragment_does_not_repeat_default_node(language: str) -> None:
    rules = RuleLoader()
    default = rules.load_context_bundle("contract", language=language)
    empty = rules.load_context_bundle("contract", language=language, fragment_ids=[])
    shared = rules.load_context_bundle(
        "contract", language=language, fragment_ids=["common.hard_constraints"]
    )
    assert default == empty
    assert default.required_fragment_ids == ["contract.compiled"]
    assert shared.complete
    assert shared.required_fragment_ids == ["common.hard_constraints"]
    assert len(shared.fragments) == 1
    assert "Computer Use" in shared.fragments[0].text
    assert shared.text_characters < default.text_characters


@pytest.mark.parametrize("language", ["en", "zh_cn"])
def test_standalone_late_stage_can_fetch_required_shared_content(language: str) -> None:
    rules = RuleLoader()
    stage = rules.load_stage("coding-single-agent", "documentation", language=language)
    requirements = {item["instruction_id"]: item for item in stage["shared_requirements"]}
    assert requirements["common.hard_constraints"]["when"] == "before_any_action"
    assert requirements["route.single_agent.return_map"]["when"] == "needs_prerequisite"
    for requirement in requirements.values():
        payload = requirement["lookup"]["arguments"]["payload"]
        bundle = rules.load_context_bundle(
            payload["node_id"],
            language=payload["language"],
            fragment_ids=payload["fragment_ids"],
            max_chars=payload["max_chars"],
        )
        assert bundle.complete
        assert bundle.build_id == stage["build_id"]
        assert bundle.required_fragment_ids == [requirement["instruction_id"]]
        assert (
            hashlib.sha256(bundle.fragments[0].text.encode()).hexdigest()
            == requirement["text_sha256"]
        )


@pytest.mark.parametrize(
    "corruption",
    ["missing", "hash", "language", "trigger", "scope", "budget", "reuse", "missing_unit"],
)
def test_invalid_shared_requirement_blocks_stage_delivery(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, corruption: str
) -> None:
    staged = CompiledResources(tmp_path, monkeypatch)
    entry = staged.document["routes"]["single_agent"]["en"]["stages"]["documentation"]
    shared = entry["shared_requirements"][0]
    if corruption == "missing":
        entry.pop("shared_requirements")
    elif corruption == "hash":
        shared["text_sha256"] = "0" * 64
    elif corruption == "language":
        shared["language"] = "zh_cn"
    elif corruption == "trigger":
        shared["when"] = "optional"
    elif corruption == "scope":
        shared["lookup"]["arguments"]["payload"]["node_id"] = "acceptance"
    elif corruption == "budget":
        shared["lookup"]["arguments"]["payload"]["max_chars"] = 256
    elif corruption == "reuse":
        shared["reuse"] = "trust_caller_has_read_something"
    else:
        del staged.document["fragments"]["common.hard_constraints"]
    staged.save()
    with pytest.raises(RuleLoadError):
        RuleLoader().load_stage("coding-single-agent", "documentation")

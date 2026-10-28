from __future__ import annotations

import hashlib
import json

import pytest
from pydantic import ValidationError
from token_io_decoupling_workflow.decision_context import (
    DecisionContextInput,
    _input_hash,
)


def _payload(**overrides: object) -> DecisionContextInput:
    request: dict[str, object] = {
        "raw_content": (
            "User requirement: preserve existing behavior.\n"
            "Current diff: adds strict decision question.\n"
            "LSP observation: caller-composed symbol fact."
        ),
        "decision_goal": "Ask which lowest sufficient effort fits the released task.",
        "output_kind": "decision_question",
        "outbound_data_permitted": True,
    }
    request.update(overrides)
    return DecisionContextInput.model_validate(request)


@pytest.mark.parametrize(
    "field,value",
    [
        ("raw_content", None),
        ("raw_content", ""),
        ("raw_content", "  \n"),
        ("raw_content", 1),
        ("raw_content", "x" * 60_001),
        ("decision_goal", None),
        ("decision_goal", "\t "),
        ("decision_goal", 3),
        ("decision_goal", "g" * 1201),
        ("output_kind", "other"),
        ("outbound_data_permitted", 1),
    ],
)
def test_input_rejects_missing_type_blank_and_oversized_values(field: str, value: object) -> None:
    data = _payload().model_dump()
    data[field] = value
    with pytest.raises(ValidationError):
        DecisionContextInput.model_validate(data)


def test_input_forbids_extra_fields_and_required_fields() -> None:
    data = _payload().model_dump()
    del data["raw_content"]
    with pytest.raises(ValidationError):
        DecisionContextInput.model_validate(data)
    with pytest.raises(ValidationError):
        DecisionContextInput.model_validate({**_payload().model_dump(), "unexpected": True})


def test_hash_covers_all_decision_inputs_but_excludes_permission() -> None:
    baseline = _payload()
    assert _input_hash(baseline) == _input_hash(_payload(outbound_data_permitted=False))
    assert _input_hash(baseline) != _input_hash(_payload(raw_content="changed source"))
    assert _input_hash(baseline) != _input_hash(_payload(decision_goal="changed goal"))
    assert _input_hash(baseline) != _input_hash(_payload(output_kind="decision_context"))
    canonical = {
        "raw_content": (
            "User requirement: preserve existing behavior.\n"
            "Current diff: adds strict decision question.\n"
            "LSP observation: caller-composed symbol fact."
        ),
        "decision_goal": "Ask which lowest sufficient effort fits the released task.",
        "output_kind": "decision_question",
    }
    expected = hashlib.sha256(
        json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()
    assert _input_hash(baseline) == expected

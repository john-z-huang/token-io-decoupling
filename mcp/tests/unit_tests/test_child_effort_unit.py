from __future__ import annotations

import hashlib
import json

import pytest
from pydantic import ValidationError
from token_io_decoupling_workflow.child_effort import (
    ChildEffortInput,
    _input_hash,
)


def _payload(**overrides: object) -> ChildEffortInput:
    facts: dict[str, object] = {
        "slice_id": "slice-17",
        "role": "Primary Output",
        "objective": "Implement a bounded API integration with unit coverage.",
        "decision_question": (
            "What is the lowest sufficient supported effort for this released slice?"
        ),
        "task_complexity": "complex",
        "uncertainty": "One provider response detail remains uncertain.",
        "scope": "One package and its focused tests.",
        "dependencies": "Existing Decisions SDK wrapper.",
        "risk": "Malformed responses must fail closed.",
        "verification_demands": "Mocked API success and failure cases.",
        "previous_failure_evidence": "none",
        "slice_fingerprint": "a" * 64,
        "runtime": "codex",
        "child_model": "gpt-6-luna",
        "supported_efforts": ["low", "medium", "high", "xhigh", "max"],
        "outbound_data_permitted": True,
    }
    facts.update(overrides)
    return ChildEffortInput.model_validate(facts)


@pytest.mark.parametrize(
    "value",
    [None, "", "  \n", 12, "x" * 1201],
)
def test_decision_question_is_required_nonblank_str_and_bounded(value: object) -> None:
    data = _payload().model_dump()
    data["decision_question"] = value
    with pytest.raises(ValidationError):
        ChildEffortInput.model_validate(data)


def test_decision_question_is_required() -> None:
    data = _payload().model_dump()
    del data["decision_question"]
    with pytest.raises(ValidationError):
        ChildEffortInput.model_validate(data)


def test_decision_question_accepts_1200_characters() -> None:
    assert len(_payload(decision_question="x" * 1200).decision_question) == 1200


def test_payload_rejects_unrecognized_runtime_and_model() -> None:
    with pytest.raises(ValidationError):
        _payload(runtime="unsupported_agent")
    with pytest.raises(ValidationError):
        _payload(child_model="unsupported_model")


def test_hash_includes_only_decision_fact_changes_not_permission_or_fingerprint() -> None:
    baseline = _payload()
    changed_question = _payload(decision_question="为当前切片选择最低充分档位。")
    assert _input_hash(baseline) != _input_hash(changed_question)
    assert _input_hash(baseline) == _input_hash(
        _payload(outbound_data_permitted=False, slice_fingerprint="b" * 64)
    )
    canonical = {
        "slice_id": "slice-17",
        "role": "Primary Output",
        "objective": "Implement a bounded API integration with unit coverage.",
        "decision_question": (
            "What is the lowest sufficient supported effort for this released slice?"
        ),
        "task_complexity": "complex",
        "uncertainty": "One provider response detail remains uncertain.",
        "scope": "One package and its focused tests.",
        "dependencies": "Existing Decisions SDK wrapper.",
        "risk": "Malformed responses must fail closed.",
        "verification_demands": "Mocked API success and failure cases.",
        "previous_failure_evidence": "none",
        "runtime": "codex",
        "child_model": "gpt-6-luna",
        "supported_efforts": ["low", "medium", "high", "xhigh", "max"],
    }
    expected = hashlib.sha256(
        json.dumps(canonical, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()
    assert _input_hash(baseline) == expected

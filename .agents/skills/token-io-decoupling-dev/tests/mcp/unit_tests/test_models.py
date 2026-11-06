from __future__ import annotations

import pytest
from pydantic import TypeAdapter, ValidationError

from token_io_decoupling_core.models import CodingMode, ModeCount
from token_io_decoupling_core.workflow_models import (
    ActiveCheckpointNode,
    CheckpointFact,
    CheckpointNode,
    CheckpointSemanticRef,
    EvidenceSubmission,
    FactKey,
    FactMissingEvidence,
    FactNotApplicable,
    FactUnknown,
)


def test_mode_count_contract_remains_strict() -> None:
    assert ModeCount(mode=CodingMode.SINGLE_AGENT, child_count=0).child_count == 0
    assert ModeCount(mode=CodingMode.MULTI_AGENT, child_count=1).child_count == 1
    with pytest.raises(ValidationError):
        ModeCount.model_validate({"mode": "Multi-Agent Coding", "child_count": True})
    with pytest.raises(ValidationError):
        ModeCount(mode=CodingMode.SINGLE_AGENT, child_count=1)


def test_active_rule_checkpoint_ids_remain_exact_and_environment_is_retired() -> None:
    adapter = TypeAdapter(ActiveCheckpointNode)
    assert adapter.validate_python("contract") is CheckpointNode.CONTRACT
    assert "environment" not in adapter.json_schema()["enum"]
    with pytest.raises(ValidationError):
        adapter.validate_python("environment")


def test_fact_judgments_keep_unknown_missing_evidence_and_not_applicable_shapes() -> None:
    assert FactUnknown(status="unknown").status == "unknown"
    assert FactMissingEvidence(
        status="missing_evidence", required_evidence=["reviewed diff"]
    ).required_evidence == ["reviewed diff"]
    reference = CheckpointSemanticRef(uri="memory://decision", content_hash="a" * 64)
    not_applicable = FactNotApplicable(status="not_applicable", reason=reference)
    fact = CheckpointFact(fact_key=FactKey.LOCKED_CHILD_COUNT, judgment=not_applicable)
    assert fact.judgment.status == "not_applicable"
    with pytest.raises(ValidationError):
        FactMissingEvidence(status="missing_evidence", required_evidence=[])
    with pytest.raises(ValidationError):
        FactNotApplicable.model_validate(
            {"status": "not_applicable", "reason": {"uri": "x", "content_hash": "bad"}}
        )


def test_evidence_submission_rejects_duplicate_fact_keys() -> None:
    unknown = CheckpointFact(
        fact_key=FactKey.TASK_OBJECTIVE, judgment=FactUnknown(status="unknown")
    )
    with pytest.raises(ValidationError):
        EvidenceSubmission(
            node_id=CheckpointNode.CONTRACT,
            facts=[unknown, unknown],
            input_hash="b" * 64,
        )

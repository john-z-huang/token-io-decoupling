from __future__ import annotations

import pytest
from pydantic import TypeAdapter, ValidationError
from token_io_decoupling_core.models import (
    CodingMode,
    DocumentationEpoch,
    EvidenceRef,
    GitMetadataEpoch,
    ImplementationContentEpoch,
    JudgmentMissingEvidence,
    JudgmentNotApplicable,
    JudgmentUnknown,
    ModeCount,
    Revision,
    SchemaVersion,
    SemanticRef,
)
from token_io_decoupling_core.state_models import (
    ActiveCheckpointNode,
    CheckpointEvaluation,
    CheckpointNode,
    DelegationUnreserveRequest,
    EpochSnapshot,
)
from token_io_decoupling_mcp.state_models import (
    DelegationUnreserveRequest as AdapterDelegationUnreserveRequest,
)


def test_mode_and_count_are_independent_strict_values() -> None:
    assert ModeCount(mode=CodingMode.SINGLE_AGENT, child_count=0).child_count == 0
    assert ModeCount(mode=CodingMode.MULTI_AGENT, child_count=1).child_count == 1
    with pytest.raises(ValidationError):
        ModeCount.model_validate({"mode": "Multi-Agent Coding", "child_count": True})
    with pytest.raises(ValidationError):
        ModeCount(mode=CodingMode.SINGLE_AGENT, child_count=1)
    with pytest.raises(ValidationError):
        ModeCount(mode=CodingMode.MULTI_AGENT, child_count=0)


def test_versions_revisions_epochs_and_references_have_distinct_contracts() -> None:
    digest = "a" * 64
    assert SchemaVersion(value=1).value == 1
    assert Revision(value=0).value == 0
    assert ImplementationContentEpoch(value=2).value == 2
    assert DocumentationEpoch(value=3).value == 3
    assert GitMetadataEpoch(value=4).value == 4
    assert SemanticRef(uri="memory://plan", content_hash=digest).uri == "memory://plan"
    assert EvidenceRef(uri="file://result", content_hash=digest).content_hash == digest
    with pytest.raises(ValidationError):
        Revision(value=True)
    with pytest.raises(ValidationError):
        SemanticRef(uri="memory://plan", content_hash="bad")


def test_legacy_environment_checkpoint_evaluation_remains_readable() -> None:
    legacy = CheckpointEvaluation(
        evaluation_id="legacy-environment",
        node_id=CheckpointNode.ENVIRONMENT,
        outcome="blocked",
        branch=None,
        rule_hash="a" * 64,
        input_hash="b" * 64,
        epochs=EpochSnapshot(implementation_content=0, documentation=0, git_metadata=0),
        basis_revision=0,
        result_revision=1,
        missing_facts=[],
        missing_evidence=[],
    )
    restored = CheckpointEvaluation.model_validate_json(legacy.model_dump_json())
    assert restored.node_id is CheckpointNode.ENVIRONMENT


def test_active_checkpoint_input_rejects_environment_and_keeps_legacy_enum_values() -> None:
    adapter = TypeAdapter(ActiveCheckpointNode)
    assert adapter.validate_python("contract") is CheckpointNode.CONTRACT
    assert "environment" not in adapter.json_schema()["enum"]
    with pytest.raises(ValidationError):
        adapter.validate_python("environment")


def test_judgment_statuses_require_evidence_or_not_applicable_reason() -> None:
    assert JudgmentUnknown(status="unknown").status == "unknown"
    missing = JudgmentMissingEvidence(status="missing_evidence", required_evidence=["diff"])
    assert missing.required_evidence == ["diff"]
    n_a = JudgmentNotApplicable(status="not_applicable", reason="no documentation changed")
    assert n_a.reason
    with pytest.raises(ValidationError):
        JudgmentMissingEvidence(status="missing_evidence", required_evidence=[])
    with pytest.raises(ValidationError):
        JudgmentNotApplicable(status="not_applicable", reason=" ")


def test_delegation_unreserve_requires_strict_true_attestation() -> None:
    request = {
        "allocation_id": "allocation-1",
        "creation_not_started": True,
        "creation_not_started_reference": {
            "uri": "memory://plan",
            "content_hash": "a" * 64,
        },
        "expected_revision": 2,
        "idempotency_key": "unreserve-1",
    }

    assert DelegationUnreserveRequest.model_validate(request).creation_not_started is True
    assert AdapterDelegationUnreserveRequest is DelegationUnreserveRequest
    for invalid_value in (False, 1, "true"):
        with pytest.raises(ValidationError):
            DelegationUnreserveRequest.model_validate(
                request | {"creation_not_started": invalid_value}
            )

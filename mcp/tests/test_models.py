from __future__ import annotations

import pytest
from pydantic import ValidationError

from token_io_mcp.models import (
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

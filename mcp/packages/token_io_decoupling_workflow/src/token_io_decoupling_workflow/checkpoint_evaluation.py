"""Stateless structural checks over caller supplied checkpoint evidence."""

from __future__ import annotations

from pydantic import Field

from token_io_decoupling_core.models import RuleContext, StrictModel
from token_io_decoupling_core.rules import RuleLoader
from token_io_decoupling_core.workflow_models import (
    EvidenceSubmission,
    FactKey,
    checkpoint_submission_source_input_hash,
)


class StatelessCheckpointResult(StrictModel):
    status: str
    authority: str = "structural_check_only"
    node_id: str
    language: str = "en"
    selected_branch: str | None = None
    missing_facts: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    reason: str
    source_input_hash: str
    rule_hash: str
    instructions: RuleContext | None = None
    next_checkpoint_ids: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(
        default_factory=lambda: [
            "caller supplied facts and evidence are not authenticated",
            "does not authorize execution or establish Agent acceptance",
            "does not persist workflow state or enforce cross-call sequencing",
        ]
    )


def evaluate_checkpoint(
    submission: EvidenceSubmission,
    *,
    rules: RuleLoader,
    language: str = "en",
    expected_rule_hash: str | None = None,
) -> StatelessCheckpointResult:
    """Check supplied fact/evidence shape and rule completeness without retaining state."""
    node_id = submission.node_id
    if language not in {"en", "zh_cn"}:
        raise ValueError("unsupported checkpoint evaluation language")
    context = rules.load_context(node_id.value, language=language)
    source_hash = checkpoint_submission_source_input_hash(submission)
    if submission.input_hash is not None and source_hash != submission.input_hash:
        return StatelessCheckpointResult(
            status="blocked_input",
            node_id=node_id.value,
            language=language,
            reason="source_input_hash_mismatch",
            source_input_hash=source_hash,
            rule_hash=context.context_hash,
        )
    if expected_rule_hash is not None and expected_rule_hash != context.context_hash:
        return StatelessCheckpointResult(
            status="blocked_input",
            node_id=node_id.value,
            language=language,
            reason="stale_rule_hash",
            source_input_hash=source_hash,
            rule_hash=context.context_hash,
        )
    fact_keys = [fact.fact_key.value for fact in submission.facts]
    if len(fact_keys) != len(set(fact_keys)):
        return StatelessCheckpointResult(
            status="blocked_input",
            node_id=node_id.value,
            language=language,
            reason="conflicting_duplicate_facts",
            source_input_hash=source_hash,
            rule_hash=context.context_hash,
        )
    by_key = {fact.fact_key.value: fact.judgment.status for fact in submission.facts}
    missing_facts = [
        key
        for key in context.required_facts
        if by_key.get(key) in (None, "unknown", "missing_evidence")
    ]
    present_evidence = {item.kind.value for item in submission.evidence_refs}
    missing_evidence = [key for key in context.required_evidence if key not in present_evidence]
    branch = None
    if node_id.value == "control":
        determined = [
            fact.judgment.value.value.value
            for fact in submission.facts
            if fact.fact_key is FactKey.PROGRESS_SIGNAL
            and fact.judgment.status == "determined"
            and fact.judgment.value.kind == "enum"
        ]
        branch = determined[0] if len(determined) == 1 else None
    if branch is not None and branch not in context.legal_branches:
        return StatelessCheckpointResult(
            status="blocked_input",
            node_id=node_id.value,
            language=language,
            selected_branch=branch,
            reason="branch_not_allowed_by_current_rule",
            source_input_hash=source_hash,
            rule_hash=context.context_hash,
        )
    incomplete = bool(missing_facts or missing_evidence)
    return StatelessCheckpointResult(
        status="incomplete_for_agent_review" if incomplete else "ready_for_agent_review",
        node_id=node_id.value,
        language=language,
        selected_branch=branch,
        missing_facts=missing_facts,
        missing_evidence=missing_evidence,
        reason="requirements_missing" if incomplete else "requirements_structurally_present",
        source_input_hash=source_hash,
        rule_hash=context.context_hash,
        instructions=context,
        next_checkpoint_ids=context.next_checkpoint_ids,
    )

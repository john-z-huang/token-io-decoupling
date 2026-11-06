from __future__ import annotations

import hashlib
import json
from types import SimpleNamespace
from typing import Any, cast

import pytest
from pydantic import ValidationError

from token_io_decoupling_core.workflow_models import (
    CheckpointEvidenceRef,
    CheckpointFact,
    CheckpointNode,
    EvidenceKind,
    EvidenceSubmission,
    FactDetermined,
    FactKey,
    FactUnknown,
    LegalBranch,
    TypedEvidenceReference,
    checkpoint_submission_source_input_hash,
)
from token_io_decoupling_workflow.checkpoint_evaluation import evaluate_checkpoint
from token_io_decoupling_workflow.payloads import EvaluatePayload
from token_io_decoupling_workflow.rules import RuleLoader


def _submission(
    node: CheckpointNode = CheckpointNode.CONTRACT, *, include_hash: bool = True
) -> EvidenceSubmission:
    submission = EvidenceSubmission(
        node_id=node,
        facts=[
            CheckpointFact(
                fact_key=FactKey.TASK_OBJECTIVE,
                judgment=FactUnknown(status="unknown"),
            )
        ],
    )
    if include_hash:
        return submission.model_copy(
            update={"input_hash": checkpoint_submission_source_input_hash(submission)}
        )
    return submission


def _rules() -> RuleLoader:
    return RuleLoader()


def _complete_submission(node: CheckpointNode) -> EvidenceSubmission:
    rules = _rules()
    context = rules.load_context(node.value)
    facts = []
    for key_text in context.required_facts:
        key = FactKey(key_text)
        if key is FactKey.PROGRESS_SIGNAL:
            judgment = FactDetermined.model_validate(
                {
                    "status": "determined",
                    "value": {"kind": "enum", "value": LegalBranch.CONTINUE},
                }
            )
        elif key is FactKey.TASK_TYPE:
            judgment = FactDetermined.model_validate(
                {"status": "determined", "value": {"kind": "enum", "value": LegalBranch.CODING}}
            )
        else:
            judgment = FactDetermined.model_validate(
                {
                    "status": "determined",
                    "value": {
                        "kind": "semantic_ref",
                        "value": {"uri": "memory://fact", "content_hash": "a" * 64},
                    },
                }
            )
        facts.append(CheckpointFact(fact_key=key, judgment=judgment))
    evidence_refs = [
        TypedEvidenceReference(
            kind=EvidenceKind(evidence),
            reference=CheckpointEvidenceRef(
                uri=f"memory://{index}", content_hash="b" * 64, evidence_id=f"e{index}"
            ),
        )
        for index, evidence in enumerate(context.required_evidence)
    ]
    return EvidenceSubmission(
        node_id=node,
        facts=facts,
        evidence_refs=evidence_refs,
    )


def test_evaluation_reports_missing_requirements_without_claiming_authority() -> None:
    result = evaluate_checkpoint(_submission(), rules=_rules())

    assert result.status == "incomplete_for_agent_review"
    assert result.authority == "structural_check_only"
    assert result.missing_facts
    assert "caller supplied facts and evidence are not authenticated" in result.limitations
    assert result.source_input_hash != "0" * 64


def test_evaluation_blocks_input_hash_and_rule_hash_mismatch() -> None:
    submission = _submission()
    rules = _rules()

    bad_input = submission.model_copy(update={"input_hash": "f" * 64})
    assert evaluate_checkpoint(bad_input, rules=rules).reason == "source_input_hash_mismatch"
    assert (
        evaluate_checkpoint(submission, rules=rules, expected_rule_hash="e" * 64).reason
        == "stale_rule_hash"
    )


def test_evaluation_rejects_duplicate_fact_keys() -> None:
    submission = _submission()
    duplicate = submission.model_copy(update={"facts": [*submission.facts, submission.facts[0]]})
    data = duplicate.model_dump(mode="json", exclude={"input_hash"})
    digest = hashlib.sha256(
        json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()
    duplicate = duplicate.model_copy(update={"input_hash": digest})

    result = evaluate_checkpoint(duplicate, rules=_rules())

    assert result.status == "blocked_input"
    assert result.reason == "conflicting_duplicate_facts"


def test_evaluation_accepts_absent_hash_and_returns_computed_hash() -> None:
    submission = _complete_submission(CheckpointNode.TASK_INTENT)

    result = evaluate_checkpoint(submission, rules=_rules())

    assert result.status == "ready_for_agent_review"
    assert result.source_input_hash == checkpoint_submission_source_input_hash(submission)


def test_control_evaluation_accepts_legal_branch() -> None:
    submission = _complete_submission(CheckpointNode.CONTROL)

    result = evaluate_checkpoint(submission, rules=_rules())

    assert result.status == "ready_for_agent_review"
    assert result.selected_branch == "continue"


def test_evaluation_uses_selected_language_rule_hash() -> None:
    rules = _rules()
    submission = _complete_submission(CheckpointNode.TASK_INTENT)
    english = rules.load_context(CheckpointNode.TASK_INTENT.value, language="en")
    chinese = rules.load_context(CheckpointNode.TASK_INTENT.value, language="zh_cn")

    assert english.context_hash != chinese.context_hash
    assert (
        evaluate_checkpoint(
            submission, rules=rules, language="en", expected_rule_hash=english.context_hash
        ).status
        == "ready_for_agent_review"
    )
    assert (
        evaluate_checkpoint(
            submission, rules=rules, language="zh_cn", expected_rule_hash=chinese.context_hash
        ).status
        == "ready_for_agent_review"
    )
    assert (
        evaluate_checkpoint(
            submission, rules=rules, language="zh_cn", expected_rule_hash=english.context_hash
        ).reason
        == "stale_rule_hash"
    )
    assert (
        evaluate_checkpoint(
            submission, rules=rules, language="en", expected_rule_hash=chinese.context_hash
        ).reason
        == "stale_rule_hash"
    )


def test_default_compiled_bundle_hash_is_checkpoint_rule_hash() -> None:
    rules = _rules()
    node_id = CheckpointNode.TASK_INTENT.value
    submission = _complete_submission(CheckpointNode.TASK_INTENT)
    full_context = rules.load_context(node_id, language="en")
    fragment_bundle = rules.load_context_bundle(node_id, language="en")

    assert fragment_bundle.context_hash == full_context.context_hash
    result = evaluate_checkpoint(
        submission, rules=rules, language="en", expected_rule_hash=fragment_bundle.context_hash
    )
    assert result.status == "ready_for_agent_review"
    assert result.instructions is not None
    assert result.instructions.owner_text == fragment_bundle.fragments[0].text


def test_evaluation_payload_bounds_current_facts_and_language() -> None:
    base = {
        "node_id": CheckpointNode.CONTRACT.value,
        "submission": json.loads(_submission(include_hash=False).model_dump_json()),
    }
    EvaluatePayload.model_validate_json(
        json.dumps({**base, "language": "zh_cn", "current_facts": {}})
    )

    with pytest.raises(ValidationError):
        EvaluatePayload.model_validate_json(
            json.dumps(
                {
                    **base,
                    "current_facts": {f"key-{index}": "x" for index in range(17)},
                }
            )
        )
    with pytest.raises(ValidationError):
        EvaluatePayload.model_validate_json(
            json.dumps({**base, "current_facts": {"key": {"nested": "value"}}})
        )
    with pytest.raises(ValidationError):
        EvaluatePayload.model_validate_json(
            json.dumps({**base, "current_facts": {"key": "x" * 1025}})
        )
    with pytest.raises(ValidationError):
        EvaluatePayload.model_validate_json(
            json.dumps(
                {
                    **base,
                    "submission": {
                        **base["submission"],
                        "evidence_refs": [
                            {
                                "kind": EvidenceKind.READ_ONLY_GIT_STATE.value,
                                "reference": {
                                    "uri": "x" * 512,
                                    "content_hash": "a" * 64,
                                    "evidence_id": "e" * 128,
                                },
                            }
                            for _ in range(48)
                        ],
                    },
                    "current_facts": {f"key-{index}": "x" * 1024 for index in range(8)},
                }
            )
        )


def test_submission_rejects_just_over_nested_item_limits() -> None:
    base = json.loads(_submission(include_hash=False).model_dump_json())
    invalid_submissions = []
    invalid_submissions.append({**base, "facts": base["facts"] * 129})
    invalid_submissions.append(
        {
            **base,
            "evidence_refs": [
                {
                    "kind": EvidenceKind.READ_ONLY_GIT_STATE.value,
                    "reference": {
                        "uri": "memory://evidence",
                        "content_hash": "a" * 64,
                        "evidence_id": "evidence",
                    },
                }
                for _ in range(129)
            ],
        }
    )
    invalid_submissions.append(
        {
            **base,
            "coverage_dimensions": [
                "implementation_content",
                "documentation",
                "git_metadata",
                "implementation_content",
            ],
        }
    )
    invalid_submissions.append(
        {
            **base,
            "facts": [
                {
                    "fact_key": FactKey.TASK_OBJECTIVE.value,
                    "judgment": {
                        "status": "determined",
                        "value": {
                            "kind": "semantic_ref",
                            "value": {"uri": "memory://fact", "content_hash": "a" * 64},
                        },
                        "evidence": [
                            {
                                "kind": EvidenceKind.READ_ONLY_GIT_STATE.value,
                                "reference": {
                                    "uri": "memory://evidence",
                                    "content_hash": "b" * 64,
                                    "evidence_id": f"e{index}",
                                },
                            }
                            for index in range(17)
                        ],
                    },
                }
            ],
        }
    )

    for invalid in invalid_submissions:
        with pytest.raises(ValidationError):
            EvidenceSubmission.model_validate_json(json.dumps(invalid))


def test_evaluation_callback_passes_same_language_to_fake_advisor() -> None:
    from token_io_decoupling_transport.tool import ToolDefinition
    from token_io_decoupling_workflow.tool import register_tools

    class FakeRegistrar:
        def __init__(self) -> None:
            self.callbacks: dict[str, Any] = {}

        def register_all(self, definitions: tuple[ToolDefinition, ...]) -> None:
            self.callbacks = {definition.name: definition.callback for definition in definitions}

    class FakeAdvisor:
        calls: list[dict[str, Any]] = []

        def advise(self, advisory_input: Any, **kwargs: Any) -> Any:
            self.calls.append(kwargs)
            return SimpleNamespace(model_dump=lambda mode="json": {"status": "fallback"})

    rules = _rules()
    registrar = FakeRegistrar()
    advisor = FakeAdvisor()
    cast(Any, register_tools)(
        registrar,
        rules=rules,
        advisor=advisor,
        decisions_config=None,
        capability_callback=lambda: {},
    )
    language = "zh_cn"
    expected = rules.load_context(CheckpointNode.TASK_INTENT.value, language=language)
    payload = EvaluatePayload.model_validate_json(
        json.dumps(
            {
                "node_id": CheckpointNode.TASK_INTENT.value,
                "language": language,
                "submission": _submission(
                    CheckpointNode.TASK_INTENT, include_hash=False
                ).model_dump(mode="json"),
                "semantic_input": {
                    "node_id": "task_intent",
                    "requested_outcome": "Inspect the current task objective",
                    "task_signal": "coding",
                },
            }
        )
    )

    output = registrar.callbacks["workflow_evaluate"](payload)

    assert output["language"] == language
    assert len(advisor.calls) == 1
    assert advisor.calls[0]["language"] == language
    assert advisor.calls[0]["expected_rule_hash"] == expected.context_hash
    assert advisor.calls[0]["checkpoint_source_input_hash"] == output["source_input_hash"]

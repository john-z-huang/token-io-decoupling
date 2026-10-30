from __future__ import annotations

import pytest
from token_io_decoupling_core.state_models import CheckpointNode
from token_io_decoupling_workflow.api_recovery import (
    classify_provider_failure,
    recovery_for_provider_failure,
    recovery_for_reason,
)
from token_io_decoupling_workflow.child_effort import ChildEffortResult
from token_io_decoupling_workflow.decision_context import DecisionContextResult
from token_io_decoupling_workflow.decisions import DecisionAdvice
from token_io_decoupling_workflow.delegation_decisions import DelegationDecisionResult


class APIStatusError(Exception):
    def __init__(self, status_code: int, code: str | None = None) -> None:
        super().__init__("private response text")
        self.status_code = status_code
        self.code = code


def test_transient_candidates_are_bounded_and_safe() -> None:
    class APITimeoutError(Exception):
        pass

    failures = [
        APITimeoutError("private timeout body"),
        APIStatusError(503, "temporary_server_error"),
        APIStatusError(429, "rate_limit_exceeded"),
    ]
    for error in failures:
        failure = classify_provider_failure(error)
        recovery = recovery_for_provider_failure(failure)
        assert recovery.retry_eligible is True
        assert recovery.total_attempt_limit == 3
        assert "private" not in recovery.model_dump_json()


def test_hard_failures_win_over_transient_status_or_exception_name() -> None:
    class APITimeoutError(Exception):
        status_code = 401
        code = "insufficient_quota"

    cases = [
        (APITimeoutError("timeout"), "authentication"),
        (APIStatusError(403, "rate_limit_exceeded"), "authorization"),
        (APIStatusError(503, "invalid_api_key"), "authentication"),
        (APIStatusError(503, "insufficient_quota"), "quota"),
        (APIStatusError(429, "insufficient_quota"), "quota"),
        (APIStatusError(404, "model_not_found"), "not_found"),
        (APIStatusError(429), "rate_limit"),
        (APIStatusError(400, "rate_limit_exceeded"), "unknown"),
        (APIStatusError(503, "rate_limit_exceeded"), "unknown"),
    ]
    for error, expected_class in cases:
        failure = classify_provider_failure(error)
        recovery = recovery_for_provider_failure(failure)
        assert failure.failure_class == expected_class
        assert recovery.retry_eligible is False
        assert recovery.total_attempt_limit is None
        if expected_class == "not_found":
            assert recovery.action == "restore_fixed_api_access"


@pytest.mark.parametrize(
    "reason,expected_action",
    [
        ("stale_policy", "refresh_current_facts_and_policy"),
        ("missing_credentials", "resolve_credentials_or_configuration"),
        ("outbound_data_not_permitted", "resolve_permission"),
        ("refusal", "correct_input_or_review_evidence"),
        ("invalid_response", "correct_input_or_review_evidence"),
        ("incomplete_response", "correct_input_or_review_evidence"),
        ("insufficient_evidence", "correct_input_or_review_evidence"),
        ("idempotent_replay", "no_action"),
    ],
)
def test_non_provider_exits_are_not_retry_candidates(reason: str, expected_action: str) -> None:
    recovery = recovery_for_reason(reason)

    assert recovery.retry_eligible is False
    assert recovery.action == expected_action
    assert recovery.total_attempt_limit is None


def test_unknown_or_unreadable_provider_attributes_fail_closed() -> None:
    class UnknownTimeoutError(Exception):
        pass

    class APITimeoutError(Exception):
        @property
        def status_code(self) -> int:
            raise RuntimeError("private attribute failure")

    class APITimeoutErrorWithInvalidStatus(Exception):
        status_code = "503"

    class APITimeoutErrorWithOutOfRangeStatus(Exception):
        status_code = 600

    class APITimeoutErrorWithUnreadableCode(Exception):
        @property
        def code(self) -> str:
            raise RuntimeError("private code access failure")

    class APITimeoutErrorWithUnreadableBody(Exception):
        code = None

        @property
        def body(self) -> dict[str, object]:
            raise RuntimeError("private body access failure")

    for error in (
        UnknownTimeoutError("timeout"),
        APITimeoutError("private"),
        APITimeoutErrorWithInvalidStatus("private"),
        APITimeoutErrorWithOutOfRangeStatus("private"),
        APITimeoutErrorWithUnreadableCode("private"),
        APITimeoutErrorWithUnreadableBody("private"),
    ):
        failure = classify_provider_failure(error)
        recovery = recovery_for_provider_failure(failure)
        assert failure.failure_class == "unknown"
        assert recovery.retry_eligible is False
        assert "private" not in recovery.model_dump_json()


def test_public_result_models_expose_nullable_recovery_field() -> None:
    schemas = [
        ChildEffortResult.model_json_schema(),
        DecisionContextResult.model_json_schema(),
        DelegationDecisionResult.model_json_schema(),
        DecisionAdvice.model_json_schema(),
    ]
    for schema in schemas:
        assert "recovery" in schema["properties"]
        assert "null" in str(schema["properties"]["recovery"])
        assert schema["properties"]["recovery"]["default"] is None

    outputs = [
        ChildEffortResult(
            status="available",
            reason="effort_selected",
            selected_effort="medium",
            input_hash="a" * 64,
            slice_fingerprint="b" * 64,
        ),
        DecisionContextResult(
            status="available",
            reason="description_generated",
            description="Reviewed context.",
            input_hash="c" * 64,
            output_kind="decision_context",
        ),
        DelegationDecisionResult(
            status="available",
            decision="child_role",
            reason="suggestion_available",
            suggested_value="Primary Output",
            next_action="review_suggestion",
            fact_revision=1,
            fact_fingerprint="d" * 64,
            context_input_hash="e" * 64,
        ),
        DecisionAdvice(
            status="available",
            reason="advice_available",
            node_id=CheckpointNode.TASK_INTENT,
        ),
    ]
    assert all(output.model_dump(mode="json")["recovery"] is None for output in outputs)

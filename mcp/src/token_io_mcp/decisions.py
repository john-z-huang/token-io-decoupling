"""Bounded, non-authoritative Decisions API advice for selected Coding checkpoints."""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Callable
from typing import Annotated, Any, Literal, TypeAlias, cast

from pydantic import ConfigDict, Field, StrictBool, StrictStr, model_validator

from token_io_mcp.models import RuleContext, StrictModel
from token_io_mcp.rules import RuleLoader
from token_io_mcp.state_models import (
    CheckpointEvaluation,
    CheckpointNode,
    EpochDimension,
    EpochSnapshot,
    WorkflowState,
)
from token_io_mcp.state_service import BindingError, StateService

DECISIONS_MODEL = "gpt-6-luna"
DECISIONS_TIMEOUT_SECONDS = 20.0
MAX_REQUEST_CHARS = 8_000
SUPPORTED_ADVISORY_NODES = frozenset(
    {
        CheckpointNode.TASK_INTENT,
        CheckpointNode.OUTPUT_CLASS,
        CheckpointNode.CONTRACT_CHANGE,
        CheckpointNode.VERIFICATION_IMPACT,
        CheckpointNode.CONTROL,
    }
)

ShortText = Annotated[StrictStr, Field(min_length=1, max_length=400)]
DeliverableList = Annotated[list[ShortText], Field(max_length=5)]


class AdvisoryInputBase(StrictModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class TaskIntentInput(AdvisoryInputBase):
    node_id: Literal[CheckpointNode.TASK_INTENT]
    requested_outcome: ShortText
    deliverables: DeliverableList = Field(default_factory=list)
    task_signal: Literal["coding", "not_coding", "mixed", "unclear"]


class OutputClassInput(AdvisoryInputBase):
    node_id: Literal[CheckpointNode.OUTPUT_CLASS]
    requested_output: ShortText
    deliverables: DeliverableList = Field(default_factory=list)
    delegation_boundary: Literal["root_only", "worker_eligible", "mixed", "unclear"]


class ContractChangeInput(AdvisoryInputBase):
    node_id: Literal[CheckpointNode.CONTRACT_CHANGE]
    change_summary: ShortText
    objective_or_scope_changed: StrictBool
    new_user_direction_present: StrictBool


class VerificationImpactInput(AdvisoryInputBase):
    node_id: Literal[CheckpointNode.VERIFICATION_IMPACT]
    change_summary: ShortText
    changed_dimensions: Annotated[list[EpochDimension], Field(max_length=3)]
    affected_coverage: Annotated[list[EpochDimension], Field(max_length=3)]

    @model_validator(mode="after")
    def affected_coverage_is_bounded_by_change(self) -> VerificationImpactInput:
        if not set(self.affected_coverage) <= set(self.changed_dimensions):
            raise ValueError("affected coverage must be included in changed dimensions")
        return self


class ControlInput(AdvisoryInputBase):
    node_id: Literal[CheckpointNode.CONTROL]
    progress_signal: Literal["continue", "amend", "stop", "evidence-on-demand"]
    slice_outcome: Literal["ready", "incomplete", "blocked", "returned"]
    evidence_request_status: Literal["not_requested", "pending", "returned"]
    boundary_summary: ShortText


DecisionAdvisoryInput: TypeAlias = Annotated[
    TaskIntentInput
    | OutputClassInput
    | ContractChangeInput
    | VerificationImpactInput
    | ControlInput,
    Field(discriminator="node_id"),
]


class DecisionsRuntimeConfig(StrictModel):
    enabled: StrictBool = False
    outbound_data_permitted: StrictBool = False

    @model_validator(mode="after")
    def enabled_requires_explicit_outbound_permission(self) -> DecisionsRuntimeConfig:
        if self.enabled and not self.outbound_data_permitted:
            raise ValueError("Decisions requires explicit outbound data permission")
        return self


FailureClass: TypeAlias = Literal[
    "transport",
    "authentication",
    "authorization",
    "not_found",
    "rate_limit",
    "quota",
    "api",
    "sdk_contract",
    "configuration",
    "unknown",
]
ProviderErrorCode: TypeAlias = Literal[
    "invalid_api_key",
    "model_not_found",
    "insufficient_quota",
    "rate_limit_exceeded",
    "other",
]


class DecisionAdvice(StrictModel):
    status: Literal["available", "fallback", "stale"]
    reason: Literal[
        "disabled",
        "advice_available",
        "core_blocked",
        "state_context_unavailable",
        "rule_context_unavailable",
        "missing_credentials",
        "provider_error",
        "timeout",
        "refusal",
        "invalid_response",
        "rule_context_too_large",
        "binding_unavailable",
        "stale_context",
        "idempotent_replay",
    ]
    failure_class: FailureClass | None = None
    http_status: Annotated[int, Field(ge=100, le=599)] | None = None
    provider_error_code: ProviderErrorCode | None = None
    node_id: CheckpointNode
    suggested_choice: str | None = None
    input_hash: str | None = None
    rule_hash: str | None = None
    basis_revision: int | None = None
    epochs: EpochSnapshot | None = None
    model: Literal["gpt-6-luna"] | None = None
    total_tokens: int | None = None


class EvaluationWithAdvice(StrictModel):
    evaluation: CheckpointEvaluation
    advice: DecisionAdvice


_QUESTIONS: dict[CheckpointNode, tuple[str, str]] = {
    CheckpointNode.TASK_INTENT: (
        "task_intent",
        "Classify the request from the facts and owner excerpt; choose the best-supported option.",
    ),
    CheckpointNode.OUTPUT_CLASS: (
        "output_class",
        "Classify the deliverable from facts and owner excerpt; choose the best-supported option.",
    ),
    CheckpointNode.CONTRACT_CHANGE: (
        "contract_change",
        "Classify the stated change using supplied facts and owner excerpt.",
    ),
    CheckpointNode.VERIFICATION_IMPACT: (
        "verification_impact",
        "Classify the affected state dimensions using only the supplied change and coverage facts.",
    ),
    CheckpointNode.CONTROL: (
        "control",
        "Advise the best-supported Control signal from supplied facts and owner excerpt.",
    ),
}

ClientFactory = Callable[[str, str], object]


class DecisionsAdvisor:
    """Ask for one fixed-choice suggestion; never authorizes or mutates Core state."""

    def __init__(
        self,
        state_service: StateService,
        rule_loader: RuleLoader,
        config: DecisionsRuntimeConfig,
        *,
        client_factory: ClientFactory | None = None,
    ) -> None:
        self._state_service = state_service
        self._rule_loader = rule_loader
        self._config = config
        self._client_factory = client_factory

    def advise(
        self,
        advisory_input: DecisionAdvisoryInput,
        *,
        core_evaluation: CheckpointEvaluation | None = None,
        replayed: bool = False,
    ) -> DecisionAdvice:
        node_id = advisory_input.node_id
        if replayed:
            return DecisionAdvice(status="fallback", reason="idempotent_replay", node_id=node_id)
        if core_evaluation is not None and core_evaluation.outcome == "blocked":
            return DecisionAdvice(status="fallback", reason="core_blocked", node_id=node_id)
        if not self._config.enabled:
            return DecisionAdvice(status="fallback", reason="disabled", node_id=node_id)
        if node_id not in SUPPORTED_ADVISORY_NODES:
            return DecisionAdvice(status="fallback", reason="invalid_response", node_id=node_id)

        try:
            state = (
                self._state_service.workflow_get_state_for_evaluation(core_evaluation)
                if core_evaluation is not None
                else self._state_service.workflow_get_state()
            )
            if state is None:
                return DecisionAdvice(status="stale", reason="stale_context", node_id=node_id)
        except BindingError:
            return DecisionAdvice(status="fallback", reason="binding_unavailable", node_id=node_id)
        except Exception:
            return DecisionAdvice(
                status="fallback", reason="state_context_unavailable", node_id=node_id
            )
        try:
            rules = self._rule_loader.load_context(node_id.value)
        except Exception:
            return DecisionAdvice(
                status="fallback", reason="rule_context_unavailable", node_id=node_id
            )

        allowed = list(rules.legal_branches)
        if not allowed:
            return DecisionAdvice(status="fallback", reason="invalid_response", node_id=node_id)
        if len(_request_input(advisory_input, rules)) > MAX_REQUEST_CHARS:
            return _fallback("rule_context_too_large", node_id, "", rules, state)
        if core_evaluation is not None and (
            core_evaluation.node_id is not node_id
            or core_evaluation.stale
            or core_evaluation.result_revision != state.revision
            or core_evaluation.epochs != state.epochs
            or core_evaluation.rule_hash != rules.context_hash
        ):
            return _fallback("stale_context", node_id, "", rules, state)
        basis_hash = _basis_hash(advisory_input, state, rules.context_hash)
        api_key = os.environ.get("OPENAI_API_KEY")
        base_url = os.environ.get("OPENAI_BASE_URL")
        if not api_key or not api_key.strip() or not base_url or not base_url.strip():
            return _fallback("missing_credentials", node_id, basis_hash, rules, state)

        client: object | None = None
        try:
            client = self._make_client(api_key, base_url)
            question_name, instructions = _QUESTIONS[node_id]
            request_input = _request_input(advisory_input, rules)
            response = cast(Any, client).decisions.create(
                model=DECISIONS_MODEL,
                input=request_input,
                questions=[
                    {
                        "type": "choice",
                        "name": question_name,
                        "instructions": instructions,
                        "choices": [
                            {
                                "value": choice,
                                "description": "Option supported by the supplied facts.",
                            }
                            for choice in allowed
                        ],
                    }
                ],
            )
        except Exception as exc:
            reason, failure_class, http_status, error_code = _provider_failure(exc)
            return _fallback(
                reason,
                node_id,
                basis_hash,
                rules,
                state,
                failure_class=failure_class,
                http_status=http_status,
                provider_error_code=error_code,
            )
        finally:
            close = getattr(client, "close", None)
            if callable(close):
                try:
                    close()
                except Exception:
                    pass

        answer = _validated_choice(response, question_name, set(allowed))
        if answer is None:
            reason = "refusal" if _is_refusal(response, question_name) else "invalid_response"
            return _fallback(reason, node_id, basis_hash, rules, state)
        response_model = getattr(response, "model", None)
        if response_model is not None and response_model != DECISIONS_MODEL:
            return _fallback("invalid_response", node_id, basis_hash, rules, state)

        try:
            current_state = (
                self._state_service.workflow_get_state_for_evaluation(core_evaluation)
                if core_evaluation is not None
                else self._state_service.workflow_get_state()
            )
            if current_state is None:
                return DecisionAdvice(status="stale", reason="stale_context", node_id=node_id)
            current_rules = self._rule_loader.load_context(node_id.value)
        except BindingError:
            return _fallback("binding_unavailable", node_id, basis_hash, rules, state)
        except Exception:
            return _fallback("stale_context", node_id, basis_hash, rules, state)
        if (
            current_rules.context_hash != rules.context_hash
            or _basis_hash(advisory_input, current_state, current_rules.context_hash) != basis_hash
        ):
            return DecisionAdvice(
                status="stale",
                reason="stale_context",
                node_id=node_id,
                input_hash=basis_hash,
                rule_hash=rules.context_hash,
                basis_revision=state.revision,
                epochs=state.epochs,
            )
        usage = getattr(response, "usage", None)
        total_tokens = getattr(usage, "total_tokens", None)
        if type(total_tokens) is not int or total_tokens < 0:
            total_tokens = None
        return DecisionAdvice(
            status="available",
            reason="advice_available",
            node_id=node_id,
            suggested_choice=answer,
            input_hash=basis_hash,
            rule_hash=rules.context_hash,
            basis_revision=state.revision,
            epochs=state.epochs,
            model=DECISIONS_MODEL,
            total_tokens=total_tokens,
        )

    def _make_client(self, api_key: str, base_url: str) -> object:
        if self._client_factory is not None:
            return self._client_factory(api_key, base_url)
        from openai import OpenAI

        return OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=DECISIONS_TIMEOUT_SECONDS,
            max_retries=0,
        )


def _basis_hash(advisory_input: DecisionAdvisoryInput, state: WorkflowState, rule_hash: str) -> str:
    basis = {
        "input": advisory_input.model_dump(mode="json"),
        "project_id": state.project_id,
        "root_session_id": state.root_session_id,
        "run_id": state.run_id,
        "rule_hash": rule_hash,
        "revision": state.revision,
        "mode_count": state.mode_count.model_dump(mode="json"),
        "mode_source": state.mode_source,
        "lifecycle": state.lifecycle,
        "epochs": state.epochs.model_dump(mode="json"),
    }
    encoded = json.dumps(basis, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _request_input(advisory_input: DecisionAdvisoryInput, rules: RuleContext) -> str:
    facts = advisory_input.model_dump(mode="json", exclude={"node_id"})
    payload = {
        "node_id": advisory_input.node_id.value,
        "facts": facts,
        "rule_facts": rules.required_facts,
        "rule_evidence": rules.required_evidence,
        "allowed_choices": rules.legal_branches,
        "owner_section": {
            "source": rules.owner_path,
            "heading": rules.owner_section,
            "text": rules.owner_text,
        },
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _validated_choice(response: object, expected_name: str, allowed: set[str]) -> str | None:
    answers = getattr(response, "answers", None)
    if not isinstance(answers, (list, tuple)) or len(answers) != 1:
        return None
    answer = answers[0]
    if getattr(answer, "type", None) != "choice" or getattr(answer, "name", None) != expected_name:
        return None
    choice = getattr(answer, "choice", None)
    return choice if isinstance(choice, str) and choice in allowed else None


def _is_refusal(response: object, expected_name: str) -> bool:
    answers = getattr(response, "answers", None)
    return (
        isinstance(answers, (list, tuple))
        and len(answers) == 1
        and getattr(answers[0], "type", None) == "refusal"
        and getattr(answers[0], "name", None) == expected_name
    )


def _provider_failure(
    exc: Exception,
) -> tuple[
    Literal["provider_error", "timeout"],
    FailureClass,
    int | None,
    ProviderErrorCode | None,
]:
    error_name = type(exc).__name__
    status_value = getattr(exc, "status_code", None)
    status = status_value if type(status_value) is int and 100 <= status_value <= 599 else None
    raw_code = getattr(exc, "code", None)
    if not isinstance(raw_code, str):
        body = getattr(exc, "body", None)
        error = body.get("error") if isinstance(body, dict) else None
        if isinstance(error, dict):
            raw_code = error.get("code")
            if not isinstance(raw_code, str):
                raw_code = error.get("type")
    allowed_codes = {
        "invalid_api_key",
        "model_not_found",
        "insufficient_quota",
        "rate_limit_exceeded",
    }
    code = raw_code if isinstance(raw_code, str) and raw_code in allowed_codes else None

    if error_name in {"APITimeoutError", "APIConnectionError", "APIConnectionTimeoutError"}:
        reason = "timeout" if error_name == "APITimeoutError" else "provider_error"
        return reason, "transport", status, code
    if isinstance(exc, (TypeError, ValueError)):
        return "provider_error", "configuration", status, code
    if error_name == "APIResponseValidationError":
        return "provider_error", "sdk_contract", status, code
    if status == 401 or code == "invalid_api_key":
        return "provider_error", "authentication", status, "invalid_api_key" if code else None
    if status == 403:
        safe_code: ProviderErrorCode | None = code
        if safe_code is None and isinstance(raw_code, str):
            safe_code = "other"
        return "provider_error", "authorization", status, safe_code
    if status == 404 or code == "model_not_found":
        return "provider_error", "not_found", status, "model_not_found" if code else None
    if code == "insufficient_quota":
        return "provider_error", "quota", status, code
    if status == 429 or code == "rate_limit_exceeded":
        return "provider_error", "rate_limit", status, "rate_limit_exceeded" if code else None
    if status is not None:
        return "provider_error", "api", status, "other" if isinstance(raw_code, str) else None
    return "provider_error", "unknown", None, None


def _fallback(
    reason: Literal[
        "missing_credentials",
        "provider_error",
        "timeout",
        "refusal",
        "invalid_response",
        "rule_context_too_large",
        "state_context_unavailable",
        "rule_context_unavailable",
        "binding_unavailable",
        "stale_context",
    ],
    node_id: CheckpointNode,
    input_hash: str,
    rules: RuleContext,
    state: WorkflowState,
    *,
    failure_class: FailureClass | None = None,
    http_status: int | None = None,
    provider_error_code: ProviderErrorCode | None = None,
) -> DecisionAdvice:
    return DecisionAdvice(
        status="fallback" if reason != "stale_context" else "stale",
        reason=reason,
        node_id=node_id,
        input_hash=input_hash,
        rule_hash=rules.context_hash,
        basis_revision=state.revision,
        epochs=state.epochs,
        failure_class=failure_class,
        http_status=http_status,
        provider_error_code=provider_error_code,
    )

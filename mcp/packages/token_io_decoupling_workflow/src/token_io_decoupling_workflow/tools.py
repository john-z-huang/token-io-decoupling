"""Registration for public workflow information and workflow evaluation tools."""

from __future__ import annotations

from typing import Any

from token_io_decoupling_core.rules import RuleLoader
from token_io_decoupling_core.state_models import CheckpointNode
from token_io_decoupling_state.service import StateService
from token_io_decoupling_transport.payloads import _RULE_CONTEXT
from token_io_decoupling_transport.registration import ToolRegistrar

from token_io_decoupling_workflow.child_effort import (
    ChildEffortPayload,
    ChildEffortSelector,
)
from token_io_decoupling_workflow.decision_context import (
    DecisionContextGenerator,
    DecisionContextPayload,
)
from token_io_decoupling_workflow.decisions import (
    DecisionAdvice,
    DecisionAdvisoryInput,
    DecisionsAdvisor,
    DecisionsRuntimeConfig,
    EvaluationWithAdvice,
)
from token_io_decoupling_workflow.payloads import _CONTROL_EVALUATE, _EVALUATE


def _evaluate_with_advice(
    evaluation: Any,
    advisory_input: DecisionAdvisoryInput | None,
    advisor: DecisionsAdvisor,
    *,
    replayed: bool = False,
) -> Any:
    if advisory_input is None:
        return evaluation
    if advisory_input.node_id is not evaluation.node_id:
        return EvaluationWithAdvice(
            evaluation=evaluation,
            advice=DecisionAdvice(
                status="fallback",
                reason="invalid_response",
                node_id=advisory_input.node_id,
            ),
        )
    advice = (
        DecisionAdvice(
            status="fallback",
            reason="idempotent_replay",
            node_id=advisory_input.node_id,
        )
        if replayed
        else advisor.advise(advisory_input, core_evaluation=evaluation)
    )
    return EvaluationWithAdvice(evaluation=evaluation, advice=advice)


def register_workflow_tools(
    registrar: ToolRegistrar,
    *,
    service: StateService,
    rules: RuleLoader,
    advisor: DecisionsAdvisor,
    decisions_config: DecisionsRuntimeConfig | None,
    provider: Any,
    embedded: bool,
    require_codex_context: bool,
    binding_diagnostic: Any,
) -> None:
    effort_selector = ChildEffortSelector()
    context_generator = DecisionContextGenerator()
    registrar.register_no_args(
        "workflow_capabilities",
        lambda: {
            "subsystem": "token-io-mcp",
            "supported_transports": ["stdio"],
            "host_adapters": {
                "Codex Desktop": {
                    "identity_attestation": "unavailable",
                    "guard_binding": "unavailable",
                },
                "ChatGPT Desktop": {
                    "identity_attestation": "unavailable",
                    "guard_binding": "unavailable",
                },
            },
            "enhanced_binding": "unverified" if not embedded else binding_diagnostic(provider),
            "binding_transport": (
                getattr(provider, "transport", "embedded_provider") if embedded else "unavailable"
            ),
            "caller_match": "required" if require_codex_context else "disabled",
            "mode_fallback": "Native",
            "api_decisions": "enabled"
            if decisions_config and decisions_config.enabled
            else "disabled",
            "child_effort_decisions": "available_per_invocation",
            "decision_context_generation": "available_per_invocation",
            "protocol_target": "2026-07-28",
        },
    )
    registrar.register(
        "rules_get_context",
        _RULE_CONTEXT,
        lambda payload: rules.load_context(payload.node_id.value, language=payload.language),
        enhanced=False,
    )
    registrar.register(
        "workflow_select_child_effort",
        ChildEffortPayload,
        lambda payload: effort_selector.select(payload.request),
        enhanced=False,
    )
    registrar.register(
        "workflow_generate_decision_context",
        DecisionContextPayload,
        lambda payload: context_generator.generate(payload.request),
        enhanced=False,
    )

    def evaluate_node(payload: Any) -> Any:
        if payload.semantic_input is None:
            return service.workflow_evaluate(
                payload.node_id,
                expected_revision=payload.expected_revision,
                idempotency_key=payload.idempotency_key,
                branch=payload.branch.value if payload.branch else None,
                input_hash=payload.input_hash,
                slice_ids=payload.slice_ids,
            )
        if payload.semantic_input.node_id is not payload.node_id:
            raise ValueError("semantic input node must match the evaluated checkpoint")
        evaluation, replayed = service.workflow_evaluate_with_replay(
            payload.node_id,
            expected_revision=payload.expected_revision,
            idempotency_key=payload.idempotency_key,
            branch=payload.branch.value if payload.branch else None,
            input_hash=payload.input_hash,
            slice_ids=payload.slice_ids,
        )
        return _evaluate_with_advice(evaluation, payload.semantic_input, advisor, replayed=replayed)

    def evaluate_control(payload: Any) -> Any:
        if payload.semantic_input is None:
            return service.evaluate_control_checkpoint(
                expected_revision=payload.expected_revision,
                idempotency_key=payload.idempotency_key,
                branch=payload.branch.value if payload.branch else None,
                input_hash=payload.input_hash,
                slice_ids=payload.slice_ids,
            )
        if payload.semantic_input.node_id is not CheckpointNode.CONTROL:
            raise ValueError("control evaluation requires Control semantic input")
        evaluation, replayed = service.evaluate_control_checkpoint_with_replay(
            expected_revision=payload.expected_revision,
            idempotency_key=payload.idempotency_key,
            branch=payload.branch.value if payload.branch else None,
            input_hash=payload.input_hash,
            slice_ids=payload.slice_ids,
        )
        return _evaluate_with_advice(evaluation, payload.semantic_input, advisor, replayed=replayed)

    registrar.register("workflow_evaluate", _EVALUATE, evaluate_node, role="parent")
    registrar.register(
        "evaluate_control_checkpoint", _CONTROL_EVALUATE, evaluate_control, role="parent"
    )

"""Registration for public workflow information and workflow evaluation tools."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from token_io_decoupling_core.binding import BindingProvider
from token_io_decoupling_core.rules import RuleLoader
from token_io_decoupling_core.state_models import CheckpointNode
from token_io_decoupling_state.service import StateService
from token_io_decoupling_transport.payloads import _RULE_CONTEXT
from token_io_decoupling_transport.registration import ToolRegistrar

from token_io_decoupling_workflow.capabilities import capability_report
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
from token_io_decoupling_workflow.delegation_decisions import (
    ChildCandidateSelectionPayload,
    ChildRoleSelectionPayload,
    DelegationDecisionSelector,
    ExecutorSelectionPayload,
    OutputTokenRoutingPayload,
)
from token_io_decoupling_workflow.payloads import _CONTROL_EVALUATE, _EVALUATE
from token_io_decoupling_workflow.task_plan_core import TaskPlanService
from token_io_decoupling_workflow.task_plan_payloads import (
    TaskPlanArchivePayload,
    TaskPlanCompletePayload,
    TaskPlanUpdatePayload,
)


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
    task_plan_service: TaskPlanService,
    rules: RuleLoader,
    advisor: DecisionsAdvisor,
    decisions_config: DecisionsRuntimeConfig | None,
    provider: BindingProvider,
    embedded: bool,
    require_codex_context: bool,
    binding_details: Callable[[BindingProvider], dict[str, str]],
) -> None:
    effort_selector = ChildEffortSelector()
    context_generator = DecisionContextGenerator(rules=rules)
    delegation_selector = DelegationDecisionSelector(rules)
    registrar.register_no_args(
        "workflow_capabilities",
        lambda: capability_report(
            provider,
            embedded=embedded,
            require_codex_context=require_codex_context,
            api_decisions_enabled=bool(decisions_config and decisions_config.enabled),
            diagnose_binding=binding_details,
            task_plan_service=task_plan_service,
        ),
    )
    registrar.register(
        "task_plan_update",
        TaskPlanUpdatePayload,
        lambda payload: task_plan_service.update(payload.request.model_dump(mode="json")),
        enhanced=False,
    )
    registrar.register(
        "task_plan_complete",
        TaskPlanCompletePayload,
        lambda payload: task_plan_service.complete(payload.request.model_dump(mode="json")),
        enhanced=False,
    )
    registrar.register(
        "task_plan_archive",
        TaskPlanArchivePayload,
        lambda payload: task_plan_service.archive(payload.request.model_dump(mode="json")),
        enhanced=False,
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
    registrar.register(
        "workflow_select_child_role",
        ChildRoleSelectionPayload,
        lambda payload: delegation_selector.select_child_role(payload.request),
        enhanced=False,
    )
    registrar.register(
        "workflow_select_executor",
        ExecutorSelectionPayload,
        lambda payload: delegation_selector.select_executor(payload.request),
        enhanced=False,
    )
    registrar.register(
        "workflow_select_child",
        ChildCandidateSelectionPayload,
        lambda payload: delegation_selector.select_child_candidate(payload.request),
        enhanced=False,
    )
    registrar.register(
        "workflow_assess_output_tokens",
        OutputTokenRoutingPayload,
        lambda payload: delegation_selector.assess_output_tokens(payload.request),
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

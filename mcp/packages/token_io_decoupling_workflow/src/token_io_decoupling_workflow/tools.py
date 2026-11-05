"""Registration for public workflow information and workflow evaluation tools."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from token_io_decoupling_core.binding import BindingProvider
from token_io_decoupling_core.rules import DEFAULT_CONTEXT_TEXT_BUDGET, RuleLoader
from token_io_decoupling_core.state_models import CheckpointNode
from token_io_decoupling_state.service import StateService
from token_io_decoupling_transport.payloads import _RULE_CONTEXT
from token_io_decoupling_transport.registration import ToolRegistrar

from token_io_decoupling_workflow.capabilities import capability_report
from token_io_decoupling_workflow.child_effort import (
    ChildEffortPayload,
    ChildEffortSelector,
)
from token_io_decoupling_workflow.compliance_preflight import (
    CompliancePreflightService,
    validate_decoupling_compliance,
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
from token_io_decoupling_workflow.payloads import (
    _COMPLIANCE_PREFLIGHT,
    _CONTROL_EVALUATE,
    _EVALUATE,
)
from token_io_decoupling_workflow.serena_memory import SerenaMemoryReadService
from token_io_decoupling_workflow.serena_memory_tools import register_serena_memory_tools
from token_io_decoupling_workflow.task_plan_core import TaskPlanService
from token_io_decoupling_workflow.task_plan_payloads import (
    TaskPlanArchivePayload,
    TaskPlanCompletePayload,
    TaskPlanUpdatePayload,
)
from token_io_decoupling_workflow.workflow_routing import (
    WorkflowRouter,
    WorkflowRoutingPayload,
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
    compliance_service: CompliancePreflightService | None,
    rules: RuleLoader,
    advisor: DecisionsAdvisor,
    decisions_config: DecisionsRuntimeConfig | None,
    provider: BindingProvider,
    embedded: bool,
    require_codex_context: bool,
    binding_details: Callable[[BindingProvider], dict[str, str]],
    output_materialization_details: dict[str, str] | None = None,
    serena_memory_service: SerenaMemoryReadService | None = None,
) -> None:
    memory_reads = serena_memory_service or SerenaMemoryReadService()
    register_serena_memory_tools(registrar, memory_reads)
    effort_selector = ChildEffortSelector()
    context_generator = DecisionContextGenerator(rules=rules)
    delegation_selector = DelegationDecisionSelector(rules)
    workflow_router = WorkflowRouter(rules, decisions_config)

    def get_rule_context(payload: Any) -> Any:
        if payload.context_version is None:
            return rules.load_context(payload.node_id.value, language=payload.language)
        return rules.load_context_bundle(
            payload.node_id.value,
            language=payload.language,
            fragment_ids=payload.fragment_ids,
            max_chars=payload.max_chars or DEFAULT_CONTEXT_TEXT_BUDGET,
        )

    registrar.register_no_args(
        "workflow_capabilities",
        lambda: capability_report(
            provider,
            embedded=embedded,
            require_codex_context=require_codex_context,
            api_decisions_enabled=bool(decisions_config and decisions_config.enabled),
            diagnose_binding=binding_details,
            task_plan_service=task_plan_service,
            serena_memory_service=memory_reads,
            compliance_service=compliance_service,
            output_materialization=output_materialization_details,
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
        get_rule_context,
        enhanced=False,
    )
    registrar.register(
        "validate_decoupling_compliance",
        _COMPLIANCE_PREFLIGHT,
        lambda payload: validate_decoupling_compliance(compliance_service, payload.request),
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
        "decide_decoupling_workflow",
        WorkflowRoutingPayload,
        lambda payload: workflow_router.decide(payload.request),
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

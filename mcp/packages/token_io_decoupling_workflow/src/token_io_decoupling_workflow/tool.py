"""Canonical workflow tool definitions using the shared registration template."""

from __future__ import annotations

from typing import Any

from token_io_decoupling_core.workflow_models import CheckpointNode
from token_io_decoupling_transport.tool import ToolDefinition, ToolRegistrar
from token_io_decoupling_workflow.checkpoint_evaluation import evaluate_checkpoint
from token_io_decoupling_workflow.child_effort import (
    ChildEffortPayload,
    ChildEffortSelector,
)
from token_io_decoupling_workflow.decision_context import (
    DecisionContextGenerator,
    DecisionContextPayload,
)
from token_io_decoupling_workflow.decisions import DecisionsAdvisor
from token_io_decoupling_workflow.delegation_decisions import (
    ChildCandidateSelectionPayload,
    ChildRoleSelectionPayload,
    DelegationDecisionSelector,
    ExecutorSelectionPayload,
    OutputTokenRoutingPayload,
)
from token_io_decoupling_workflow.events.advice import EventAdvisor
from token_io_decoupling_workflow.events.checks import WorkflowEventChecker
from token_io_decoupling_workflow.events.models import EventCheckPayload
from token_io_decoupling_workflow.payloads import (
    _CONTROL_EVALUATE,
    _EVALUATE,
    _RULE_CONTEXT,
)
from token_io_decoupling_workflow.rules import DEFAULT_CONTEXT_TEXT_BUDGET, RuleLoader


def register_tools(
    registrar: ToolRegistrar,
    *,
    rules: RuleLoader,
    advisor: DecisionsAdvisor,
    event_advisor: EventAdvisor,
    capability_callback,
) -> None:
    """集中声明 11 个操作及其输入模型，注册关系不模拟 DAG 或执行顺序。"""
    effort_selector = ChildEffortSelector()
    context_generator = DecisionContextGenerator(rules=rules)
    delegation_selector = DelegationDecisionSelector(rules)
    event_checker = WorkflowEventChecker(rules, event_advisor)

    def get_rule_context(payload: Any) -> Any:
        """返回当前请求所选的完整编译内容，不按历史调用补齐规则。"""
        return rules.load_context_bundle(
            payload.node_id.value,
            language=payload.language,
            fragment_ids=payload.fragment_ids,
            max_chars=payload.max_chars or DEFAULT_CONTEXT_TEXT_BUDGET,
        )

    def evaluate_node(payload: Any) -> Any:
        """先保留独立结构结论，再附加可选建议；建议失败不授权执行。"""
        if payload.submission.node_id is not payload.node_id:
            raise ValueError("submission node must match the evaluated checkpoint")
        result = evaluate_checkpoint(
            payload.submission,
            rules=rules,
            language=payload.language,
            expected_rule_hash=payload.expected_rule_hash,
        )
        output = result.model_dump(mode="json")
        if payload.semantic_input is not None:
            if payload.semantic_input.node_id is not payload.node_id:
                raise ValueError("semantic input node must match the evaluated checkpoint")
            output["advice"] = advisor.advise(
                payload.semantic_input,
                current_facts=payload.current_facts,
                checkpoint_source_input_hash=result.source_input_hash,
                language=payload.language,
                expected_rule_hash=result.rule_hash,
            ).model_dump(mode="json")
        return output

    def evaluate_control(payload: Any) -> Any:
        """对固定 Control 节点复用同一结构与建议边界，不推进任务状态。"""
        if payload.submission.node_id is not CheckpointNode.CONTROL:
            raise ValueError("control evaluation requires Control evidence")
        result = evaluate_checkpoint(
            payload.submission,
            rules=rules,
            language=payload.language,
            expected_rule_hash=payload.expected_rule_hash,
        )
        output = result.model_dump(mode="json")
        if payload.semantic_input is not None:
            if payload.semantic_input.node_id is not CheckpointNode.CONTROL:
                raise ValueError("control evaluation requires Control semantic input")
            output["advice"] = advisor.advise(
                payload.semantic_input,
                current_facts=payload.current_facts,
                checkpoint_source_input_hash=result.source_input_hash,
                language=payload.language,
                expected_rule_hash=result.rule_hash,
            ).model_dump(mode="json")
        return output

    registrar.register_all(
        (
            ToolDefinition(
                name="workflow_capabilities",
                callback=capability_callback,
                bounded_errors=True,
            ),
            ToolDefinition(
                name="rules_get_context",
                callback=get_rule_context,
                payload_type=_RULE_CONTEXT,
            ),
            ToolDefinition(
                name="workflow_select_child_effort",
                callback=lambda payload: effort_selector.select(payload.request),
                payload_type=ChildEffortPayload,
            ),
            ToolDefinition(
                name="workflow_generate_decision_context",
                callback=lambda payload: context_generator.generate(payload.request),
                payload_type=DecisionContextPayload,
            ),
            ToolDefinition(
                name="workflow_check_event",
                callback=lambda payload: event_checker.check(payload.request),
                payload_type=EventCheckPayload,
            ),
            ToolDefinition(
                name="workflow_select_child_role",
                callback=lambda payload: delegation_selector.select_child_role(payload.request),
                payload_type=ChildRoleSelectionPayload,
            ),
            ToolDefinition(
                name="workflow_select_executor",
                callback=lambda payload: delegation_selector.select_executor(payload.request),
                payload_type=ExecutorSelectionPayload,
            ),
            ToolDefinition(
                name="workflow_select_child",
                callback=lambda payload: delegation_selector.select_child_candidate(
                    payload.request
                ),
                payload_type=ChildCandidateSelectionPayload,
            ),
            ToolDefinition(
                name="workflow_assess_output_tokens",
                callback=lambda payload: delegation_selector.assess_output_tokens(payload.request),
                payload_type=OutputTokenRoutingPayload,
            ),
            ToolDefinition(
                name="workflow_evaluate",
                callback=evaluate_node,
                payload_type=_EVALUATE,
            ),
            ToolDefinition(
                name="evaluate_control_checkpoint",
                callback=evaluate_control,
                payload_type=_CONTROL_EVALUATE,
            ),
        )
    )

"""模块拆分后，旧公共导入必须继续指向同一组类型和入口。"""

from importlib import import_module

import pytest


@pytest.mark.parametrize(
    ("legacy", "implementation", "symbol"),
    [
        (
            "token_io_decoupling_tools.task_plan_core",
            "token_io_decoupling_tools.task_plans.service",
            "TaskPlanService",
        ),
        (
            "token_io_decoupling_tools.task_plan_core",
            "token_io_decoupling_tools.task_plans.store",
            "SerenaMemoryStore",
        ),
        (
            "token_io_decoupling_tools.task_plan_core",
            "token_io_decoupling_tools.task_plans.types",
            "TaskPlanFailure",
        ),
        (
            "token_io_decoupling_tools.output_materialization",
            "token_io_decoupling_tools.materialization.service",
            "OutputMaterializationService",
        ),
        (
            "token_io_decoupling_tools.output_materialization",
            "token_io_decoupling_tools.materialization.models",
            "MaterializationAssignment",
        ),
        (
            "token_io_decoupling_tools.output_materialization",
            "token_io_decoupling_tools.materialization.models",
            "OutputMaterializerConfig",
        ),
        (
            "token_io_decoupling_tools.materialization_storage",
            "token_io_decoupling_tools.artifact_storage.service",
            "MaterializationStorage",
        ),
        (
            "token_io_decoupling_tools.compliance_preflight",
            "token_io_decoupling_tools.compliance.service",
            "CompliancePreflightService",
        ),
        (
            "token_io_decoupling_tools.tool",
            "token_io_decoupling_tools.registration.local",
            "register_tools",
        ),
        (
            "token_io_decoupling_workflow.delegation_decisions",
            "token_io_decoupling_workflow.delegation.selector",
            "DelegationDecisionSelector",
        ),
        (
            "token_io_decoupling_workflow.delegation_decisions",
            "token_io_decoupling_workflow.delegation.models",
            "DelegationDecisionResult",
        ),
        (
            "token_io_decoupling_workflow.child_effort",
            "token_io_decoupling_workflow.effort.selector",
            "ChildEffortSelector",
        ),
        (
            "token_io_decoupling_workflow.decisions",
            "token_io_decoupling_workflow.advisory.advisor",
            "DecisionsAdvisor",
        ),
        (
            "token_io_decoupling_workflow.decision_context",
            "token_io_decoupling_workflow.context_generation.generator",
            "DecisionContextGenerator",
        ),
        (
            "token_io_decoupling_workflow.rules",
            "token_io_decoupling_workflow.compiled_rules.loader",
            "RuleLoader",
        ),
        (
            "token_io_decoupling_workflow.rules",
            "token_io_decoupling_workflow.compiled_rules.contracts",
            "RuleLoadError",
        ),
        (
            "token_io_decoupling_core.workflow_models",
            "token_io_decoupling_core.workflow_contracts.vocabulary",
            "BindingIdentity",
        ),
        (
            "token_io_decoupling_core.workflow_models",
            "token_io_decoupling_core.workflow_contracts.evidence",
            "EvidenceSubmission",
        ),
    ],
    ids=[
        "plan-service",
        "plan-store",
        "plan-error",
        "materialization-service",
        "assignment",
        "materializer-config",
        "artifact-storage",
        "compliance",
        "registration",
        "delegation",
        "delegation-result",
        "effort",
        "advisory",
        "context-generation",
        "rule-loader",
        "rule-error",
        "binding-identity",
        "checkpoint-evidence",
    ],
)
def test_public_imports_preserve_object_identity(
    legacy: str, implementation: str, symbol: str
) -> None:
    legacy_module = import_module(legacy)
    implementation_module = import_module(implementation)

    assert getattr(legacy_module, symbol) is getattr(implementation_module, symbol)

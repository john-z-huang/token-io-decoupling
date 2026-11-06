"""Canonical Layer-01 paths for packaged standalone policy owners."""

OWNER_PATHS: dict[str, str] = {
    "child-role-selection": (
        "instruction-compiler/sources/skill/references/coding/layer-01-fundamental-concepts/delegation/child-role-selection.md"
    ),
    "task-assignment": (
        "instruction-compiler/sources/skill/references/coding/layer-01-fundamental-concepts/execution-planning/task-assignment.md"
    ),
    "output-token-routing": (
        "instruction-compiler/sources/skill/references/coding/layer-01-fundamental-concepts/execution-planning/output-token-routing.md"
    ),
    "session-role-ownership": (
        "instruction-compiler/sources/skill/references/coding/layer-01-fundamental-concepts/session-runtime/session-role-ownership.md"
    ),
    "decision-context-generation": (
        "instruction-compiler/sources/skill/references/coding/layer-01-fundamental-concepts/execution-planning/decision-context-generation.md"
    ),
    "workflow-routing-advice": (
        "instruction-compiler/sources/skill/references/coding/layer-01-fundamental-concepts/execution-planning/workflow-routing-advice.md"
    ),
    "candidate-compliance": (
        "instruction-compiler/sources/skill/references/coding/layer-01-fundamental-concepts/execution-planning/candidate-compliance.md"
    ),
    "output-materialization": (
        "instruction-compiler/sources/skill/references/coding/layer-01-fundamental-concepts/execution-planning/output-materialization.md"
    ),
}

DELEGATION_POLICY_OWNERS: tuple[str, ...] = (
    "child-role-selection",
    "task-assignment",
    "output-token-routing",
    "session-role-ownership",
    "decision-context-generation",
)

OPTIONAL_FRAGMENT_OWNER_BINDINGS: dict[str, tuple[str, str]] = {
    "decision.workflow_routing_advice": ("decision", "workflow-routing-advice"),
    "implementation.candidate_compliance": ("implementation", "candidate-compliance"),
    "implementation.output_materialization": ("implementation", "output-materialization"),
}

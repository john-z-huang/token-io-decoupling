"""检查点与概念层、Layer-03 owner 的对应关系。"""

from __future__ import annotations

LAYER3_OWNERS = (
    "route-entry",
    "workflow-navigation-selection",
    "session-audit-resolution",
    "session-state-resolution",
    "context-source-selection",
    "decision-context-selection",
    "planning-output-selection",
    "bootstrap-selection",
    "executor-selection",
    "output-route-selection",
    "role-reservation",
    "advisory-selection",
    "repair-disposition",
    "documentation-impact",
    "module-entry-resolution",
)


MODULE_L3_OWNERS = {
    "entry-readiness": {"module-entry-resolution", "workflow-navigation-selection"},
    "session-readiness": {
        "module-entry-resolution",
        "session-state-resolution",
        "session-audit-resolution",
    },
    "work-definition": {
        "module-entry-resolution",
        "context-source-selection",
        "decision-context-selection",
        "planning-output-selection",
        "advisory-selection",
    },
    "single-execution": {
        "module-entry-resolution",
        "executor-selection",
        "output-route-selection",
        "advisory-selection",
    },
    "delegated-execution": {
        "module-entry-resolution",
        "bootstrap-selection",
        "executor-selection",
        "output-route-selection",
        "role-reservation",
        "advisory-selection",
    },
    "verification-repair": {"module-entry-resolution", "repair-disposition", "advisory-selection"},
    "documentation": {"module-entry-resolution", "documentation-impact"},
    "delivery-acceptance": {"module-entry-resolution"},
}


L3_REQUIRED_LAYER12_LINK = {
    "route-entry": "../layer-02-workflow-concepts/entry-and-context/contract.md",
    "workflow-navigation-selection": (
        "../layer-01-fundamental-concepts/workflow-navigation/navigation-availability.md"
    ),
    "session-audit-resolution": (
        "../layer-01-fundamental-concepts/session-runtime/session-audit-visibility.md"
    ),
    "session-state-resolution": "../layer-01-fundamental-concepts/session-runtime/session-model.md",
    "context-source-selection": "../layer-02-workflow-concepts/entry-and-context/context.md",
    "decision-context-selection": (
        "../layer-01-fundamental-concepts/execution-planning/decision-context-generation.md"
    ),
    "planning-output-selection": (
        "../layer-01-fundamental-concepts/execution-planning/execution-planning.md"
    ),
    "bootstrap-selection": (
        "../layer-01-fundamental-concepts/delegation/delegation-child-role-allocation.md"
    ),
    "executor-selection": "../layer-01-fundamental-concepts/execution-planning/task-assignment.md",
    "output-route-selection": (
        "../layer-01-fundamental-concepts/execution-planning/output-token-routing.md"
    ),
    "role-reservation": "../layer-01-fundamental-concepts/delegation/child-role-selection.md",
    "advisory-selection": (
        "../layer-01-fundamental-concepts/execution-planning/decisions-advisory.md"
    ),
    "repair-disposition": "../layer-02-workflow-concepts/verification-and-repair/repair.md",
    "documentation-impact": "../layer-02-workflow-concepts/completion-and-effects/documentation.md",
    "module-entry-resolution": (
        "../layer-01-fundamental-concepts/execution-planning/workflow-module-contract.md"
    ),
}


MODULE_CHECKPOINT_LAYER12_TARGETS = {
    "entry-readiness": {
        "ER01": "../../layer-02-workflow-concepts/entry-and-context/contract.md",
        "ER03": "../../layer-02-workflow-concepts/entry-and-context/mode.md",
    },
    "session-readiness": {
        "SR04": "../../layer-01-fundamental-concepts/delegation/delegation-mode-count-gate.md"
    },
    "work-definition": {
        "WD02": "../../layer-01-fundamental-concepts/execution-planning/workflow-routing-advice.md",
    },
    "single-execution": {
        "SE02": "../../layer-01-fundamental-concepts/execution-control/execution-control.md",
        "SE03": (
            "../../layer-02-workflow-concepts/decision-and-execution/implementation.md",
            "../../layer-01-fundamental-concepts/execution-planning/output-materialization.md",
            "../../layer-01-fundamental-concepts/execution-planning/candidate-compliance.md",
        ),
        "SE04": "../../layer-01-fundamental-concepts/execution-control/execution-stage-feedback.md",
    },
    "delegated-execution": {
        "DE04": "../../layer-01-fundamental-concepts/execution-control/execution-control.md",
        "DE05": "../../layer-01-fundamental-concepts/delegation/delegation-child-creation.md",
        "DE06": "../../layer-01-fundamental-concepts/delegation/delegation-child-dispatch.md",
        "DE07": (
            "../../layer-02-workflow-concepts/decision-and-execution/implementation.md",
            "../../layer-01-fundamental-concepts/execution-planning/output-materialization.md",
            "../../layer-01-fundamental-concepts/execution-planning/candidate-compliance.md",
        ),
    },
    "verification-repair": {
        "VR01": "../../layer-01-fundamental-concepts/execution-planning/output-materialization.md",
    },
    "documentation": {
        "DOC02": "../../layer-01-fundamental-concepts/execution-planning/candidate-compliance.md",
    },
    "delivery-acceptance": {
        "DA02": "../../layer-02-workflow-concepts/completion-and-effects/git.md",
        "DA03": "../../layer-02-workflow-concepts/completion-and-effects/acceptance.md",
    },
}


MODULE_CHECKPOINT_L3_OWNERS = {
    "entry-readiness": {
        "ER00": {"module-entry-resolution", "route-entry"},
        "ER02": {"workflow-navigation-selection"},
    },
    "session-readiness": {
        "SR00": {"module-entry-resolution"},
        "SR02": {"session-state-resolution"},
        "SR03": {"session-audit-resolution"},
    },
    "work-definition": {
        "WD00": {"module-entry-resolution"},
        "WD01": {"context-source-selection", "decision-context-selection"},
        "WD02": {"advisory-selection"},
        "WD03": {"planning-output-selection"},
    },
    "single-execution": {
        "SE00": {"module-entry-resolution"},
        "SE01": {"executor-selection", "output-route-selection"},
        "SE05": {"advisory-selection"},
    },
    "delegated-execution": {
        "DE00": {"module-entry-resolution"},
        "DE01": {"bootstrap-selection"},
        "DE02": {"executor-selection", "output-route-selection"},
        "DE03": {"role-reservation"},
        "DE08": {"advisory-selection"},
    },
    "verification-repair": {
        "VR00": {"module-entry-resolution"},
        "VR04": {"advisory-selection"},
        "VR05": {"repair-disposition"},
    },
    "documentation": {"DOC00": {"module-entry-resolution"}, "DOC04": {"documentation-impact"}},
    "delivery-acceptance": {"DA00": {"module-entry-resolution"}},
}

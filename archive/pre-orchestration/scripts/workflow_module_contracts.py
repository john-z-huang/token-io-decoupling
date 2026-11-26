"""Shared immutable contract for Coding's Layer-04 route/module structure."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = Path("workflows")
WORKFLOW_SELECTOR = WORKFLOW_PATH / "coding.yaml"
ROUTES_DIR = Path("skill") / WORKFLOW_PATH
HOOKS_DIR = Path("skill/hooks")
MODULE_HOOKS = {
    "entry-readiness": "entry", "session-readiness": "session", "work-definition": "planning",
    "single-execution": "execution", "delegated-execution": "delegation",
    "verification-repair": "verification", "documentation": "documentation", "delivery-acceptance": "delivery",
}
MODULES = (
    "entry-readiness", "session-readiness", "work-definition", "single-execution",
    "delegated-execution", "verification-repair", "documentation", "delivery-acceptance",
)
ROUTE_MODULES = {
    "coding-single-agent": (
        "entry-readiness", "session-readiness", "work-definition", "single-execution",
        "verification-repair", "documentation", "delivery-acceptance",
    ),
    "coding-multi-agent": (
        "entry-readiness", "session-readiness", "work-definition", "delegated-execution",
        "verification-repair", "documentation", "delivery-acceptance",
    ),
}
MODULE_PREFIXES = {
    "entry-readiness": "ER", "session-readiness": "SR", "work-definition": "WD",
    "single-execution": "SE", "delegated-execution": "DE", "verification-repair": "VR",
    "documentation": "DOC", "delivery-acceptance": "DA",
}
# 固定检查点 ID 和顺序；流程图仅供导航，不以图的文案指纹锁定合同。
MODULE_CHECKPOINTS = {
    "entry-readiness": ("ER00", "ER01", "ER02", "ER03"),
    "session-readiness": ("SR00", "SR01", "SR02", "SR03", "SR04"),
    "work-definition": ("WD00", "WD01", "WD02", "WD03"),
    "single-execution": ("SE00", "SE01", "SE02", "SE03", "SE04", "SE05", "SE06"),
    "delegated-execution": ("DE00", "DE01", "DE02", "DE03", "DE04", "DE05", "DE06", "DE07", "DE08", "DE09"),
    "verification-repair": ("VR00", "VR01", "VR02", "VR03", "VR04", "VR05", "VR06"),
    "documentation": ("DOC00", "DOC01", "DOC02", "DOC03", "DOC04", "DOC05", "DOC06"),
    "delivery-acceptance": ("DA00", "DA01", "DA02", "DA03", "DA04", "DA05"),
}
TOP_PREFIXES = {"coding-single-agent": "SM", "coding-multi-agent": "MM"}
LAYER3_OWNERS = (
    "route-entry", "workflow-navigation-selection", "session-audit-resolution",
    "session-state-resolution", "context-source-selection", "decision-context-selection",
    "planning-output-selection", "bootstrap-selection", "executor-selection",
    "output-route-selection", "role-reservation", "advisory-selection",
    "repair-disposition", "documentation-impact", "module-entry-resolution",
)
MODULE_L3_OWNERS = {
    "entry-readiness": {"module-entry-resolution", "workflow-navigation-selection"},
    "session-readiness": {"module-entry-resolution", "session-state-resolution", "session-audit-resolution"},
    "work-definition": {"module-entry-resolution", "context-source-selection", "decision-context-selection", "planning-output-selection", "advisory-selection"},
    "single-execution": {"module-entry-resolution", "executor-selection", "output-route-selection", "advisory-selection"},
    "delegated-execution": {"module-entry-resolution", "bootstrap-selection", "executor-selection", "output-route-selection", "role-reservation", "advisory-selection"},
    "verification-repair": {"module-entry-resolution", "repair-disposition", "advisory-selection"},
    "documentation": {"module-entry-resolution", "documentation-impact"},
    "delivery-acceptance": {"module-entry-resolution"},
}
L3_REQUIRED_LAYER12_LINK = {
    "route-entry": "../layer-02-workflow-concepts/entry-and-context/contract.md",
    "workflow-navigation-selection": "../layer-01-fundamental-concepts/workflow-navigation/navigation-availability.md",
    "session-audit-resolution": "../layer-01-fundamental-concepts/session-runtime/session-audit-visibility.md",
    "session-state-resolution": "../layer-01-fundamental-concepts/session-runtime/session-model.md",
    "context-source-selection": "../layer-02-workflow-concepts/entry-and-context/context.md",
    "decision-context-selection": "../layer-01-fundamental-concepts/execution-planning/decision-context-generation.md",
    "planning-output-selection": "../layer-01-fundamental-concepts/execution-planning/execution-planning.md",
    "bootstrap-selection": "../layer-01-fundamental-concepts/delegation/delegation-child-role-allocation.md",
    "executor-selection": "../layer-01-fundamental-concepts/execution-planning/task-assignment.md",
    "output-route-selection": "../layer-01-fundamental-concepts/execution-planning/output-token-routing.md",
    "role-reservation": "../layer-01-fundamental-concepts/delegation/child-role-selection.md",
    "advisory-selection": "../layer-01-fundamental-concepts/execution-planning/decisions-advisory.md",
    "repair-disposition": "../layer-02-workflow-concepts/verification-and-repair/repair.md",
    "documentation-impact": "../layer-02-workflow-concepts/completion-and-effects/documentation.md",
    "module-entry-resolution": "../layer-01-fundamental-concepts/execution-planning/workflow-module-contract.md",
}
MODULE_CHECKPOINT_LAYER12_TARGETS = {
    "entry-readiness": {"ER01": "../references/coding/layer-02-workflow-concepts/entry-and-context/contract.md",
                        "ER03": "../references/coding/layer-02-workflow-concepts/entry-and-context/mode.md"},
    "session-readiness": {"SR04": "../references/coding/layer-01-fundamental-concepts/delegation/delegation-mode-count-gate.md"},
    "work-definition": {
        "WD02": "../references/coding/layer-01-fundamental-concepts/execution-planning/workflow-routing-advice.md",
    },
    "single-execution": {"SE02": "../references/coding/layer-01-fundamental-concepts/execution-control/execution-control.md",
                         "SE03": (
                             "../references/coding/layer-02-workflow-concepts/decision-and-execution/implementation.md",
                             "../references/coding/layer-01-fundamental-concepts/execution-planning/output-materialization.md",
                             "../references/coding/layer-01-fundamental-concepts/execution-planning/candidate-compliance.md",
                         ),
                         "SE04": "../references/coding/layer-01-fundamental-concepts/execution-control/execution-stage-feedback.md"},
    "delegated-execution": {"DE04": "../references/coding/layer-01-fundamental-concepts/execution-control/execution-control.md",
                            "DE05": "../references/coding/layer-01-fundamental-concepts/delegation/delegation-child-creation.md",
                            "DE06": "../references/coding/layer-01-fundamental-concepts/delegation/delegation-child-dispatch.md",
                            "DE07": (
                                "../references/coding/layer-02-workflow-concepts/decision-and-execution/implementation.md",
                                "../references/coding/layer-01-fundamental-concepts/execution-planning/output-materialization.md",
                                "../references/coding/layer-01-fundamental-concepts/execution-planning/candidate-compliance.md",
                            )},
    "verification-repair": {
        "VR01": "../references/coding/layer-01-fundamental-concepts/execution-planning/output-materialization.md",
    },
    "documentation": {
        "DOC02": "../references/coding/layer-01-fundamental-concepts/execution-planning/candidate-compliance.md",
    },
    "delivery-acceptance": {"DA02": "../references/coding/layer-02-workflow-concepts/completion-and-effects/git.md",
                            "DA03": "../references/coding/layer-02-workflow-concepts/completion-and-effects/acceptance.md"},
}
MODULE_CHECKPOINT_L3_OWNERS = {
    "entry-readiness": {"ER00": {"module-entry-resolution", "route-entry"}, "ER02": {"workflow-navigation-selection"}},
    "session-readiness": {"SR00": {"module-entry-resolution"}, "SR02": {"session-state-resolution"}, "SR03": {"session-audit-resolution"}},
    "work-definition": {"WD00": {"module-entry-resolution"}, "WD01": {"context-source-selection", "decision-context-selection"}, "WD02": {"advisory-selection"}, "WD03": {"planning-output-selection"}},
    "single-execution": {"SE00": {"module-entry-resolution"}, "SE01": {"executor-selection", "output-route-selection"}, "SE05": {"advisory-selection"}},
    "delegated-execution": {"DE00": {"module-entry-resolution"}, "DE01": {"bootstrap-selection"}, "DE02": {"executor-selection", "output-route-selection"}, "DE03": {"role-reservation"}, "DE08": {"advisory-selection"}},
    "verification-repair": {"VR00": {"module-entry-resolution"}, "VR04": {"advisory-selection"}, "VR05": {"repair-disposition"}},
    "documentation": {"DOC00": {"module-entry-resolution"}, "DOC04": {"documentation-impact"}},
    "delivery-acceptance": {"DA00": {"module-entry-resolution"}},
}

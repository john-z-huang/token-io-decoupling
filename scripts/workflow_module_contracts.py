"""Shared immutable contract for Coding's Layer-04 route/module structure."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROUTES_DIR = Path("references/coding/layer-04-workflows")
MODULES_DIR = ROUTES_DIR / "modules"
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
# These sequences and graph fingerprints are fixed migration contracts.  The
# digests cover every node label and every directed, labeled edge in each
# owner map; they are intentionally independent of the diagrams being checked.
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
MODULE_REQUIRED_EDGES = {
    "entry-readiness": (("D_ENTRY", "ER01"), ("D_ENTRY", "ER_NEEDS"), ("D_ENTRY", "ER_BLOCK"), ("ER03", "ER_DONE")),
    "session-readiness": (("SR02", "SR03"), ("SR02", "SR01"), ("SR03", "D_MODE"), ("D_MODE", "SR_DONE")),
    "work-definition": (("WD01", "WD02"), ("WD02", "WD03"), ("WD03", "D_PLAN"), ("WD_PLAN", "WD_DONE")),
    "single-execution": (("D_GATE", "SE03"), ("D_GATE", "SE05"), ("D_RECOVERY", "SE_NEEDS_EOD"), ("SE_NEEDS_EOD", "SE05"), ("D_RECOVERY", "SE_NEEDS_AMEND"), ("SE_NEEDS_AMEND", "SE05"), ("D_RECOVERY", "D_CONTROL"), ("D_CONTROL", "SE_NEEDS_NEXT"), ("D_CONTINUE_COVERS", "D_REROUTE"), ("D_CONTINUE_COVERS", "SE05"), ("D_REROUTE", "SE02")),
    "delegated-execution": (("DE01", "DE02"), ("DE02", "D_EXEC"), ("D_EXEC", "DE03"), ("D_ROLE", "DE04"), ("D_GATE", "DE05"), ("DE05", "D_CHILD"), ("D_CHILD", "DE06"), ("DE06", "DE07"), ("DE06", "DE_NEEDS_PENDING"), ("DE_NEEDS_PENDING", "DE07"), ("D_RECOVERY", "DE_NEEDS_AMEND"), ("DE_NEEDS_AMEND", "DE08"), ("D_RECOVERY", "DE04"), ("D_RECOVERY", "D_CONTROL"), ("D_CONTINUE_COVERS", "D_REROUTE"), ("D_REROUTE", "DE01")),
    "verification-repair": (("D_RESULT", "VR05"), ("VR05", "D_REPAIR"), ("D_REPAIR", "VR_SCOPE"), ("VR_SCOPE", "VR_EXEC"), ("VR_EXEC", "VR_HANDOFF"), ("VR_HANDOFF", "VR01"), ("D_RESULT", "VR06")),
    "documentation": (("D_MEMORY", "DOC03"), ("DOC03", "DOC04"), ("DOC04", "DOC05"), ("DOC05", "DOC06")),
    "delivery-acceptance": (("D_VERIFIED", "D_GIT"), ("D_GIT", "DA02"), ("DA02", "DA03"), ("DA03", "D_PLAN"), ("D_PLAN", "DA04"), ("DA04", "DA05")),
}
MODULE_REQUIRED_LABEL_FRAGMENTS = {
    "single-execution": {
        "en": {"D_CONTINUE_COVERS": "Does prior Continue still cover"},
        "zh": {"D_CONTINUE_COVERS": "先前 Continue 是否仍覆盖"},
    },
    "delegated-execution": {
        "en": {"D_CONTINUE_COVERS": "Does prior Continue still cover"},
        "zh": {"D_CONTINUE_COVERS": "先前 Continue 是否仍覆盖"},
    },
}
MODULE_REQUIRED_EDGE_LABELS = {
    "single-execution": {
        "en": {("SE_NEEDS_AMEND", "SE05"): "Contract/Decision and needed Context current", ("D_CONTINUE_COVERS", "D_REROUTE"): "prior Continue covers Slice; boundary and epochs current"},
        "zh": {("SE_NEEDS_AMEND", "SE05"): "Contract/Decision及所需Context已当前", ("D_CONTINUE_COVERS", "D_REROUTE"): "Continue仍覆盖该Slice；边界与epoch当前"},
    },
    "delegated-execution": {
        "en": {("DE01", "DE02"): "actual task explicitly authorized", ("D_RESULT", "DE_NEEDS_PENDING"): "child result pending", ("DE_NEEDS_AMEND", "DE08"): "Contract/Decision and needed Context current", ("D_CONTINUE_COVERS", "D_REROUTE"): "prior Continue covers Slice; boundary and epochs current"},
        "zh": {("DE01", "DE02"): "实际任务已明确授权", ("D_RESULT", "DE_NEEDS_PENDING"): "子代理结果待处理", ("DE_NEEDS_AMEND", "DE08"): "Contract/Decision及所需Context已当前", ("D_CONTINUE_COVERS", "D_REROUTE"): "Continue仍覆盖Slice且边界/epoch当前"},
    },
    "verification-repair": {
        "en": {("VR_SCOPE", "VR_EXEC"): "narrow repair authorized", ("VR_HANDOFF", "VR01"): "new fingerprint/epochs returned", ("D_RESULT", "VR06"): "all required items current and passed"},
        "zh": {("VR_SCOPE", "VR_EXEC"): "窄范围修复已授权", ("VR_HANDOFF", "VR01"): "新指纹/epoch 已返回", ("D_RESULT", "VR06"): "所有必需项目当前有效且通过"},
    },
    "documentation": {
        "en": {("DOC03", "DOC04"): "write succeeded and readback confirmed", ("DOC04", "DOC05"): "only documentation dimension changed", ("DOC05", "DOC06"): "applicable checks pass"},
        "zh": {("DOC03", "DOC04"): "写入成功且读回确认", ("DOC04", "DOC05"): "仅文档维度改变", ("DOC05", "DOC06"): "适用检查通过"},
    },
    "delivery-acceptance": {
        "en": {("DA03", "D_PLAN"): "all criteria mapped", ("D_PLAN", "DA04"): "matching active plan exists", ("DA04", "DA05"): "archived plan read back"},
        "zh": {("DA03", "D_PLAN"): "所有 criteria 已映射", ("D_PLAN", "DA04"): "存在匹配 active plan", ("DA04", "DA05"): "计划已归档且读回"},
    },
}
MODULE_GRAPH_SHA256 = {
    "en": {
        "delegated-execution": "0d06299dd912dc34ed11fcaf59f40167144f4e92a64252a48963345531b6e432",
        "delivery-acceptance": "7524c6a1f2d2611188a42fc206cb68d45dfec3fe753003765e4eadbc205e8ce3",
        "documentation": "9d5a8690dd8a436f651f08c54e4098385300fdef3ff91dd9894ffc001fce3480",
        "entry-readiness": "269dc96c4965b035ce5ad6d6ea1fb04dd0cafbe64a8ec84f58e36f9a4745c2f8",
        "session-readiness": "16f94918cc826fdf291d9102adc049acf5fca12d6778425d517845f257406252",
        "single-execution": "19238454672f799be2dd120d7230294eaf73eb00308e11d8ae2d38999279d960",
        "verification-repair": "9def420e7ebfb8ba6836c875960654b7038653bd36cab4d47121fb6c340decbb",
        "work-definition": "abec8a47930c29f495b092e4d5a40ceb76a764d9f4c7fcd4807e86b2ed102c12",
    },
    "zh": {
        "delegated-execution": "9c1445213f9867fd0f2298a3a6a0f8c18738bae2fe6f9d937bfec9f4130acffb",
        "delivery-acceptance": "65f47da7b0e6d9a820ec1b30dc5323d70cb9f3664363b3a498dbb803390d723a",
        "documentation": "459c91325cc289b825f56c2d8ade809a1825658f9d65d2215507f8f1f702e017",
        "entry-readiness": "3c8a6bbf88b8d27126b04bde51fbe5c8b356e5cb4de13d2af0a145d642331b5e",
        "session-readiness": "a3756c195fef91d6e186c428fb1d030b0430d8dd0e677d10dd7da2af894245e1",
        "single-execution": "739edd16c7b04e85b934e794621d4b8f498563710b95c60fb930ca7f3c1f1396",
        "verification-repair": "c02c391de233167a29141f3bfcd425eb7aa0f1ece0197eb35532ae3230e7f787",
        "work-definition": "cbf59d6113953a9ebea2f4c561a842f35b026c6625be93c4c3d38024b959b6ef",
    },
}
MODULE_SEMANTIC_FRAGMENTS = {
    "single-execution": (
        "update the Contract and Decision under their owners, and update Context when needed",
        "obtain a new explicit `Continue`",
    ),
    "delegated-execution": (
        "separately authorize and assess the original task",
        "after the auxiliary task completes, return to DE01",
        "pending child result returns `needs_prerequisite` and resumes at DE07",
        "`write_content_memo: true` or `false`",
    ),
    "documentation": (
        "DOC03 -- write succeeded and readback confirmed --> DOC04",
        "DOC04 -- only documentation dimension changed",
    ),
    "delivery-acceptance": (
        "DA03 -- all criteria mapped; every applicable item passes on current epochs --> D_PLAN",
        "DA04 -- archive or readback failed --> DA_BLOCK",
    ),
}
MANIFEST_ROUTE_SHA256 = {
    "single-agent": "c6bf914782a2730a5c3c760eb4b35dd0de5f2c20ead1ab8b2177d0b4b4d6145a",
    "multi-agent": "8878c7587dce79500cf9dff08cc1da7459d41aa1be7321696481d06fbb6cb6b7",
}
MIXED_STEP_CONTRACTS = {
    ("single-agent", "S06"): {
        "semantic_substeps": ("Decision, Decision Brief and execution planning", "Planning output/Memory lifecycle and optional advice", "Executor/output disposition for implementation"),
        "target_sequence": (("work-definition", ("WD01", "WD02", "WD03")), ("single-execution", ("SE01",))),
        "branch_or_return": "Do not merge later S09 Control advice with S06 Decision advice",
    },
    ("multi-agent", "M07"): {
        "semantic_substeps": ("Decision, two-level plan, planning Memory and Decision advice", "Bootstrap proposal plus actual-task authorization", "Executor/output/role decision and Slice release"),
        "target_sequence": (("work-definition", ("WD01", "WD02", "WD03")), ("delegated-execution", ("DE01", "DE02", "DE03", "DE04"))),
        "branch_or_return": "This Decision/Bootstrap step is distinct from M16 Acceptance/archive",
    },
}
VERIFICATION_STEP_CONTRACTS = {
    ("single-agent", "S10"): {"checkpoints": ("VR01", "VR02", "VR03", "VR04", "VR06"), "return": "Current successful Verification returns through VR06 before returning the result; conditional advice and verifier visibility remain owner-gated."},
    ("multi-agent", "M12"): {"checkpoints": ("VR01", "VR02", "VR03", "VR04", "VR06"), "return": "Current successful Verification returns through VR06 before returning the result; conditional advice and verifier visibility remain owner-gated."},
}
TOP_PREFIXES = {"coding-single-agent": "SM", "coding-multi-agent": "MM"}
MIGRATION_MANIFEST = Path("docs/workflow-module-migration.json")
LAYER3_OWNERS = (
    "route-entry", "enhanced-path-selection", "session-audit-resolution",
    "session-state-resolution", "context-source-selection", "decision-context-selection",
    "planning-output-selection", "bootstrap-selection", "executor-selection",
    "output-route-selection", "role-reservation", "advisory-selection",
    "repair-disposition", "documentation-impact", "module-entry-resolution",
)
MODULE_L3_OWNERS = {
    "entry-readiness": {"module-entry-resolution", "enhanced-path-selection"},
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
    "enhanced-path-selection": "../layer-01-fundamental-concepts/enhanced-native-state/enhanced-workflow-availability.md",
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
    "entry-readiness": {"ER01": "../../layer-02-workflow-concepts/entry-and-context/contract.md",
                        "ER03": "../../layer-02-workflow-concepts/entry-and-context/mode.md"},
    "session-readiness": {"SR04": "../../layer-01-fundamental-concepts/delegation/delegation-mode-count-gate.md"},
    "single-execution": {"SE02": "../../layer-01-fundamental-concepts/execution-control/execution-control.md",
                         "SE03": "../../layer-02-workflow-concepts/decision-and-execution/implementation.md",
                         "SE04": "../../layer-01-fundamental-concepts/execution-control/execution-stage-feedback.md"},
    "delegated-execution": {"DE04": "../../layer-01-fundamental-concepts/execution-control/execution-control.md",
                            "DE05": "../../layer-01-fundamental-concepts/delegation/delegation-child-creation.md",
                            "DE06": "../../layer-01-fundamental-concepts/delegation/delegation-child-dispatch.md",
                            "DE07": "../../layer-02-workflow-concepts/decision-and-execution/implementation.md"},
    "delivery-acceptance": {"DA02": "../../layer-02-workflow-concepts/completion-and-effects/git.md",
                            "DA03": "../../layer-02-workflow-concepts/completion-and-effects/acceptance.md"},
}
MODULE_CHECKPOINT_L3_OWNERS = {
    "entry-readiness": {"ER00": {"module-entry-resolution", "route-entry"}, "ER02": {"enhanced-path-selection"}},
    "session-readiness": {"SR00": {"module-entry-resolution"}, "SR02": {"session-state-resolution"}, "SR03": {"session-audit-resolution"}},
    "work-definition": {"WD00": {"module-entry-resolution"}, "WD01": {"context-source-selection", "decision-context-selection"}, "WD02": {"advisory-selection"}, "WD03": {"planning-output-selection"}},
    "single-execution": {"SE00": {"module-entry-resolution"}, "SE01": {"executor-selection", "output-route-selection"}, "SE05": {"advisory-selection"}},
    "delegated-execution": {"DE00": {"module-entry-resolution"}, "DE01": {"bootstrap-selection"}, "DE02": {"executor-selection", "output-route-selection"}, "DE03": {"role-reservation"}, "DE08": {"advisory-selection"}},
    "verification-repair": {"VR00": {"module-entry-resolution"}, "VR04": {"advisory-selection"}, "VR05": {"repair-disposition"}},
    "documentation": {"DOC00": {"module-entry-resolution"}, "DOC04": {"documentation-impact"}},
    "delivery-acceptance": {"DA00": {"module-entry-resolution"}},
}

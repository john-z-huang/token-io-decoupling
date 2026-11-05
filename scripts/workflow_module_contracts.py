"""Shared immutable contract for Coding's Layer-04 route/module structure."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROUTES_DIR = Path("docs/skill/references/coding/layer-04-workflows")
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
    "work-definition": (
        ("WD01", "WD02"), ("WD02", "D_ROUTING_ADVICE"),
        ("WD_ADVICE_NA", "D_ROUTING_ADVICE"), ("D_ROUTING_ADVICE", "WD03"),
        ("D_ROUTING_ADVICE", "WD_ROUTING_NA"), ("WD_ROUTING_NA", "WD03"),
        ("WD03", "D_PLAN"), ("WD_PLAN", "WD_DONE"),
    ),
    "single-execution": (
        ("D_GATE", "SE03"), ("D_GATE", "SE05"),
        ("SE03", "D_OUTPUT"), ("D_OUTPUT", "SE_OUTPUT_PREP"),
        ("SE_OUTPUT_PREP", "SE_OUTPUT_PREFLIGHT"),
        ("SE_OUTPUT_PREFLIGHT", "SE_OUTPUT_APPLY"),
        ("SE_OUTPUT_APPLY", "SE_OUTPUT_REVIEW"), ("SE_OUTPUT_REVIEW", "SE04"),
        ("D_OUTPUT", "SE_OUTPUT_NA"), ("SE_OUTPUT_NA", "SE04"),
        ("D_OUTPUT", "SE_OUTPUT_NEEDS"),
        ("D_RECOVERY", "SE_NEEDS_EOD"), ("SE_NEEDS_EOD", "SE05"),
        ("D_RECOVERY", "SE_NEEDS_AMEND"), ("SE_NEEDS_AMEND", "SE05"),
        ("D_RECOVERY", "D_CONTROL"), ("D_CONTROL", "SE_NEEDS_NEXT"),
        ("D_CONTINUE_COVERS", "D_REROUTE"), ("D_CONTINUE_COVERS", "SE05"),
        ("D_REROUTE", "SE02"),
    ),
    "delegated-execution": (
        ("DE01", "DE02"), ("DE02", "D_EXEC"), ("D_EXEC", "DE03"),
        ("D_ROLE", "DE04"), ("D_GATE", "DE05"), ("DE05", "D_CHILD"),
        ("D_CHILD", "DE06"), ("DE06", "DE07"),
        ("DE_NEEDS_PENDING", "DE_RESULT_REVIEW"),
        ("DE07", "D_OUTPUT"), ("D_OUTPUT", "DE_OUTPUT_PREP"),
        ("DE_OUTPUT_PREP", "DE_OUTPUT_PREFLIGHT"),
        ("DE_OUTPUT_PREFLIGHT", "DE_OUTPUT_APPLY"),
        ("DE_OUTPUT_APPLY", "DE_OUTPUT_REVIEW"), ("DE_OUTPUT_REVIEW", "D_RESULT"),
        ("D_OUTPUT", "DE_OUTPUT_NA"), ("DE_OUTPUT_NA", "D_RESULT"),
        ("D_OUTPUT", "DE_NEEDS_OUTPUT"),
        ("D_RESULT", "DE_RESULT_REVIEW"), ("D_RESULT", "DE_NEEDS_PENDING"),
        ("D_RESULT", "DE_NEEDS_SLICE"),
        ("DE_RESULT_REVIEW", "DE08"), ("DE_RESULT_REVIEW", "DE_NEEDS_PENDING"),
        ("D_RECOVERY", "DE_NEEDS_AMEND"), ("DE_NEEDS_AMEND", "DE08"),
        ("D_RECOVERY", "DE04"), ("D_RECOVERY", "D_CONTROL"),
        ("D_CONTINUE_COVERS", "D_REROUTE"), ("D_REROUTE", "DE01"),
    ),
    "verification-repair": (("D_RESULT", "VR05"), ("VR05", "D_REPAIR"), ("D_REPAIR", "VR_SCOPE"), ("VR_SCOPE", "VR_EXEC"), ("VR_EXEC", "VR_HANDOFF"), ("VR_HANDOFF", "VR01"), ("D_RESULT", "VR06")),
    "documentation": (
        ("D_PREFLIGHT", "DOC_PREFLIGHT"), ("D_PREFLIGHT", "DOC_PREFLIGHT_NA"),
        ("D_PREFLIGHT", "DOC_NEEDS_PREFLIGHT"), ("DOC_PREFLIGHT", "DOC02"),
        ("DOC_PREFLIGHT_NA", "DOC02"),
        ("D_MEMORY", "DOC03"), ("DOC03", "D_MEMORY_VERIFY"),
        ("D_MEMORY_VERIFY", "DOC_MEM_VERIFY_NA"), ("DOC_MEM_VERIFY_NA", "DOC04"),
        ("D_MEMORY_VERIFY", "DOC_MEM_VERIFY"), ("DOC_MEM_VERIFY", "DOC04"),
        ("DOC_MEM_VERIFY", "DOC_NEEDS_MEM"), ("DOC03", "DOC_NEEDS_MEM"),
        ("DOC04", "DOC05"), ("DOC05", "DOC06"),
    ),
    "delivery-acceptance": (("D_VERIFIED", "D_GIT"), ("D_GIT", "DA02"), ("DA02", "DA03"), ("DA03", "D_PLAN"), ("D_PLAN", "DA04"), ("DA04", "DA05")),
}
MODULE_REQUIRED_LABEL_FRAGMENTS = {
    "delivery-acceptance": {
        "en": {
            "DA04": "Preserve full plan; append final evidence; verify lossless archive; same repository scope"
        },
        "zh": {"DA04": "保留计划全文；追加最终证据；验证无损归档；同一仓库存储范围"},
    },
    "work-definition": {
        "en": {
            "D_PLAN": "Persistence explicitly prohibited?",
            "WD_PLAN": "verify repository scope",
            "WD_PLAN_NA": "documented persistence restriction",
        },
        "zh": {
            "D_PLAN": "明确禁止持久化？",
            "WD_PLAN": "核验仓库存储范围",
            "WD_PLAN_NA": "已记录的持久化限制",
        },
    },
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
    "work-definition": {
        "en": {
            ("D_PLAN", "WD_PLAN"): "no; default",
            ("D_PLAN", "WD_PLAN_NA"): "yes; restriction exception",
            ("D_PLAN", "WD_BLOCK"): "explicit persistence requirement conflicts",
            ("D_ROUTING_ADVICE", "WD_ROUTING_NA"): "optional advice not selected or ineligible; record reason",
        },
        "zh": {
            ("D_PLAN", "WD_PLAN"): "否；默认",
            ("D_PLAN", "WD_PLAN_NA"): "是；限制例外",
            ("D_PLAN", "WD_BLOCK"): "与明确持久化要求冲突",
            ("D_ROUTING_ADVICE", "WD_ROUTING_NA"): "未选择可选建议或不符合条件；记录原因",
        },
    },
    "single-execution": {
        "en": {
            ("SE_NEEDS_AMEND", "SE05"): "Contract/Decision and needed Context current",
            ("D_CONTINUE_COVERS", "D_REROUTE"): "prior Continue covers Slice; boundary and epochs current",
            ("SE02", "SE_BLOCK"): "required plan access, persistence, or verification failed",
            ("SE_OUTPUT_PREFLIGHT", "SE_OUTPUT_APPLY"): "fresh whole-batch pass on same pinned root and policy",
            ("SE_OUTPUT_APPLY", "SE_OUTPUT_REVIEW"): "exact application; receipts and actual state reviewed",
        },
        "zh": {
            ("SE_NEEDS_AMEND", "SE05"): "Contract/Decision及所需Context已当前",
            ("D_CONTINUE_COVERS", "D_REROUTE"): "Continue仍覆盖该Slice；边界与epoch当前",
            ("SE02", "SE_BLOCK"): "必需计划访问、持久化或核验失败",
            ("SE_OUTPUT_PREFLIGHT", "SE_OUTPUT_APPLY"): "在同一固定 root 和政策下新鲜 whole-batch 预检通过",
            ("SE_OUTPUT_APPLY", "SE_OUTPUT_REVIEW"): "准确应用完成；收据和实际状态已审阅",
        },
    },
    "delegated-execution": {
        "en": {
            ("DE01", "DE02"): "actual task explicitly authorized",
            ("DE06", "DE07"): "dispatch confirmed; enter while child executes",
            ("DE_OUTPUT_APPLY", "DE_OUTPUT_REVIEW"): "candidate ID/hash, receipts and actual current state retained",
            ("D_RESULT", "DE_NEEDS_PENDING"): "child result pending",
            ("D_RESULT", "DE_RESULT_REVIEW"): "actual result available for review",
            ("DE_NEEDS_PENDING", "DE_RESULT_REVIEW"): "actual result received; reuse retained evidence without re-preparing or re-applying",
            ("DE_RESULT_REVIEW", "DE08"): "actual result and retained evidence reviewed",
            ("DE_RESULT_REVIEW", "DE_NEEDS_PENDING"): "result still pending",
            ("DE_NEEDS_AMEND", "DE08"): "Contract/Decision and needed Context current",
            ("D_CONTINUE_COVERS", "D_REROUTE"): "prior Continue covers Slice; boundary and epochs current",
            ("DE04", "DE_BLOCK"): "required plan access, persistence, or verification failed",
            ("DE_OUTPUT_PREFLIGHT", "DE_OUTPUT_APPLY"): "fresh whole-batch pass on same pinned root and policy",
            ("DE_OUTPUT_APPLY", "DE_OUTPUT_REVIEW"): "exact application; candidate ID/hash, receipts and actual current state retained",
        },
        "zh": {
            ("DE01", "DE02"): "实际任务已明确授权",
            ("DE06", "DE07"): "派发已确认；子代理执行期间进入",
            ("DE_OUTPUT_APPLY", "DE_OUTPUT_REVIEW"): "候选 ID/hash、收据和实际当前状态已保留",
            ("D_RESULT", "DE_NEEDS_PENDING"): "子代理结果待处理",
            ("D_RESULT", "DE_RESULT_REVIEW"): "实际结果可供审阅",
            ("DE_NEEDS_PENDING", "DE_RESULT_REVIEW"): "收到实际结果；复用保留证据，不重新准备或再次应用",
            ("DE_RESULT_REVIEW", "DE08"): "实际结果和保留证据已审阅",
            ("DE_RESULT_REVIEW", "DE_NEEDS_PENDING"): "结果仍待处理",
            ("DE_NEEDS_AMEND", "DE08"): "Contract/Decision及所需Context已当前",
            ("D_CONTINUE_COVERS", "D_REROUTE"): "Continue仍覆盖Slice且边界/epoch当前",
            ("DE04", "DE_BLOCK"): "必需计划访问、持久化或核验失败",
            ("DE_OUTPUT_PREFLIGHT", "DE_OUTPUT_APPLY"): "在同一固定 root 和政策下新鲜 whole-batch 预检通过",
            ("DE_OUTPUT_APPLY", "DE_OUTPUT_REVIEW"): "准确应用；候选 ID/hash、收据和实际当前状态已保留",
        },
    },
    "verification-repair": {
        "en": {
            ("VR_SCOPE", "VR_EXEC"): "narrow repair authorized",
            ("VR_HANDOFF", "VR01"): "new fingerprint/epochs returned",
            ("D_RESULT", "VR06"): "all required items current and passed",
        },
        "zh": {
            ("VR_SCOPE", "VR_EXEC"): "窄范围修复已授权",
            ("VR_HANDOFF", "VR01"): "新指纹/epoch 已返回",
            ("D_RESULT", "VR06"): "所有必需项目当前有效且通过",
        },
    },
    "documentation": {
        "en": {
            ("D_PREFLIGHT", "DOC_PREFLIGHT"): "selected; exact candidate, scope and trusted baseline current",
            ("D_PREFLIGHT", "DOC_PREFLIGHT_NA"): "not selected/no applicable candidate; record reason",
            ("D_PREFLIGHT", "DOC_NEEDS_PREFLIGHT"): "selected but candidate, scope, or baseline missing",
            ("DOC03", "D_MEMORY_VERIFY"): "write operation succeeded",
            ("D_MEMORY_VERIFY", "DOC_MEM_VERIFY_NA"): "no stored-content check required; record N/A",
            ("D_MEMORY_VERIFY", "DOC_MEM_VERIFY"): "owner requires stored-content verification",
            ("DOC_MEM_VERIFY", "DOC04"): "matching verified evidence or content comparison passes",
            ("DOC_MEM_VERIFY", "DOC_NEEDS_MEM"): "required verification fails, is unavailable, or outcome is uncertain",
            ("DOC03", "DOC_NEEDS_MEM"): "required capability or write fails",
            ("DOC04", "DOC05"): "only documentation dimension changed",
            ("DOC05", "DOC06"): "applicable checks pass",
        },
        "zh": {
            ("D_PREFLIGHT", "DOC_PREFLIGHT"): "已选择；准确候选、范围和可信基线当前有效",
            ("D_PREFLIGHT", "DOC_PREFLIGHT_NA"): "未选择/无适用候选；记录原因",
            ("D_PREFLIGHT", "DOC_NEEDS_PREFLIGHT"): "已选择但候选、范围或基线缺失",
            ("DOC03", "D_MEMORY_VERIFY"): "写入操作成功",
            ("D_MEMORY_VERIFY", "DOC_MEM_VERIFY_NA"): "无需存储内容检查；记录 N/A",
            ("D_MEMORY_VERIFY", "DOC_MEM_VERIFY"): "owner 要求存储内容核验",
            ("DOC_MEM_VERIFY", "DOC04"): "匹配的核验凭据或内容比较通过",
            ("DOC_MEM_VERIFY", "DOC_NEEDS_MEM"): "必需核验失败、不可用或结果不明",
            ("DOC03", "DOC_NEEDS_MEM"): "必需能力或写入失败",
            ("DOC04", "DOC05"): "仅文档维度改变",
            ("DOC05", "DOC06"): "适用检查通过",
        },
    },
    "delivery-acceptance": {
        "en": {
            ("DA03", "D_PLAN"): "all criteria mapped",
            ("D_PLAN", "DA04"): "matching active plan exists",
            ("DA04", "DA05"): "preservation passed; archive equals final active content",
            ("D_PLAN", "DA_PLAN_NA"): "documented persistence restriction",
            ("D_PLAN", "DA_NEEDS_PLAN"): "required plan missing or inaccessible",
        },
        "zh": {
            ("DA03", "D_PLAN"): "所有 criteria 已映射",
            ("D_PLAN", "DA04"): "存在匹配 active plan",
            ("DA04", "DA05"): "内容保留通过；归档等于最终活动内容",
            ("D_PLAN", "DA_PLAN_NA"): "有记录的持久化限制",
            ("D_PLAN", "DA_NEEDS_PLAN"): "必需计划缺失或不可访问",
        },
    },
}
MODULE_GRAPH_SHA256 = {
    "en": {
        "delegated-execution": "373cd76116cdbdad3a862a97a8221a5da51bc8a6a6d51db2a65675f8efbf4110",
        "delivery-acceptance": "114d90b56e06ce1cb9909b4d96709db532fbb01e96263412166e3ad878481145",
        "documentation": "c9070e292a599a7d4c2be5156ef4570082bfe7a042c0e65ff4597a09f6574714",
        "entry-readiness": "269dc96c4965b035ce5ad6d6ea1fb04dd0cafbe64a8ec84f58e36f9a4745c2f8",
        "session-readiness": "16f94918cc826fdf291d9102adc049acf5fca12d6778425d517845f257406252",
        "single-execution": "c8e13c6a23674d0743d8a19d0256c8623afb873f18e0e8a53c4042aebf104795",
        "verification-repair": "e1101b3f9ccb50347b5011bd134ba863fe47e96c05519f5593297a730f44333e",
        "work-definition": "df5ac02fb9814c1d7c4239255ae11632b86188d0e945ad20336f2c93a21eeea7",
    },
    "zh": {
        "delegated-execution": "9ea8f48b70ec5ed8af34127fcd89c4b56a91f816498769ec871409f4a9ffd441",
        "delivery-acceptance": "38cd9058f163cdce14984ef7076db774f5ac0d35cbe6186f4d9c41af74dfe16c",
        "documentation": "4efd99ed15b4f66fbe1e0d784222d8e7a50a3a55308821fcc4ee6e4f0c2de2fe",
        "entry-readiness": "3c8a6bbf88b8d27126b04bde51fbe5c8b356e5cb4de13d2af0a145d642331b5e",
        "session-readiness": "a3756c195fef91d6e186c428fb1d030b0430d8dd0e677d10dd7da2af894245e1",
        "single-execution": "27a517874ef476a3b984a8f052ef9767311ab24547f16904b57edf570d9a2b66",
        "verification-repair": "c6ac131143c713a1a80daf5025e32d557e07dc1ab9b50dcce4850e59f40a7c0c",
        "work-definition": "85603bc72ab325515577e72be316797a608e09e05881c06a1ea3df2763b29cc8",
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
        "Once dispatch and the explicit memo value are confirmed, enter DE07 immediately while the child executes",
        "resume at the DE07 result-collection/review substep",
        "Do not restart or repeat preparation, preflight, or application while collecting the result",
        "`write_content_memo: true` or `false`",
    ),
    "documentation": (
        "DOC03 -- write operation succeeded --> D_MEMORY_VERIFY",
        "D_MEMORY_VERIFY -- no stored-content check required; record N/A --> DOC_MEM_VERIFY_NA",
        "D_MEMORY_VERIFY -- owner requires stored-content verification --> DOC_MEM_VERIFY",
        "DOC_MEM_VERIFY -- required verification fails, is unavailable, or outcome is uncertain --> DOC_NEEDS_MEM",
        "DOC04 -- only documentation dimension changed",
    ),
    "delivery-acceptance": (
        "DA03 -- all criteria mapped; every applicable item passes on current epochs --> D_PLAN",
        "DA04 -- preservation, update, archive or readback failed --> DA_BLOCK",
        "final summary cannot replace accumulated records",
        "archive is identical to the verified final active baseline",
        "same verified repository storage scope",
    ),
    "work-definition": (
        "selected storage scope, repository identity and paired active/archive namespaces",
    ),
}
MANIFEST_ROUTE_SHA256 = {
    "single-agent": "b131f04b533afae068f9a5439d9a46abaa02c5f357aa8af2602334bef864be74",
    "multi-agent": "794618ea45a215251c8b51aa3b811b6ffc012489da5602e2c31ff251ba29aad0",
}
MIXED_STEP_CONTRACTS = {
    ("single-agent", "S06"): {
        "semantic_substeps": ("Decision, Decision Brief and execution planning", "Planning output/Memory lifecycle, optional Decision advice, and task-stage routing advice", "Executor/output disposition for implementation"),
        "target_sequence": (("work-definition", ("WD01", "WD02", "WD03")), ("single-execution", ("SE01",))),
        "branch_or_return": "Do not merge later S09 Control advice with S06 Decision advice",
    },
    ("multi-agent", "M07"): {
        "semantic_substeps": ("Decision, two-level plan, planning Memory, Decision advice and task-stage routing advice", "Bootstrap proposal plus actual-task authorization", "Executor/output/role decision and Slice release"),
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
    "work-definition": {
        "WD02": "../../layer-01-fundamental-concepts/execution-planning/workflow-routing-advice.md",
    },
    "single-execution": {"SE02": "../../layer-01-fundamental-concepts/execution-control/execution-control.md",
                         "SE03": (
                             "../../layer-02-workflow-concepts/decision-and-execution/implementation.md",
                             "../../layer-01-fundamental-concepts/execution-planning/output-materialization.md",
                             "../../layer-01-fundamental-concepts/execution-planning/candidate-compliance.md",
                         ),
                         "SE04": "../../layer-01-fundamental-concepts/execution-control/execution-stage-feedback.md"},
    "delegated-execution": {"DE04": "../../layer-01-fundamental-concepts/execution-control/execution-control.md",
                            "DE05": "../../layer-01-fundamental-concepts/delegation/delegation-child-creation.md",
                            "DE06": "../../layer-01-fundamental-concepts/delegation/delegation-child-dispatch.md",
                            "DE07": (
                                "../../layer-02-workflow-concepts/decision-and-execution/implementation.md",
                                "../../layer-01-fundamental-concepts/execution-planning/output-materialization.md",
                                "../../layer-01-fundamental-concepts/execution-planning/candidate-compliance.md",
                            )},
    "verification-repair": {
        "VR01": "../../layer-01-fundamental-concepts/execution-planning/output-materialization.md",
    },
    "documentation": {
        "DOC02": "../../layer-01-fundamental-concepts/execution-planning/candidate-compliance.md",
    },
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

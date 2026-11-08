"""工作流有向图节点与边的语义标签合同。"""

MODULE_REQUIRED_LABEL_FRAGMENTS = {
    "delivery-acceptance": {
        "en": {
            "DA04": "Preserve full plan; append final evidence; "
            "verify lossless archive; same repository "
            "scope"
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
            ("D_ROUTING_ADVICE", "WD_ROUTING_NA"): "optional advice "
            "not selected or "
            "ineligible; record "
            "reason",
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
            ("D_CONTINUE_COVERS", "D_REROUTE"): "prior Continue "
            "covers Slice; "
            "boundary and epochs "
            "current",
            ("SE02", "SE_BLOCK"): "required plan access, persistence, or verification failed",
            ("SE_OUTPUT_PREFLIGHT", "SE_OUTPUT_APPLY"): "fresh "
            "whole-batch "
            "pass on same "
            "pinned root "
            "and policy",
            ("SE_OUTPUT_APPLY", "SE_OUTPUT_REVIEW"): "exact "
            "application; "
            "receipts and "
            "actual state "
            "reviewed",
        },
        "zh": {
            ("SE_NEEDS_AMEND", "SE05"): "Contract/Decision及所需Context已当前",
            ("D_CONTINUE_COVERS", "D_REROUTE"): "Continue仍覆盖该Slice；边界与epoch当前",
            ("SE02", "SE_BLOCK"): "必需计划访问、持久化或核验失败",
            ("SE_OUTPUT_PREFLIGHT", "SE_OUTPUT_APPLY"): "在同一固定 root "
            "和政策下新鲜 "
            "whole-batch "
            "预检通过",
            ("SE_OUTPUT_APPLY", "SE_OUTPUT_REVIEW"): "准确应用完成；收据和实际状态已审阅",
        },
    },
    "delegated-execution": {
        "en": {
            ("DE01", "DE02"): "actual task explicitly authorized",
            ("DE06", "DE07"): "dispatch confirmed; enter while child executes",
            ("DE_OUTPUT_APPLY", "DE_OUTPUT_REVIEW"): "exact "
            "application; "
            "candidate "
            "ID/hash, "
            "receipts and "
            "actual "
            "current "
            "state "
            "retained",
            ("D_RESULT", "DE_NEEDS_PENDING"): "child result pending",
            ("D_RESULT", "DE_RESULT_REVIEW"): "actual result available for review",
            ("DE_NEEDS_PENDING", "DE_RESULT_REVIEW"): "actual "
            "result "
            "received; "
            "reuse "
            "retained "
            "evidence "
            "without "
            "re-preparing "
            "or "
            "re-applying",
            ("DE_RESULT_REVIEW", "DE08"): "actual result and retained evidence reviewed",
            ("DE_RESULT_REVIEW", "DE_NEEDS_PENDING"): "result still pending",
            ("DE_NEEDS_AMEND", "DE08"): "Contract/Decision and needed Context current",
            ("D_CONTINUE_COVERS", "D_REROUTE"): "prior Continue "
            "covers Slice; "
            "boundary and "
            "epochs current",
            ("DE04", "DE_BLOCK"): "required plan access, persistence, or verification failed",
            ("DE_OUTPUT_PREFLIGHT", "DE_OUTPUT_APPLY"): "fresh "
            "whole-batch "
            "pass on "
            "same "
            "pinned "
            "root and "
            "policy",
        },
        "zh": {
            ("DE01", "DE02"): "实际任务已明确授权",
            ("DE06", "DE07"): "派发已确认；子代理执行期间进入",
            ("DE_OUTPUT_APPLY", "DE_OUTPUT_REVIEW"): "准确应用；候选 "
            "ID/hash、收据和实际当前状态已保留",
            ("D_RESULT", "DE_NEEDS_PENDING"): "子代理结果待处理",
            ("D_RESULT", "DE_RESULT_REVIEW"): "实际结果可供审阅",
            (
                "DE_NEEDS_PENDING",
                "DE_RESULT_REVIEW",
            ): "收到实际结果；复用保留证据，不重新准备或再次应用",
            ("DE_RESULT_REVIEW", "DE08"): "实际结果和保留证据已审阅",
            ("DE_RESULT_REVIEW", "DE_NEEDS_PENDING"): "结果仍待处理",
            ("DE_NEEDS_AMEND", "DE08"): "Contract/Decision及所需Context已当前",
            ("D_CONTINUE_COVERS", "D_REROUTE"): "Continue仍覆盖Slice且边界/epoch当前",
            ("DE04", "DE_BLOCK"): "必需计划访问、持久化或核验失败",
            ("DE_OUTPUT_PREFLIGHT", "DE_OUTPUT_APPLY"): "在同一固定 "
            "root "
            "和政策下新鲜 "
            "whole-batch "
            "预检通过",
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
            ("D_PREFLIGHT", "DOC_PREFLIGHT"): "selected; exact "
            "candidate, scope and "
            "trusted baseline current",
            ("D_PREFLIGHT", "DOC_PREFLIGHT_NA"): "not selected/no "
            "applicable candidate; "
            "record reason",
            ("D_PREFLIGHT", "DOC_NEEDS_PREFLIGHT"): "selected but "
            "candidate, scope, "
            "or baseline missing",
            ("DOC03", "D_MEMORY_VERIFY"): "write operation succeeded",
            ("D_MEMORY_VERIFY", "DOC_MEM_VERIFY_NA"): "no stored-content "
            "check required; "
            "record N/A",
            ("D_MEMORY_VERIFY", "DOC_MEM_VERIFY"): "owner requires stored-content verification",
            ("DOC_MEM_VERIFY", "DOC04"): "matching verified evidence or content comparison passes",
            ("DOC_MEM_VERIFY", "DOC_NEEDS_MEM"): "required verification "
            "fails, is unavailable, "
            "or outcome is "
            "uncertain",
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

MODULE_SEMANTIC_FRAGMENTS = {
    "single-execution": (
        "update the Contract and Decision under their owners, and update Context when needed",
        "obtain a new explicit `Continue`",
    ),
    "delegated-execution": (
        "separately authorize and assess the original task",
        "after the auxiliary task completes, return to DE01",
        "Once dispatch and the explicit memo value are confirmed, "
        "enter DE07 immediately while the child executes",
        "resume at the DE07 result-collection/review substep",
        "Do not restart or repeat preparation, preflight, or "
        "application while collecting the result",
        "`write_content_memo: true` or `false`",
    ),
    "documentation": (
        "DOC03 -- write operation succeeded --> D_MEMORY_VERIFY",
        "D_MEMORY_VERIFY -- no stored-content check required; record N/A --> DOC_MEM_VERIFY_NA",
        "D_MEMORY_VERIFY -- owner requires stored-content verification --> DOC_MEM_VERIFY",
        "DOC_MEM_VERIFY -- required verification fails, is unavailable, or "
        "outcome is uncertain --> DOC_NEEDS_MEM",
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

"""混合执行与验证修复阶段的固定步骤合同。"""

MIXED_STEP_CONTRACTS = {
    ("single-agent", "S06"): {
        "semantic_substeps": (
            "Decision, Decision Brief and execution planning",
            "Planning output/Memory lifecycle, "
            "optional Decision advice, and "
            "task-stage routing advice",
            "Executor/output disposition for implementation",
        ),
        "target_sequence": (
            ("work-definition", ("WD01", "WD02", "WD03")),
            ("single-execution", ("SE01",)),
        ),
        "branch_or_return": "Do not merge later S09 Control advice with S06 Decision advice",
    },
    ("multi-agent", "M07"): {
        "semantic_substeps": (
            "Decision, two-level plan, planning "
            "Memory, Decision advice and "
            "task-stage routing advice",
            "Bootstrap proposal plus actual-task authorization",
            "Executor/output/role decision and Slice release",
        ),
        "target_sequence": (
            ("work-definition", ("WD01", "WD02", "WD03")),
            ("delegated-execution", ("DE01", "DE02", "DE03", "DE04")),
        ),
        "branch_or_return": "This Decision/Bootstrap step is distinct from M16 Acceptance/archive",
    },
}

VERIFICATION_STEP_CONTRACTS = {
    ("single-agent", "S10"): {
        "checkpoints": ("VR01", "VR02", "VR03", "VR04", "VR06"),
        "return": "Current successful Verification returns through "
        "VR06 before returning the result; conditional "
        "advice and verifier visibility remain "
        "owner-gated.",
    },
    ("multi-agent", "M12"): {
        "checkpoints": ("VR01", "VR02", "VR03", "VR04", "VR06"),
        "return": "Current successful Verification returns through "
        "VR06 before returning the result; conditional "
        "advice and verifier visibility remain "
        "owner-gated.",
    },
}

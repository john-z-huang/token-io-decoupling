"""Fixed tool manifests and entry-point names for the four server profiles."""

from __future__ import annotations

PROFILE_TOOLS: dict[str, frozenset[str]] = {
    "workflow": frozenset(
        {
            "workflow_capabilities",
            "rules_get_context",
            "workflow_evaluate",
            "evaluate_control_checkpoint",
        }
    ),
    "root": frozenset(
        {
            "workflow_open",
            "delegation_reserve",
            "delegation_bind",
            "slice_check",
            "slice_release",
            "workflow_transition",
            "parent_get_worker_summary",
            "workflow_reconcile",
        }
    ),
    "worker": frozenset(
        {
            "worker_get_assignment",
            "worker_record_progress",
            "worker_get_evidence",
            "worker_report_blocker",
            "worker_get_recovery_context",
        }
    ),
    "share": frozenset({"database_schema_status", "state_get", "record_evidence"}),
}

PROFILE_ROLES: dict[str, str | None] = {
    "workflow": None,
    "root": "parent",
    "worker": "worker",
    "share": None,
}

PROFILE_SERVER_NAMES: dict[str, str] = {
    "workflow": "token-io-decoupling-workflow",
    "root": "token-io-decoupling-root-agent-tools",
    "worker": "token-io-decoupling-worker-agent-tools",
    "share": "token-io-decoupling-share-tools",
}


# Backwards-compatible name: values remain Codex server aliases, not executable paths.
PROFILE_SCRIPTS = PROFILE_SERVER_NAMES

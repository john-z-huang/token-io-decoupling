"""Agent-facing MCP descriptions for every exposed wire tool."""

from __future__ import annotations

SERVER_DESCRIPTION = (
    "Bounded Token I/O MCP tools. The active profile and verified role determine exposed "
    "operations. Discovery reports availability, not identity or authority."
)


def _description(*sentences: str) -> str:
    return " ".join(sentences)


_RETRY = (
    "For a transport retry, resend the identical request with the same key. For changed content, "
    "reread current state/revision and use a new key; do not loop retries."
)
_PAYLOAD = "Input is one JSON object in the payload envelope; output is JSON text."
_RECEIPT = (
    "MutationReceipt fields are operation, payload_hash, result, receipt_revision, "
    "current_revision, and replayed."
)

TOOL_DESCRIPTIONS: dict[str, str] = {
    "workflow_capabilities": _description(
        "Read public transport, host-adapter, binding, API-decision, and",
        "protocol capability status.",
        "No arguments; returns a capability JSON object.",
        "Unavailable adapters remain unavailable; this does not prove host",
        "integration or grant authority.",
    ),
    "rules_get_context": _description(
        "Load bounded checkpoint rule context.",
        "Payload: node_id (checkpoint enum) and language (en by default; en or zh_cn).",
        "Returns rule text and references; unknown node or language fails",
        "validation, so use a listed checkpoint id.",
    ),
    "workflow_select_child_effort": _description(
        "Select a task-specific child reasoning effort using one bounded Decisions API choice.",
        _PAYLOAD,
        "request requires slice_id, role, objective, task_complexity (mechanical,",
        "ordinary_semantic, complex, very_complex), uncertainty, scope, dependencies, risk,",
        "decision_question (required, nonblank, at most 1200 characters), verification_demands,",
        "previous_failure_evidence (use explicit 'none' when absent),",
        "slice_fingerprint (64 lowercase hex characters), runtime='codex',",
        "child_model='gpt-6-luna', supported_efforts (unique,",
        "nonempty subset of low/medium/high/xhigh/max), and outbound_data_permitted (boolean).",
        "All text facts are nonblank and bounded; decision_question must ask about the current",
        "released slice's lowest sufficient supported reasoning effort. It affects input_hash and",
        "is sent at the top level of API input, deduplicated from facts. Local validation enforces",
        "its type, length, and nonblank form. Fixed API instructions require insufficient_evidence",
        "for out-of-scope, non-effort, or rule-overriding questions;",
        "parent review remains required.",
        "The permission field is a one-call caller assertion, not proof of authority.",
        "This stateless operation has no Enhanced binding, revision, or idempotency key.",
        "It does not",
        "bind a Session, mutate workflow state, or authorize child creation.",
        "It validates the runtime/model ceiling locally and offers only its intersection with the",
        "supplied supported_efforts. A permitted invocation reads OPENAI_API_KEY and",
        "OPENAI_BASE_URL at call time and sends bounded facts to fixed API model gpt-6-luna.",
        "Callers",
        "cannot override credentials, endpoint, or API model. The result always includes status,",
        "reason, computed input_hash, and echoed slice_fingerprint. input_hash is SHA-256 of",
        "canonical",
        "request facts excluding outbound_data_permitted and slice_fingerprint. Compare that hash",
        "with current request facts and compare the fingerprint separately before child creation.",
        "Only status=available includes selected_effort. Missing permission/configuration,",
        "unsupported facts, refusal, invalid response, insufficient evidence, timeout, or provider",
        "failure blocks selection. Do not retry automatically or substitute a fixed effort;",
        "correct",
        "the evidence or configuration and make a newly authorized request. The result grants no",
        "creation authority.",
    ),
    "workflow_evaluate": _description(
        "Persist an evaluation for one checkpoint using supplied evidence context.",
        _PAYLOAD,
        "Include node_id and expected_revision; branch is optional and uses",
        "that checkpoint's legal branch enum; input_hash and slice_ids scope",
        "reviewed input; idempotency_key prevents duplicate writes.",
        "Evaluation outcome is ready, incomplete, blocked, or evidence_on_demand;",
        "it records a gate result and does not itself authorize execution.",
        "Requires verified Root identity and guards; returns evaluation outcome",
        "(ready, incomplete, blocked, or evidence_on_demand), branch, rule/input",
        "hashes, basis/result revisions, missing facts/evidence, and stale status.",
        "Optional semantic_input is a node_id-discriminated object for",
        "task_intent, output_class, contract_change, verification_impact, or",
        "control, and typed facts must match node_id.",
        "Facts are requested_outcome/deliverables/task_signal for task_intent",
        "(coding/not_coding/mixed/unclear); requested_output/deliverables/",
        "delegation_boundary (root_only/worker_eligible/mixed/unclear) for",
        "output_class; change_summary/objective_or_scope_changed/",
        "new_user_direction_present for contract_change; change_summary and",
        "changed_dimensions/affected_coverage for verification_impact; and",
        "progress_signal/slice_outcome/evidence_request_status/boundary_summary",
        "for control. With semantic_input the JSON result has separate core and",
        "advice objects; advice.status is available, fallback, or stale. It may",
        "use API only when enabled and outbound data is permitted; it never",
        "selects a branch.",
        _RETRY,
    ),
    "evaluate_control_checkpoint": _description(
        "Persist the Control checkpoint evaluation.",
        _PAYLOAD,
        "Provide expected_revision and idempotency_key; optional branch,",
        "input_hash, slice_ids, and semantic_input follow the Control",
        "contract.",
        "Requires verified Root identity and guards; returns evaluation outcome",
        "(ready, incomplete, blocked, or evidence_on_demand), branch, rule/input",
        "hashes, basis/result revisions, missing facts/evidence, and stale status.",
        "Without semantic_input the JSON result is the evaluation; with it,",
        "the result separates core evaluation and advice. Control evaluation is",
        "not the Control transition or evidence-on-demand confirmation.",
        "semantic_input fields are progress_signal",
        "(continue/amend/stop/evidence-on-demand), slice_outcome",
        "(ready/incomplete/blocked/returned), evidence_request_status",
        "(not_requested/pending/returned), and boundary_summary. Advice can use",
        "API only under explicit",
        "enablement and outbound permission. The caller judges suggested_choice;",
        "advice does not set/replace core.branch or authorize a transition.",
        _RETRY,
    ),
    "workflow_open": _description(
        "Create the root workflow from a typed workflow-open request.",
        _PAYLOAD,
        "mode_count.mode is Single-Agent Coding or Multi-Agent Coding;",
        "child_count is 0 for Single-Agent and positive for Multi-Agent.",
        "Also include mode_source (explicit/default),",
        "source as SemanticRef {uri, content_hash SHA-256}, optional",
        "semantic_references (same shape),",
        "expected_revision (0 by default), and idempotency_key.",
        "Requires verified parent role. Initializes a new workflow; an",
        "identical existing workflow is read back without resetting identity,",
        "while a mismatched locked contract/identity or stale revision fails.",
        "Returns MutationReceipt with operation, payload_hash, result,",
        "receipt_revision, current_revision, and replayed.",
        _RETRY,
    ),
    "delegation_reserve": _description(
        "Reserve a child allocation for the requested role.",
        _PAYLOAD,
        "role must be Primary Output, Change Verification, Context",
        "Bootstrap/Refresh, or Documentation/Comments & Git Operations.",
        "Supply expected_revision and idempotency_key. Requires verified",
        "parent identity and delegation guards; Single-Agent has no allocations.",
        "Returns MutationReceipt whose result contains allocation_id, slot,",
        "and normalized role; reservation does not bind a child.",
        _RECEIPT,
        _RETRY,
    ),
    "delegation_bind": _description(
        "Bind a reserved allocation to a verified child session.",
        _PAYLOAD,
        "Supply allocation_id, child_session_id, expected_revision, and idempotency_key.",
        "Requires verified parent identity and host verification of the",
        "child; returns receipt with allocation_id and child_session_id.",
        "Unknown or mismatched child binding fails closed.",
        _RECEIPT,
        _RETRY,
    ),
    "slice_check": _description(
        "Check whether a typed slice spec meets current release requirements.",
        "Payload spec contains allocation_id; output_class (code_configuration,",
        "skill_instructions, ordinary_documentation, other, or unknown);",
        "objective, return_conditions, and unreleased_boundary SemanticRefs",
        "(uri plus SHA-256 content_hash); nonempty authorized_paths and",
        "change_categories (source_code/configuration/tests/skill_instructions);",
        "and write_content_memo.",
        "Requires verified parent role; this check does not release or mutate",
        "a slice. Returns SliceCheckResult (eligible, reason, allocation_id,",
        "output_class, input_hash); resolve findings before slice_release.",
    ),
    "slice_release": _description(
        "Persist/release an eligible bounded slice for an allocation.",
        _PAYLOAD,
        "Supply spec, expected_revision, and idempotency_key.",
        "Requires verified parent role, release guards, and valid allocation.",
        "Single-Agent slices use allocation_id=root; Multi-Agent slices use a",
        "reserved allocation and do not create or bind a child. This grants no",
        "permission outside the declared paths/categories/boundary.",
        "Failed checks or stale state block release; returns a mutation receipt.",
        _RECEIPT,
        _RETRY,
    ),
    "workflow_transition": _description(
        "Apply one typed workflow transition.",
        _PAYLOAD,
        "request.kind selects control (evaluation_id, outcome",
        "continue/amend/stop), advance_epoch (dimension), confirm_checkpoint",
        "(evaluation_id), session_audit (full session_audit contract),",
        "confirm_native_reconcile (snapshot), or resolve_native_reconcile",
        "(canonical_reconcile_id, snapshot_hash, unresolved_set_hash, choice",
        "adopt_native_pair/retain_sqlite_pair, reviewed_native_revision/epochs,",
        "root_decision_ref, native_freshness_refs, root_quiescence_refs).",
        "Every nested request requires expected_revision and idempotency_key.",
        "Requires verified parent role and transition guards; returns",
        "MutationReceipt with typed result and revisions. Transitions can",
        "change Control or epoch state.",
        _RECEIPT,
        _RETRY,
    ),
    "parent_get_worker_summary": _description(
        "Read the summary for one parent-owned allocation.",
        "Payload: allocation_id. Requires verified parent role.",
        "Returns WorkerState: allocation_id, worker_session_id, role,",
        "output_class, revision, progress, and blockers. Missing or unbound",
        "allocations fail; use for oversight, not as a Worker write path.",
    ),
    "workflow_reconcile": _description(
        "Compare and, when confirmed, reconcile a supplied native snapshot.",
        _PAYLOAD,
        "snapshot has project/root ids, mode and lifecycle, source/references,",
        "revision, allocations, epochs, and evidence_refs. Provide confirm",
        "(false by default), expected_revision, and idempotency_key every call.",
        "An unconfirmed comparison may still be recorded; false is not a dry run.",
        "Requires verified parent role; returns ReconcileResult status",
        "matched/conflict/awaiting_confirmation, differences,",
        "observed/result/current revisions, and native_refs. Review conflicts",
        "and state before confirming.",
        _RETRY,
    ),
    "worker_get_assignment": _description(
        "Read the calling Worker's current assignment.",
        "No arguments. Requires verified Worker binding and valid assignment guards.",
        "Returns assignment/allocation identity, role, output class, assigned",
        "slice boundary, and current revision; unavailable assignment or",
        "revoked binding fails closed. This grants no permission outside it.",
    ),
    "worker_record_progress": _description(
        "Record progress for the calling Worker's own assignment.",
        _PAYLOAD,
        "Supply record.status (started, in_progress, or reported_complete),",
        "record.milestone (SemanticRef {uri, content_hash}) and",
        "record.references, plus expected_revision and idempotency_key.",
        "reported_complete records the Worker's report; it is not parent",
        "acceptance.",
        "Requires verified Worker identity and own-store guards; returns",
        "MutationReceipt operation, payload_hash, result, receipt_revision,",
        "current_revision, and replayed. Reread assignment/state after",
        "conflict.",
        _RETRY,
    ),
    "worker_get_evidence": _description(
        "Read evidence by identifier.",
        "Payload: evidence_id. Requires verified Worker identity and own-store guards.",
        "Returns matching evidence facts, references, coverage, hashes,",
        "revisions, and stale status visible to that Worker; missing or",
        "out-of-scope identifiers fail closed.",
    ),
    "worker_report_blocker": _description(
        "Record a blocker for the calling Worker's own assignment.",
        _PAYLOAD,
        "Supply blocker.blocker_id, blocker.reason (SemanticRef uri/content_hash),",
        "blocker.references, expected_revision, and idempotency_key.",
        "Requires verified Worker identity and own-store guards; returns",
        "MutationReceipt operation, payload_hash, result, receipt_revision,",
        "current_revision, and replayed. Reread assignment and state after",
        "conflict.",
        _RETRY,
    ),
    "worker_get_recovery_context": _description(
        "Read the calling Worker's recovery context; no arguments.",
        "Requires verified Worker binding and own-store guards.",
        "Returns exactly assignment (worker_get_assignment result) and state",
        "(worker_get_state JSON). Use those current objects to resume; this",
        "tool generates no recovery plan and cannot bypass guards.",
    ),
    "database_schema_status": _description(
        "Read the database schema diagnostic.",
        "No arguments; public and does not inspect caller-selected paths.",
        "Returns schema status, including an unavailable diagnostic when no",
        "trusted binding exists. Use before state operations to understand",
        "compatibility.",
    ),
    "state_get": _description(
        "Read state for the verified role.",
        "Payload may include index_page (collection, optional cursor,",
        "page_size 1–128) for parent pagination; Workers must omit it.",
        "Requires trusted binding and state-read guards; returns role-scoped",
        "state, revision, and pagination metadata. A stale or invalid cursor",
        "requires restarting from the first page.",
    ),
    "record_evidence": _description(
        "Record evidence in the verified role's authorized store.",
        _PAYLOAD,
        "submission includes node_id, nonempty facts (fact_key plus a",
        "judgment: unknown, missing_evidence, not_applicable with reason, or",
        "determined with value/evidence), evidence_refs and coverage_dimensions",
        "(both default empty), input_hash, and optional evidence_request_id.",
        "Provide expected_revision and idempotency_key.",
        "Requires trusted role binding and evidence-write guards; returns",
        "MutationReceipt with evidence result and revisions. Evidence is not",
        "itself a checkpoint decision.",
        _RETRY,
    ),
    "workflow_get_state": _description(
        "Compatibility embedding alias for parent workflow state read; not",
        "present in fixed profiles.",
        "Payload may include index_page for pagination; requires verified parent binding.",
        "Returns parent-scoped state. Restart pagination after cursor errors.",
    ),
    "workflow_record_evidence": _description(
        "Compatibility embedding alias for parent evidence submission; not",
        "present in fixed profiles.",
        _PAYLOAD,
        "submission has node_id, nonempty fact_key/judgment facts, optional",
        "evidence_refs/coverage_dimensions, input_hash, and optional",
        "evidence_request_id; include expected_revision/idempotency_key.",
        "Requires verified parent identity and evidence-write guards.",
        "submission uses node_id, facts, evidence_refs, coverage_dimensions,",
        "input_hash, and optional evidence_request_id. Returns MutationReceipt",
        "with operation, payload_hash, result, receipt_revision, current_revision,",
        "and replayed; evidence is not a decision.",
        _RETRY,
    ),
    "worker_get_state": _description(
        "Compatibility embedding alias for the calling Worker's own state",
        "read; not present in fixed profiles.",
        "No arguments; requires verified Worker binding and own-store guards.",
        "Returns only role-scoped state; cross-Worker reads fail closed.",
    ),
    "worker_record_evidence": _description(
        "Compatibility embedding alias for the calling Worker's evidence",
        "submission; not present in fixed profiles.",
        _PAYLOAD,
        "submission has node_id, nonempty fact_key/judgment facts, optional",
        "evidence_refs/coverage_dimensions, input_hash, and optional",
        "evidence_request_id; include expected_revision/idempotency_key.",
        "Requires verified Worker identity and own-store evidence guards.",
        "submission uses node_id, facts, evidence_refs, coverage_dimensions,",
        "input_hash, and optional evidence_request_id. Returns MutationReceipt",
        "with operation, payload_hash, result, receipt_revision, current_revision,",
        "and replayed.",
        _RETRY,
    ),
}

SERVER_INSTRUCTIONS: dict[str, str] = {
    "workflow": (
        "Profile workflow exposes capabilities, rules, the stateless child-effort selector, and "
        "Root-bound persisted evaluations. Start with workflow_capabilities and rules_get_context; "
        "invoke workflow_select_child_effort only for an authorized child-creation decision with "
        "explicit outbound_data_permitted=true and bounded current slice facts, then compare its "
        "input_hash and selected effort with verified runtime facts before creation. The selector "
        "does not authorize creation. Evaluate against current "
        "evidence and revision. Evaluation requires verified Root binding. Five-node semantic "
        "advice is a separate optional feature, disabled by default. The child-effort selector "
        "makes an API request only for an explicit per-invocation outbound_data_permitted=true "
        "assertion; this assertion is not proof of authority. It never mutates workflow state. "
        "Tool discovery does not prove host identity or grant authority."
    ),
    "root": (
        "Profile root exposes parent control, delegation, slice, transition, summary, and "
        "reconciliation tools only; public workflow/rule tools are on the separate "
        "workflow profile. "
        "It requires trusted parent binding and current guards. Start or read back the workflow "
        "with workflow_open, then check a slice before release. Mutations use revision/idempotency "
        "contracts; discovery grants no authority."
    ),
    "worker": (
        "Profile worker exposes a bound Worker's assignment, own progress/evidence, blocker, and "
        "recovery context. It requires trusted Worker binding and own-store guards; cross-Worker "
        "access is rejected. Start with worker_get_assignment and worker_get_recovery_context. "
        "Writes require current revision/idempotency data. Discovery grants no authority."
    ),
    "share": (
        "Profile share exposes schema status and role-routed state/evidence operations. Calls "
        "resolve trusted role binding and enforce role-specific guards; Worker state reads cannot "
        "paginate. Start with database_schema_status, then read state before writing evidence. "
        "Mutations require current revision/idempotency data. Discovery grants no authority."
    ),
}


def tool_description(name: str) -> str:
    """Return the required description or fail closed on an uncatalogued wire name."""
    try:
        return TOOL_DESCRIPTIONS[name]
    except KeyError as exc:
        raise ValueError(f"missing Agent-facing metadata for MCP tool: {name}") from exc


def server_description(profile: str | None, bound_role: str | None) -> str:
    """Describe only the operations registered for this profile and embedding role."""
    if profile is None:
        if bound_role == "parent":
            scope = (
                "public tools and parent-bound workflow/delegation operations, including aliases"
            )
        elif bound_role == "worker":
            scope = "public tools and Worker assignment/progress operations, including aliases"
        else:
            scope = "public capabilities, rules, and schema diagnostics only"
    else:
        scope = {
            "workflow": (
                "public capabilities/rules, stateless effort selection, and Root-bound "
                "evaluation tools"
            ),
            "root": "parent control, delegation, slice, transition, summary, reconciliation",
            "worker": "Worker assignment, progress, evidence lookup, blocker, and recovery tools",
            "share": "schema status and role-routed state/evidence tools",
        }.get(profile)
        if scope is None:
            raise ValueError(f"missing Agent-facing description for MCP profile: {profile}")
    return (
        f"{scope.capitalize()}. Protected calls require the appropriate verified trusted-host "
        "binding and current guards. Discovery reports availability, not identity or authority."
    )


def server_instructions(profile: str | None, bound_role: str | None) -> str:
    """Return instructions scoped to the registered tools and embedding role."""
    if profile is None:
        if bound_role == "parent":
            return (
                "Parent-bound embedding exposes public tools and parent operations with "
                "compatibility aliases. Start with workflow_capabilities and rules_get_context, "
                "then use parent workflow/delegation operations. No Worker operations are exposed. "
                "Mutations require current revision/idempotency data; discovery grants "
                "no authority."
            )
        if bound_role == "worker":
            return (
                "Worker-bound embedding exposes public tools and this Worker's own assignment, "
                "state, progress, evidence, blocker, and recovery operations. Start with "
                "worker_get_assignment "
                "and worker_get_recovery_context. No parent operations are exposed. Writes require "
                "current revision/idempotency data; discovery grants no authority."
            )
        return (
            "This public-only server exposes capabilities, rules, and schema diagnostics. "
            "Start with workflow_capabilities and rules_get_context. Protected "
            "operations are unavailable; a "
            "listed or public tool does not create a trusted host binding or grant authority."
        )
    try:
        return SERVER_INSTRUCTIONS[profile]
    except KeyError as exc:
        raise ValueError(f"missing Agent-facing instructions for MCP profile: {profile}") from exc

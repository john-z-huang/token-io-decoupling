"""Agent-facing MCP descriptions for every exposed wire tool."""

from __future__ import annotations

SERVER_DESCRIPTION = (
    "MCP server for a locally available Codex CLI, including local Work when it uses the local "
    "Codex CLI/app-server path. Cloud ChatGPT conversations, remote Work, and other Code Agents "
    "are not direct clients. If another Agent installs and configures Codex CLI in its own "
    "environment, only that local CLI path is supported; no other Agent or cloud adapter is "
    "provided. No runtime-environment selection step is exposed. Bounded Token I/O tools. The "
    "active profile and verified role determine exposed operations. Discovery reports "
    "availability, not identity or authority."
)


def _description(*sentences: str) -> str:
    return " ".join(sentences)


_RETRY = (
    "For an uncertain mutation result, read back current state/receipt first. If replay is needed, "
    "resend the identical payload with the same idempotency key. For changed content, reread the "
    "current revision and use a new key. Validation, permission, or guard failures need "
    "correction; "
    "do not retry them unchanged."
)
_PAYLOAD = "Input is one JSON object in the payload envelope; output is JSON text."
_RECEIPT = (
    "MutationReceipt fields are operation, payload_hash, result, receipt_revision, "
    "current_revision, and replayed."
)
_DECISION_RESULT = (
    "DelegationDecisionResult status is available, skipped, fallback, blocked, or stale: "
    "available is a suggestion; skipped means a local explicit/policy branch did not call "
    "Decisions; fallback is a policy-permitted fallback; blocked means no suggestion is usable "
    "until its guard, evidence, or review condition is resolved; "
    "stale must be refreshed and is never a fallback. decision is child_role, executor, "
    "child_candidate, or output_tokens. Inspect reason, suggested_value, fallback_value, "
    "next_action, input_hash (nullable on a local branch), fact_revision, fact_fingerprint, "
    "context_input_hash, source_policy_hashes, optional model/total_tokens, and "
    "optional recovery (retry_eligible, action, failure_class, total_attempt_limit). "
    "authority=advisory_only. Before acting, compare returned request/context/policy hashes and "
    "fact revision/fingerprint with the exact current caller facts, reviewed context, and owner "
    "text. On stale, refresh current facts and owner text, regenerate/review context if needed, "
    "and obtain a new result; never reuse it or convert it to fallback. A Decisions request "
    "requires per-call outbound_data_permitted=true plus nonblank OPENAI_API_KEY and "
    "OPENAI_BASE_URL; the tool reads and explicitly uses both with fixed model gpt-6-luna, "
    "without caller endpoint/model overrides or automatic retries. These advisory results do "
    "not reserve, create, bind, dispatch, or authorize a child or Root execution; recheck current "
    "mode, permissions, budget, role uniqueness, scope, and availability before an action."
)

_READ_ONLY_TOOLS = {
    "workflow_capabilities",
    "rules_get_context",
    "parent_get_worker_summary",
    "worker_get_assignment",
    "worker_get_evidence",
    "worker_get_recovery_context",
    "database_schema_status",
    "state_get",
    "workflow_get_state",
    "worker_get_state",
}
_STATE_WRITE_TOOLS = {
    "workflow_evaluate",
    "evaluate_control_checkpoint",
    "workflow_open",
    "delegation_reserve",
    "delegation_bind",
    "delegation_unreserve",
    "slice_check",
    "slice_release",
    "workflow_transition",
    "workflow_reconcile",
    "worker_record_progress",
    "worker_report_blocker",
    "record_evidence",
    "workflow_record_evidence",
    "worker_record_evidence",
}
_STATE_ADVICE_TOOLS = {"workflow_evaluate", "evaluate_control_checkpoint"}
_STATELESS_API_TOOLS = {
    "workflow_select_child_effort",
    "workflow_generate_decision_context",
    "workflow_select_child_role",
    "workflow_select_executor",
    "workflow_select_child",
    "workflow_assess_output_tokens",
}

TOOL_DESCRIPTIONS: dict[str, str] = {
    "workflow_capabilities": _description(
        "Read public capability summaries and capability_details (schema_version=2). No arguments;",
        "no identity or permission prerequisite. agent_runtime is the fixed local Codex CLI",
        "product scope, including local Work when it uses that local CLI/app-server path. Cloud",
        "ChatGPT conversations, remote Work, and other Code Agents are not direct clients. When",
        "another Agent installs/configures the CLI in its own environment, only that environment's",
        "local CLI path is supported; no other Agent/cloud adapter or runtime-environment",
        "selection step is provided. This static scope is not identity attestation.",
        "support.agent_runtime describes this static contract,",
        "configuration describes caller matching and persisted API advice, and runtime describes",
        "the provider's baseline binding, transport classification, and startup server mode.",
        "Status entries contain status, reason_code, message, source, and next_step; a verified",
        "binding includes its role. Disabled is normal configuration; unknown means the underlying",
        "cause cannot be determined safely. Legacy top-level fields remain summaries: non-embedded",
        "enhanced_binding stays unverified; binding_transport stays unavailable",
        "even after a valid probe.",
        "At most one provider read; no state/path inspection, mutation, or API request. Probes",
        "may use the host channel. No credentials, identity values, or raw errors are returned.",
        "On missing provider, guard failure, denial, or probe failure, inspect reason_code",
        "and next_step; configure a trusted host provider when required. A known transport or",
        "verified",
        "baseline does not verify caller metadata or operation-specific guards, enable Enhanced,",
        "change startup admission, or grant authority. No revision or idempotency key is required.",
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
        "failure blocks selection. The SDK makes one request; do not retry automatically or",
        "substitute a fixed effort. Correct evidence or configuration first. A transient candidate",
        "may be invoked again by the caller while the original authorization remains valid, after",
        "checking the same request hash, slice fingerprint, and current permissions; allow at most",
        "three total calls including",
        "the first.",
        "The result grants no",
        "creation authority.",
    ),
    "workflow_generate_decision_context": _description(
        "Generate one bounded decision question or context paragraph from caller-composed source",
        "material using one explicit Responses API request.",
        _PAYLOAD,
        "request requires raw_content (strict nonblank string, at most 60000 characters),",
        "decision_goal (strict nonblank string, at most 1200 characters), output_kind",
        "(decision_question or decision_context), and outbound_data_permitted (boolean).",
        "Compose and label user requirements, current Git diff facts, LSP observations, and plans",
        "before calling. The tool does not inspect repositories, files, commands, or LSP state.",
        "Source labels are caller assertions, not authenticity proofs. Input text is JSON-encoded",
        "without truncation and hashed canonically; the hash excludes only",
        "outbound_data_permitted.",
        "A question is limited to 1200 characters; a context paragraph to 6000. Structured",
        "missing_information has at most 8 nonblank items of at most 240 characters each.",
        "Explicit permission is required for each call; false permission blocks before reading",
        "credentials. No Enhanced binding, persisted state, automatic downstream Decisions call,",
        "or authority grant is involved.",
        "Each permitted call reads OPENAI_API_KEY and OPENAI_BASE_URL and explicitly uses them",
        "with the fixed model gpt-6-luna, Responses.parse, reasoning effort medium, no tools,",
        "store=false, disabled truncation, a 20-second client timeout, and zero retries.",
        "Only a completed response from the exact model with the exact parsed Pydantic output",
        "schema can succeed. A nonblank description with no missing facts returns",
        "status=available; a null description with specific missing information returns",
        "blocked/insufficient_evidence.",
        "Every result includes status, reason, input_hash, and output_kind. Success also includes",
        "description, model, and optional total_tokens; only insufficient_evidence preserves",
        "missing_information.",
        "Compare input_hash against the current canonical raw_content, decision_goal,",
        "and output_kind",
        "before downstream use, then manually verify that the description preserves evidence and",
        "provenance. This hash covers generation input only and is not the downstream",
        "Decisions hash.",
        "Refusal, incomplete, malformed, wrong-model, invalid-output, or provider failures block",
        "without returning raw source, raw provider errors, or a fallback description. Correct",
        "missing facts/configuration or review invalid output. A transient candidate may be",
        "invoked again by the caller while the original authorization remains valid, after",
        "checking",
        "the request hash and current policy; allow at most three total calls including the first.",
        "There is no",
        "revision or idempotency key; the tool does not automatically retry or call Decisions.",
    ),
    "workflow_select_child_role": _description(
        "Select a permitted child role with one stateless Decisions choice.",
        _PAYLOAD,
        "request includes task_id, bounded task_summary, reviewed_context and its input hash,",
        "fact_revision/fingerprint, mode, Fork/mode-reselection facts, created_roles,",
        "reserved_roles, available_slots, explicit user creation/role facts, and the",
        "per-call outbound_data_permitted assertion. Generate and review the context with",
        "workflow_generate_decision_context first. An explicit user creation instruction skips",
        "Decisions and uses its explicit role or Primary Output fallback, subject to mode,",
        "Fork, same-role, budget, permission, and Root checks.",
        "The tool loads current child-role-selection and session-role-ownership owner text from",
        "the repository or packaged resources and returns policy/request hashes, a role suggestion",
        "or Primary fallback, guard reason, and next action. An API call reads both",
        "environment values and uses fixed model gpt-6-luna with zero automatic retries. A",
        "transient candidate may be re-invoked under still-valid task authorization after current",
        "facts and policy are checked; the caller tracks a maximum of three total calls including",
        "the first. Missing",
        "facts/policy/configuration, refusal, invalid/wrong-model response, or changed policy",
        "blocks or marks the result stale. A suggested role is one of Primary Output, Change",
        "Verification, Context Bootstrap/Refresh, or Documentation/Comments & Git Operations;",
        "no role is available when one is already created or reserved in the current Session.",
        "A Primary fallback applies only to an explicit user creation instruction with no explicit",
        "role, and only after mode, Fork, role uniqueness, budget, permission, and Root",
        "checks pass.",
        "The result is advisory only and never reserves or creates a child.",
        _DECISION_RESULT,
    ),
    "workflow_select_executor": _description(
        "Suggest Root or a child as executor with one stateless Decisions choice.",
        _PAYLOAD,
        "request includes task and reviewed-context hashes, current fact revision/fingerprint,",
        "Single/Multi mode, current-session child count, available approved slots, optional",
        "explicit_user_executor (root or sub_agent), and outbound_data_permitted.",
        "An explicit Root executor or an explicit executor in a compatible mode skips the API.",
        "Explicit sub_agent under locked Single-Agent mode blocks for Root review; it is never",
        "silently changed to Root. Single-Agent mode without an explicit executor skips the API",
        "and routes the local suggestion to Root. Otherwise the",
        "tool loads the current task-assignment owner and returns root, sub_agent, or a blocked",
        "result with hashes and next_action; suggested_value is root or sub_agent. API failure,",
        "stale facts/policy, or missing evidence never defaults to Root: refresh and review the",
        "current task/context and owner hashes, then make a new authorized choice;",
        "if still blocked,",
        "keep the executor unresolved.",
        "A sub_agent suggestion with unused approved capacity may continue through role selection",
        "and creation after all current gates pass; budget exhaustion requires explicit",
        "user approval",
        "through the Root reservation path. This does not create, dispatch,",
        "or authorize an executor. Permitted calls read both environment values and use fixed",
        "model gpt-6-luna with zero automatic retries. Any optional repeat is caller-decided under",
        "still-valid authorization after current hashes are checked; maximum three total calls per",
        "recovery process, including the first. Errors are sanitized; changed policy is stale.",
        _DECISION_RESULT,
    ),
    "workflow_select_child": _description(
        "Select a suitable existing current-session child, or return a safe fallback/wait result.",
        _PAYLOAD,
        "request includes bounded candidate refs and responsibility, capability, permission,",
        "current-session, availability, and task-relevant context facts. Candidate refs should be",
        "opaque local labels; inherited foreign-session agents are excluded. An explicit user",
        "candidate skips Decisions but still must pass eligibility checks. One eligible candidate",
        "is selected directly. With multiple eligible candidates, a unique idle candidate can be",
        "selected directly after busy candidates are filtered; multiple idle candidates still",
        "require a Decisions request even when Primary Output is preferred. An idle Primary",
        "narrows offered choices to that child plus insufficient_evidence; otherwise all suitable",
        "idle candidates are offered for task-context comparison. No numeric confidence cutoff is",
        "used. suggested_value is only one candidate_ref from the supplied eligible",
        "current-Session",
        "candidate pool. On API failure/refusal/invalid or insufficient response, an eligible idle",
        "Primary Output may be the policy fallback; a busy Primary requires waiting,",
        "and without an",
        "eligible Primary the choice stays unresolved. A stale fact or owner hash is not an API",
        "failure fallback: refresh assignment, availability, context, and owner policy,",
        "then make a new authorized request. Recheck candidate identity and availability",
        "before reuse or dispatch.",
        "Only candidates in the offered pool are included in the Decisions request. The tool loads",
        "current task-assignment and session-role-ownership owners, returns hashes",
        "and action guidance, and never dispatches work. A permitted API call reads",
        "both environment values, uses fixed model gpt-6-luna, and has zero retries. Invalid,",
        "refused, insufficient,",
        "wrong-model, or stale-policy results never become a successful selection.",
        _DECISION_RESULT,
    ),
    "workflow_assess_output_tokens": _description(
        "Assess independently whether direct Root output would be large in Output Token terms.",
        _PAYLOAD,
        "request includes reviewed task context, requested output shape/volume, current mode,",
        "idle and busy suitable current-session child counts, fact revision/fingerprint, and the",
        "optional explicit_user_executor and per-call outbound_data_permitted assertion. An",
        "explicit user executor skips this output-size request, subject to the locked mode;",
        "a sub_agent instruction under Single-Agent mode blocks for Root review. The",
        "tool loads the current output-token-routing",
        "owner and returns suggested_value yes or no, or a blocked/insufficient result",
        "with reason,",
        "hashes, and next_action. A no suggestion permits Root execution only after all other",
        "gates pass. A yes suggestion forbids Root immediate execution: use an eligible idle",
        "child, or keep waiting/hold if none is available; under Single-Agent, hold and report the",
        "topology boundary without inventing a child or reframing the task. Stale facts or owner",
        "hashes must be refreshed before another judgment.",
        "This judgment is independent of executor selection and does not dispatch or authorize",
        "work. Permitted calls read both environment values and use",
        "only fixed",
        "model gpt-6-luna with zero automatic retries. An optional repeat is caller-decided under",
        "still-valid authorization after current hashes are checked, with at most three total",
        "calls",
        "per recovery process including the first; errors are sanitized and policy changes stale.",
        _DECISION_RESULT,
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
        "selects a branch. advice.recovery is informational and never authorizes resubmitting this",
        "state mutation to retry advice. Same-key replay returns the stored evaluation and",
        "does not",
        "call Decisions again; continue without advice or review the existing result.",
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
        "Reserve one child allocation for a maintained role under the current Root workflow.",
        _PAYLOAD,
        "role must be Primary Output, Change Verification, Context",
        "Bootstrap/Refresh, or Documentation/Comments & Git Operations.",
        "Supply expected_revision and idempotency_key. Requires verified Root",
        "identity and delegation guards; Single-Agent has no allocations.",
        "A role already reserved or created in this Session cannot be reserved again.",
        "The optional budget_approval object is accepted only when the locked budget",
        "has no unassigned slot. It contains requested_child_count (exactly current count + 1)",
        "and user_approval (SemanticRef or EvidenceRef to the actual explicit user approval).",
        "Call only after Root reviews that evidence; the reference is a trusted Root",
        "attestation, not cryptographic host proof. The transaction changes the count source",
        "to that approval, retains the prior source, adds one slot, and reserves the",
        "requested different role atomically. Approval cannot authorize a duplicate role.",
        "Returns MutationReceipt whose result contains allocation_id, slot,",
        "normalized role, and (for an approved increase) an audit record; reservation does not",
        "create or bind a child. Replaying the same key and request does not increase",
        "the count twice.",
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
    "delegation_unreserve": _description(
        "Protected Root operation to clear one role reservation only when child creation",
        "has not started.",
        _PAYLOAD,
        "The payload is DelegationUnreserveRequest and all fields are required: allocation_id,",
        "creation_not_started (literal JSON true; false, 1, and string values are invalid),",
        "creation_not_started_reference is a SemanticRef or EvidenceRef with uri and",
        "SHA-256 content_hash.",
        "expected_revision, and idempotency_key.",
        "Requires verified Root binding, workflow-write capability, and identity/session/path",
        "guards.",
        "Only a Multi-Agent allocation in reserved state with no worker_session_id, worker",
        "event, or output can be released.",
        "Any Slice, Root outbox, dispatch event, delegation-bind receipt, or matching Worker",
        "identity, or unknown/corrupt/missing identity blocks.",
        "Existing subagents worker.sqlite3 files are inspected read-only; this operation",
        "creates no Worker database and runs no migrations.",
        "Symlinked paths, WAL/SHM/journal sidecars, or directory/database changes during",
        "inspection fail closed. Do not remove/checkpoint files to force a release.",
        "After confirming creation is still unstarted and the Worker store is stable, refresh",
        "current state/revision; use a new key if the request content changed.",
        "Success changes only role to null and status to unassigned; slot and child_count stay",
        "fixed. The MutationReceipt result includes the proof and a Root attestation whose",
        "authority limit states it is not host proof.",
        "This operation does not create, bind, or dispatch a child and makes no API request.",
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
        "Profile workflow exposes capabilities, rules, stateless decision-context generation, "
        "child-effort selection, and delegation decisions, plus "
        "Root-bound persisted evaluations. Start with workflow_capabilities and rules_get_context; "
        "call workflow_generate_decision_context only with caller-composed, provenance-labeled "
        "source material and explicit outbound_data_permitted=true when a question or context "
        "description is needed. It does not read files, make the downstream decision, call another "
        "tool automatically, or authorize an action. Review its description and "
        "missing-information "
        "result against the supplied facts. "
        "invoke workflow_select_child_effort only for an authorized child-creation decision with "
        "explicit outbound_data_permitted=true and bounded current slice facts, then compare its "
        "input_hash and selected effort with verified runtime facts before creation. The selector "
        "does not authorize creation. "
        "Use workflow_select_child_role, workflow_select_executor, workflow_select_child, and "
        "workflow_assess_output_tokens only with current bounded facts and current owner policy. "
        "These stateless Decisions suggestions require per-call outbound permission, read both "
        "configured environment values explicitly, and use fixed model gpt-6-luna. Compare fact, "
        "context, and policy hashes before acting; recheck Root identity, role uniqueness, locked "
        "budget/user approval, scope, permissions, availability, and mode. Explicit user creation "
        "or executor instructions skip the corresponding API. Suggestions never authorize child "
        "creation, dispatch, or Root execution; a large-output yes requires delegation or waiting. "
        "Evaluation requires verified Root binding. Five-node semantic "
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
        description = TOOL_DESCRIPTIONS[name]
        if name in _READ_ONLY_TOOLS:
            recovery = (
                "Recovery class: read-only lookup with no state mutation. Only an observed "
                "transient "
                "transport failure or explicit 5xx can justify repeating the same read; "
                "validation, permission, and guard errors are not transient."
            )
        elif name in _STATE_WRITE_TOOLS:
            recovery = (
                "Recovery class: state mutation. On unknown completion, read back state/receipt; "
                "replay only the identical payload with the same idempotency key. Changed content "
                "requires current state/revision and a new key. Validation, permission, and guard "
                "errors must be resolved first."
            )
            if name in _STATE_ADVICE_TOOLS:
                recovery += (
                    " Same-key replay does not call optional Decisions advice again; never "
                    "resubmit "
                    "the state mutation to retry advice."
                )
        elif name in _STATELESS_API_TOOLS:
            recovery = (
                "Recovery class: stateless, one API request per invocation with no SDK retry. Read "
                "the structured recovery object; only a transient candidate permits considering "
                "an explicit repeat under still-valid authorization after checking current input "
                "hash and policy. The caller tracks at most three total calls including the first. "
                "Other failures require correction or stop; this tool does not count attempts."
            )
        else:
            raise ValueError(f"missing recovery classification for MCP tool: {name}")
        return (
            "Codex CLI MCP tool, including Codex CLI/app-server use from Desktop and local Work. "
            + description
            + " "
            + recovery
        )
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
        f"Codex CLI MCP server (including Codex CLI/app-server use from Desktop and local Work). "
        f"{scope.capitalize()}. Protected calls require the appropriate verified trusted-host "
        "binding and current guards. Discovery reports availability, not identity or authority."
    )


def server_instructions(profile: str | None, bound_role: str | None) -> str:
    """Return instructions scoped to the registered tools and embedding role."""
    if profile is None:
        if bound_role == "parent":
            return (
                "This MCP server serves Codex CLI, including Codex CLI/app-server use from Desktop "
                "and local Work. "
                "Parent-bound embedding exposes public tools and parent operations with "
                "compatibility aliases. Start with workflow_capabilities and rules_get_context, "
                "then use parent workflow/delegation operations. No Worker operations are exposed. "
                "Mutations require current revision/idempotency data; discovery grants "
                "no authority."
            )
        if bound_role == "worker":
            return (
                "This MCP server serves Codex CLI, including Codex CLI/app-server use from Desktop "
                "and local Work. "
                "Worker-bound embedding exposes public tools and this Worker's own assignment, "
                "state, progress, evidence, blocker, and recovery operations. Start with "
                "worker_get_assignment "
                "and worker_get_recovery_context. No parent operations are exposed. Writes require "
                "current revision/idempotency data; discovery grants no authority."
            )
        return (
            "This MCP server serves Codex CLI, including Codex CLI/app-server use from Desktop "
            "and local Work. "
            "This public-only server exposes capabilities, rules, and schema diagnostics. "
            "Start with workflow_capabilities and rules_get_context. Protected "
            "operations are unavailable; a "
            "listed or public tool does not create a trusted host binding or grant authority."
        )
    try:
        return (
            "This MCP server serves Codex CLI, including Codex CLI/app-server use from Desktop "
            "and local Work. " + SERVER_INSTRUCTIONS[profile]
        )
    except KeyError as exc:
        raise ValueError(f"missing Agent-facing instructions for MCP profile: {profile}") from exc

"""Agent-facing MCP descriptions for every exposed wire tool."""

from __future__ import annotations

STANDARD_INSTALL_NOTICE = (
    "The fixed local Codex stdio executables use threadId/sessionId request metadata and existing "
    "allocations for application scope. The workflow executable exposes 17 workflow tools; the "
    "aggregate tools executable exposes 51 parent, Worker, shared-state, and development tools. "
    "No privileged host service or external identity provider is required. This is not independent "
    "process authentication or OS isolation. Discovery does not grant authority; state calls still "
    "check roles, paths, and explicit operation authorization."
)

SERVER_DESCRIPTION = (
    "MCP server for a locally available Codex CLI, including local Work when it uses the local "
    "Codex CLI/app-server path. Cloud ChatGPT conversations, remote Work, and other Code Agents "
    "are not direct clients. If another Agent installs and configures Codex CLI in its own "
    "environment, only that local CLI path is supported; no other Agent or cloud adapter is "
    "provided. No runtime-environment selection step is exposed. Bounded Token I/O tools. The "
    "workflow and aggregate tools executables expose fixed inventories. Current bound roles and "
    "operation guards determine which calls may proceed. Discovery reports availability, not "
    "identity or authority."
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
_PROXY_DESCRIPTION = (
    "OpenAI API requests use an HTTPX2 client with trust_env=True, reading HTTP_PROXY, "
    "HTTPS_PROXY, ALL_PROXY and NO_PROXY (including lowercase forms) from the MCP process "
    "environment. NO_PROXY may bypass the proxy; without proxy configuration the client uses "
    "its normal direct route. Invalid or unreachable proxies fail through existing safe API "
    "error results without a direct-connection retry. Forward these variable names through "
    "Codex env_vars and restart the server after changes; values are never tool arguments."
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
    "serena_memory_tail_read",
    "serena_memory_write_check",
    "workflow_capabilities",
    "rules_get_context",
    "validate_decoupling_compliance",
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
    "decide_decoupling_workflow",
    "workflow_select_child_role",
    "workflow_select_executor",
    "workflow_select_child",
    "workflow_assess_output_tokens",
}

TOOL_DESCRIPTIONS: dict[str, str] = {
    "serena_memory_tail_read": _description(
        "Read the last N logical lines from a local project Memory file. Two direct arguments, "
        "no payload envelope: memory_path is a project-relative name under .serena/memories, "
        "with optional mem: prefix and .md suffix. Absolute, global, and external paths are "
        "rejected. "
        "tail_lines is a strict integer 0..10000; zero returns only line-count metadata. "
        "The returned content is bounded to 64000 characters; oversized windows fail rather than "
        "silently truncate. Returns status/reason, canonical Memory/path identity, total_lines, "
        "returned_lines and the selected line range/content on success. Files are opened as "
        "UTF-8; symlinks and paths outside the local Memory folder are rejected. "
        "Project scope is fixed to the workflow server's actual startup directory. The tool "
        "reads only files under that directory's .serena/memories folder, with no parent/"
        "sibling/project discovery and no installation-time project binding. It uses Python "
        "standard-library file operations only; it does not require Serena-Agent or another "
        "local program. Missing folders or files return unavailable. Rejects "
        "traversal, symlinks, non-regular files, out-of-root targets, and oversized tail windows. "
        "No files/directories, state, models or API requests are written or invoked. "
        "Missing files return unavailable. No files or directories are created, and no "
        "revision/idempotency key is used.",
    ),
    "serena_memory_write_check": _description(
        "Quick read-only literal containment check of expected text in a Serena Memory tail. "
        "Three direct arguments, no payload envelope: memory_path follows serena_memory_tail_read; "
        "changed_content is nonempty text of at most 64000 characters; tail_lines is a strict "
        "integer 0..10000. Invokes the same local tail-read implementation exactly once and "
        "matches changed_content literally against its returned content, without regex or text "
        "normalization. Returns a compact success flag/reason and selected-window evidence; "
        "does not echo the expected text or full tail. A match only proves the text is currently "
        "present in that window: pre-existing text may match, and a valid edit outside the "
        "window may not. It does not prove a recent write occurred, preservation, semantic "
        "correctness, append-only history or concurrency/CAS safety, and cannot replace required "
        "full-content acceptance or archive comparisons. Same startup-directory scope, path "
        "checks, UTF-8 encoding, and tail limits as tail read. No write, model/API request; "
        "no revision/idempotency key. Treat unavailable/error as unverified; investigate or use "
        "an appropriately sized authorized window without claiming the write itself failed.",
    ),
    "workflow_capabilities": _description(
        "Read public capability summaries and capability_details (schema_version=2). No arguments;",
        "support.local_stdio describes local request scoping and its limits;",
        "configuration.public_interfaces describes independent public-tool dependencies.",
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
        "At most one provider read; no adapter-state inspection, mutation, or API request. Probes",
        "may use the host channel. An absent task-plan service triggers no Git or Memory-path",
        "probe. A configured global plan service may revalidate its local Git common-dir identity",
        "and already-bound global root without creating paths. No credential or identity values,",
        "or raw errors are returned.",
        "On missing provider, guard failure, denial, or probe failure, inspect reason_code",
        "and next_step; use a fixed local stdio executable with valid request metadata.",
        "A known transport or",
        "verified",
        "baseline does not verify caller metadata or operation-specific guards, enable Enhanced,",
        "change startup admission, or grant authority. No revision or idempotency key is required.",
    ),
    "task_plan_update": _description(
        "Append structured records to one task plan in the configured Serena Memory namespace.",
        "The trusted task-plan factory binds storage_scope to project (default) or global; callers",
        "cannot choose storage_scope or repository_id in a request. Payload: request.project_root",
        "(absolute path and exact configured checkout match),",
        "plan_id (lower-case slug), expected_revision (current SHA-256, or JSON null only when",
        "creating an absent plan), request_id (stable operation ID), and records (1-100 immutable",
        "record_id/kind/text/sources entries). Kinds include goal, criterion, verification,",
        "blocker,",
        "resolution, result, limitation, constraint, requirement, fact, decision, and progress;",
        "verification requires outcome passed/failed/assumed/unavailable. Superseding a record",
        "requires its active ID and a reason; a resolution references an existing blocker.",
        "Returns a compact receipt with scope, revision, state, changed IDs,",
        "preservation, readback,",
        "replay, and reconciliation status; never returns plan text. The service validates",
        "history,",
        "uses a POSIX advisory lock, expected SHA, atomic same-directory write,",
        "and exact readback.",
        "Project scope retains its v1 history. Global scope maps to",
        "global/token-io-decoupling/repos/<repository_id>/plans/PLAN-<plan_id>; repository_id is",
        "derived locally from the verified Git common directory, and shared history uses v2.",
        "The receipt project_root remains the current checkout.",
        "Requires trusted operator startup configuration (--task-plan-factory MODULE:CALLABLE);",
        "default is unavailable with no path/config/import side effects.",
        "Makes no model/API request.",
        "Raw Serena writers can bypass this tool's lock and revision checks;",
        "no global ACL is claimed.",
        "Stale SHA, conflicting operation ID, invalid history/policy/path, unsupported lock, or",
        "readback failure returns a bounded reason and current revision when known;",
        "reconcile uncertain writes.",
    ),
    "task_plan_complete": _description(
        "Append final results and limitations and mark one task plan completed.",
        "The trusted task-plan factory binds storage_scope to project (default) or global; callers",
        "cannot choose storage_scope or repository_id in a request. Payload: request.project_root",
        "(absolute path and exact configured checkout match),",
        "plan_id,",
        "expected_revision (current SHA-256), request_id (stable operation ID), criterion_evidence",
        "(exactly one mapping per active criterion to an active verification record), and 1-100",
        "result/limitation records. Completion requires at least one active criterion, a passed",
        "verification for every criterion, and no unresolved blocker; missing, failed, assumed, or",
        "unavailable evidence is rejected. Resolve blockers with a typed resolution record first.",
        "Completion is terminal; later updates are rejected and an identical completion operation",
        "replays without another write. The receipt is compact and reports",
        "revision/readback state;",
        "it does not assert that caller-supplied evidence is semantically true or sufficient.",
        "Global scope shares v2 history by a repository_id derived locally from the verified Git",
        "common directory; the receipt project_root remains the current checkout.",
        "Requires the explicit trusted task-plan factory and configured Serena MemoryManager; the",
        "default is unavailable. Uses no model/API request. Raw Serena writes can bypass its lock.",
        "Conflicts, invalid evidence/history/policy/path, and uncertain writes",
        "return bounded reasons.",
    ),
    "task_plan_archive": _description(
        "Move one completed task plan to its fixed archive namespace without overwriting.",
        "The trusted task-plan factory binds storage_scope to project (default) or global; callers",
        "cannot choose storage_scope or repository_id in a request. Payload: request.project_root",
        "(absolute path and exact configured checkout match),",
        "plan_id,",
        "and expected_revision (SHA-256 of the completed plan). In project scope, the tool maps",
        "plans/PLAN-<id> to archive-plans/PLAN-<id>; in global scope, both names are fixed inside",
        "the configured repository namespace. Callers cannot choose source or destination. It adds",
        "no event or",
        "request ID. A POSIX advisory lock and atomic no-clobber hard link precede source removal;",
        "existing destinations are never modified. A source-absent replay succeeds only when the",
        "archived bytes match the expected revision and the full completed",
        "history/identity parses.",
        "Global scope maps the archive to",
        "global/token-io-decoupling/repos/<repository_id>/archive-plans/PLAN-<id> with the same",
        "locally derived identity as its active plan.",
        "Returns a compact scoped receipt. Requires trusted operator startup configuration;",
        "default is unavailable and makes no model/API request.",
        "Raw Serena writers can bypass the lock.",
        "Incomplete plans, stale revisions, collisions, symlinks, policy denial, or unsupported",
        "filesystem primitives fail closed; interruptions return uncertain/reconciliation status.",
    ),
    "rules_get_context": _description(
        "Load a checkpoint's legacy owner context or an explicit version-1",
        "indexed fragment bundle.",
        "Legacy payload: node_id (registered checkpoint enum) and language",
        "(en by default; en or zh_cn).",
        "When context_version and all extension fields are omitted, return the unchanged legacy",
        "RuleContext fields, owner text, and context hash. fragment_ids and max_chars require",
        "context_version=1; unknown fields and unsupported versions fail validation.",
        "Version 1 starts with the node's indexed default fragments, adds any",
        "explicit fragment_ids,",
        "and resolves only the index's declared dependency edges in deterministic order.",
        "The response contains bounded node metadata and whole text fragments;",
        "node metadata is not",
        "charged to max_chars. max_chars counts Unicode characters",
        "in fragment text only, defaults",
        "to 12000, and is limited to 256..60000. No fragment is truncated.",
        "index_sha256 binds the canonical versioned index; context_hash binds it",
        "with node metadata, returned fragment text/hashes, the budget result, and",
        "the remaining-owner-reference report.",
        "complete=true means every requested fragment in the explicit index closure was loaded; it",
        "does not mean the task's other direct owners or linked documents have been read.",
        "remaining_owner_refs is a bounded list of local Markdown links found in",
        "returned fragments whose target section is not in the returned closure;",
        "it marks references to read separately,",
        "not rules already included. The list is capped at 16 with a truncation flag.",
        "Budget omissions and missing owner files/headings appear in missing_fragments with",
        "complete=false and an incomplete status. Invalid paths/symlinks, unknown IDs, duplicate",
        "index IDs, dependency cycles, and duplicate real headings fail closed.",
        "owner_path is repository-relative source provenance under docs/skill, not",
        "an installed Skill",
        "file path. Installed servers use their packaged versioned index and normalized fragments;",
        "fragment hashes cover the same trimmed text returned by either source.",
    ),
    "validate_decoupling_compliance": _description(
        "Run a bounded, read-only preflight over a candidate document overlay before an "
        "authorized write.",
        _PAYLOAD,
        "Payload envelope: request.policy_scope is skill_maintenance or generic_project; "
        "request.candidates has 1-64 unique entries. Each entry has a canonical "
        "repository-relative POSIX path (at most 512 characters), operation=create/replace/delete, "
        "baseline={state:absent} for create or {state:sha256,value:<64 lowercase hex>} for "
        "replace/delete, and content for create/replace. A file is limited to 131072 Unicode "
        "characters and the whole batch to 524288 UTF-8 bytes.",
        "The trusted CompliancePreflightService root and allowed policy scopes are fixed by "
        "operator startup code loaded only through --compliance-factory MODULE:CALLABLE. Payload "
        "and current working directory cannot choose a root. Without a configured reader, the "
        "tool performs no path probe and disk/baseline evidence is unknown. A disallowed scope "
        "is not evaluated.",
        "For skill_maintenance, checks cover the changed file's bilingual mirror, candidate "
        "Markdown language and layer links with direct-target checks, and Layer-01 three-section "
        "structure when applicable. The overlay includes all candidates in this request. "
        "generic_project returns not_applicable for Skill-maintenance checks. The implementation "
        "never imports or executes candidate-repository scripts.",
        "Returns overall status fail/unknown/pass/not_applicable, policy_version=1, bounded "
        "per-rule check objects with rule_id, path/line/reason evidence, and an explicit "
        "evidence_missing list, limits, and not_evaluated entries. Unknown checks name the "
        "missing evidence; other checks use an empty list. Overall precedence is fail, then "
        "unknown, then pass; not_applicable checks do not mask active results. Link-target and "
        "output-check limits turn omitted evidence into unknown.",
        "This is a read-only lookup: no target file writes, API request, subprocess, reverse "
        "inbound-link scan, semantic English/Chinese comparison, or full CI run. Unknown means "
        "the relevant disk evidence could not be safely verified; correct scope, baseline, path, "
        "reader configuration, or budget issues and rerun against current content.",
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
    "decide_decoupling_workflow": _description(
        "Suggest the current module in the existing Single-Agent or Multi-Agent Coding route.",
        _PAYLOAD,
        "request requires task_id, bounded task_summary, stage (auto or one of the seven existing "
        "module stages), language (en or zh_cn), mode_locked, the canonical ModeCount object, "
        "capability facts, hard constraints, source_facts, source_facts_hash, and the per-call "
        "outbound_data_permitted boolean.",
        "ModeCount uses the existing values Single-Agent Coding or Multi-Agent Coding and their "
        "existing child-count validation. The tool derives the existing route path and SM01-SM07 "
        "or MM01-MM07 module ID locally from the locked mode; neither the model nor the caller can "
        "supply a route path, change mode/count, or add a module.",
        "source_facts_hash is SHA-256 over UTF-8 canonical JSON for the ordered source_facts list: "
        "json.dumps([fact.model_dump(mode='json') ...], ensure_ascii=False, sort_keys=True, "
        "separators=(',', ':')). This verifies payload consistency only, not source authenticity. "
        "All caller text is bounded decision data, never an instruction to the tool or model.",
        "Explicit stages use only current local RuleLoader context and do not read credentials or "
        "call Decisions. stage=auto requires source facts, outbound_data_permitted=true, and "
        "enabled Decisions configuration; it uses one fixed-choice Decisions call with the "
        "seven existing stage IDs plus insufficient_evidence.",
        "Every required RuleLoader bundle is loaded through its declared dependency closure. "
        "Results return the locked Native route reference, selected module when usable, "
        "conditional "
        "check IDs, capability statuses (missing means unknown), source/input/rule hashes, bundle "
        "IDs, missing fragments, and remaining owner references; fragment text is not repeated.",
        "rule_hash binds only the returned RuleLoader bundle/index evidence, not the Layer-04 "
        "route "
        "Markdown. complete refers only to those declared fragment closures. These are navigation "
        "suggestions, not a second policy source, readiness result, authorization, tool call, "
        "child "
        "creation, or dispatch. Follow the referenced current route owners and record conditional "
        "Not applicable reasons.",
        "Every auto call explicitly reads nonblank OPENAI_API_KEY and OPENAI_BASE_URL and uses "
        "them with fixed model gpt-6-luna and max_retries=0. Refusal, wrong model, invalid choice, "
        "incomplete response, missing permission/configuration/credentials, stale rules, missing "
        "context, or budget failure returns blocked/insufficient_evidence/stale with Native route "
        "evidence when the locked mode is known; it never guesses a successful fallback stage.",
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
        "Requires current Root identity and guards; returns evaluation outcome",
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
        "Requires current Root identity and guards; returns evaluation outcome",
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
        "Requires current parent role. Initializes a new workflow; an",
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
        "Supply expected_revision and idempotency_key. Requires current Root",
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
        "Requires current parent identity and host verification of the",
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
        "Requires current Root binding, workflow-write capability, and identity/session/path",
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
        "Requires current parent role; this check does not release or mutate",
        "a slice. Returns SliceCheckResult (eligible, reason, allocation_id,",
        "output_class, input_hash); resolve findings before slice_release.",
    ),
    "slice_release": _description(
        "Persist/release an eligible bounded slice for an allocation.",
        _PAYLOAD,
        "Supply spec, expected_revision, and idempotency_key.",
        "Requires current parent role, release guards, and valid allocation.",
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
        "Requires current parent role and transition guards; returns",
        "MutationReceipt with typed result and revisions. Transitions can",
        "change Control or epoch state.",
        _RECEIPT,
        _RETRY,
    ),
    "parent_get_worker_summary": _description(
        "Read the summary for one parent-owned allocation.",
        "Payload: allocation_id. Requires current parent role.",
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
        "Requires current parent role; returns ReconcileResult status",
        "matched/conflict/awaiting_confirmation, differences,",
        "observed/result/current revisions, and native_refs. Review conflicts",
        "and state before confirming.",
        _RETRY,
    ),
    "worker_get_assignment": _description(
        "Read the calling Worker's current assignment.",
        "No arguments. Requires registered Worker binding and valid assignment guards.",
        "Returns assignment/allocation identity, role, output class, assigned",
        "slice boundary, and current revision; unavailable assignment or",
        "revoked binding fails closed. This grants no permission outside it.",
    ),
    "materialize_decoupled_output": _description(
        "Prepare, inspect, or apply a bounded file output for the calling Worker.",
        (
            "Input envelope: payload.request.action is prepare, inspect, or apply. Prepare accepts "
            "1–16 files; each has an exact normalized repo-relative leaf path, create/replace "
            "operation, absent or SHA-256 baseline, and one finite template: literal_text, "
            "json_document supplied as strict bounded JSON text, or fact_markdown containing at "
            "most 8 headings and 64 source facts. Inspect requires prepared_id, "
            "expected_manifest_hash, file_index, offset, and max_chars (default 2048, maximum "
            "8192). Apply accepts only prepared_id and expected_manifest_hash; it never "
            "regenerates content or calls an API."
        ),
        (
            "Requires a currently registered Worker binding and confirmed assignment, the fixed "
            "Primary Output assignment with code_configuration or skill_instructions output, "
            "and a separate active operator grant matching "
            "project/root/Worker/allocation/role/class/Slice/assignment hash, pinned roots, exact "
            "paths, operations, templates, policy, and revision. Recheck occurs for every action "
            "and before each file write. Payloads cannot select roots, role, grant, or authority. "
            "A Native coding-task role or an Agent Session's Primary Output label is not a "
            "verified MCP Worker binding. State-store guards do not grant project-file write "
            "permission."
        ),
        (
            "Without an explicitly loaded --output-materializer-factory, trusted grant, secure "
            "configured roots, or the same configured 185 preflight root, the operation is "
            "unavailable and probes no default paths. Apply requires a fresh whole-batch 185 "
            "result with policy_version=1 and status=pass. Responses ordering is optional, "
            "requires the independent grant plus outbound_data_permitted=true on prepare, reads "
            "both nonblank process environment values, sends at most 48,000 characters across "
            "fixed instructions and serialized fact input (excluding fixed schema/framing), uses "
            "only gpt-6-luna with zero retries, and returns only orderings of supplied fact IDs; "
            "local code renders the original facts."
        ),
        (
            "Prepare writes immutable candidates and a manifest only inside the configured "
            "artifact root, returning an opaque ID, hash, sizes, bounded previews, and inspect "
            "instructions. Inspect reads one bounded artifact slice. Apply rechecks exact "
            "baselines and atomically publishes each file with no-clobber create or verified "
            "replace; missing parent directories are not created. Results distinguish applied, "
            "already_identical, conflict, not_attempted, uncertain, and partial. Same-service "
            "cooperative locking does not stop external writers; multiple files are not an "
            "atomic set and are not automatically rolled back."
        ),
    ),
    "worker_record_progress": _description(
        "Record progress for the calling Worker's own assignment.",
        _PAYLOAD,
        "Supply record.status (started, in_progress, or reported_complete),",
        "record.milestone (SemanticRef {uri, content_hash}) and",
        "record.references, plus expected_revision and idempotency_key.",
        "reported_complete records the Worker's report; it is not parent",
        "acceptance.",
        "Requires registered Worker identity and own-store guards; returns",
        "MutationReceipt operation, payload_hash, result, receipt_revision,",
        "current_revision, and replayed. Reread assignment/state after",
        "conflict.",
        _RETRY,
    ),
    "worker_get_evidence": _description(
        "Read evidence by identifier.",
        "Payload: evidence_id. Requires registered Worker identity and own-store guards.",
        "Returns matching evidence facts, references, coverage, hashes,",
        "revisions, and stale status visible to that Worker; missing or",
        "out-of-scope identifiers fail closed.",
    ),
    "worker_report_blocker": _description(
        "Record a blocker for the calling Worker's own assignment.",
        _PAYLOAD,
        "Supply blocker.blocker_id, blocker.reason (SemanticRef uri/content_hash),",
        "blocker.references, expected_revision, and idempotency_key.",
        "Requires registered Worker identity and own-store guards; returns",
        "MutationReceipt operation, payload_hash, result, receipt_revision,",
        "current_revision, and replayed. Reread assignment and state after",
        "conflict.",
        _RETRY,
    ),
    "worker_get_recovery_context": _description(
        "Read the calling Worker's recovery context; no arguments.",
        "Requires registered Worker binding and own-store guards.",
        "Returns exactly assignment (worker_get_assignment result) and state",
        "(worker_get_state JSON). Use those current objects to resume; this",
        "tool generates no recovery plan and cannot bypass guards.",
    ),
    "database_schema_status": _description(
        "Read the database schema diagnostic.",
        "No arguments; public and does not inspect caller-selected paths.",
        "Returns schema status, including an unavailable diagnostic when no",
        "local session scope exists. Use before state operations to understand",
        "compatibility.",
    ),
    "state_get": _description(
        "Read state for the current role.",
        "Payload may include index_page (collection, optional cursor,",
        "page_size 1–128) for parent pagination; Workers must omit it.",
        "Requires local session scope and state-read guards; returns role-scoped",
        "state, revision, and pagination metadata. A stale or invalid cursor",
        "requires restarting from the first page.",
    ),
    "record_evidence": _description(
        "Record evidence in the current role's authorized store.",
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
        "not exposed by either standard local server.",
        "Payload may include index_page for pagination; requires current parent binding.",
        "Returns parent-scoped state. Restart pagination after cursor errors.",
    ),
    "workflow_record_evidence": _description(
        "Compatibility embedding alias for parent evidence submission; not",
        "not exposed by either standard local server.",
        _PAYLOAD,
        "submission has node_id, nonempty fact_key/judgment facts, optional",
        "evidence_refs/coverage_dimensions, input_hash, and optional",
        "evidence_request_id; include expected_revision/idempotency_key.",
        "Requires current parent identity and evidence-write guards.",
        "submission uses node_id, facts, evidence_refs, coverage_dimensions,",
        "input_hash, and optional evidence_request_id. Returns MutationReceipt",
        "with operation, payload_hash, result, receipt_revision, current_revision,",
        "and replayed; evidence is not a decision.",
        _RETRY,
    ),
    "worker_get_state": _description(
        "Compatibility embedding alias for the calling Worker's own state",
        "read; not exposed by either standard local server.",
        "No arguments; requires registered Worker binding and own-store guards.",
        "Returns only role-scoped state; cross-Worker reads fail closed.",
    ),
    "worker_record_evidence": _description(
        "Compatibility embedding alias for the calling Worker's evidence",
        "submission; not exposed by either standard local server.",
        _PAYLOAD,
        "submission has node_id, nonempty fact_key/judgment facts, optional",
        "evidence_refs/coverage_dimensions, input_hash, and optional",
        "evidence_request_id; include expected_revision/idempotency_key.",
        "Requires registered Worker identity and own-store evidence guards.",
        "submission uses node_id, facts, evidence_refs, coverage_dimensions,",
        "input_hash, and optional evidence_request_id. Returns MutationReceipt",
        "with operation, payload_hash, result, receipt_revision, current_revision,",
        "and replayed.",
        _RETRY,
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
        elif name in {"task_plan_update", "task_plan_complete", "task_plan_archive"}:
            if name == "task_plan_archive":
                recovery = (
                    "Recovery class: task-plan archive mutation. On unknown completion, inspect "
                    "the task plan, fixed archive target, receipt, and readback first. "
                    "This archive "
                    "has no request ID; retry only the same completed revision to the same fixed "
                    "archive target. If the source is absent, treat it as replay success "
                    "only after "
                    "archived bytes match the expected revision and completed history/identity "
                    "validate. On revision conflict, refresh and review the completed plan; "
                    "reconcile active/archive state before considering a retry. Never blindly "
                    "resubmit or overwrite. This operation makes no model/API request and is not a "
                    "stateless API retry."
                )
            else:
                recovery = (
                    "Recovery class: task-plan mutation. On unknown completion, first read back "
                    "the task plan and inspect its receipt/reconciliation status. Replay only the "
                    "same logical update/complete request with its stable request_id, unchanged "
                    "expected_revision, and identical records/criterion evidence. On revision "
                    "conflict, refresh the current plan and revision, review the change, and "
                    "form a new request only if the changed content is still authorized and "
                    "intended; use a new request_id and the current reviewed revision as "
                    "expected_revision. Reconcile by checking the "
                    "plan, receipt, and readback first; never blindly resubmit. "
                    "These tools make no "
                    "model/API request and are not stateless API retries."
                )
        elif name == "materialize_decoupled_output":
            recovery = (
                "Recovery class: prepared output materialization. On an uncertain prepare, do not "
                "blindly prepare again; retain the returned opaque identity/hash when available "
                "and reconcile the configured artifact receipt. For inspect, repeat only the same "
                "bounded read after verifying the current grant and manifest hash. For an "
                "uncertain "
                "apply, inspect the same prepared ID/hash and read current target hashes before "
                "considering a repeat. A repeat must use the same prepared ID and manifest hash; "
                "the tool never regenerates content during apply. Conflict, revocation, changed "
                "assignment/grant, unknown preflight, or unsafe path is not transient and must be "
                "resolved before a new prepare. Partial application is reported per file; do not "
                "assume rollback or retry files reported uncertain without readback. This tool may "
                "write the explicitly configured artifact store during prepare and project files "
                "during apply; it is not a stateless API retry."
            )
        else:
            raise ValueError(f"missing recovery classification for MCP tool: {name}")
        result = (
            "Codex CLI MCP tool, including Codex CLI/app-server use from Desktop and local Work. "
            + description
            + " "
            + recovery
        )
        if name in _STATELESS_API_TOOLS | _STATE_ADVICE_TOOLS | {"materialize_decoupled_output"}:
            result += " " + _PROXY_DESCRIPTION
        return result
    except KeyError as exc:
        raise ValueError(f"missing Agent-facing metadata for MCP tool: {name}") from exc


def workflow_server_description() -> str:
    return (
        "Codex CLI MCP server for workflow capabilities, task plans, rules, decision support, "
        "and compliance tools. State calls require the current local session scope and "
        "operation authorization. Discovery does not authenticate a caller. "
        + STANDARD_INSTALL_NOTICE
    )


def tools_server_description() -> str:
    return (
        "Codex CLI MCP server for aggregated parent, worker, shared state/evidence, and "
        "development workflow tools. Each operation retains its own role, path, and "
        "authorization checks. Discovery does not authenticate a caller. " + STANDARD_INSTALL_NOTICE
    )


def workflow_server_instructions() -> str:
    return (
        "This server exposes workflow capabilities, task-plan, rule, decision-support, and "
        "compliance tools. Start with workflow_capabilities and rules_get_context. Each "
        "operation follows its published scope and authorization checks. Discovery grants no "
        "authority. " + STANDARD_INSTALL_NOTICE
    )


def tools_server_instructions() -> str:
    return (
        "Local Codex CLI aggregate tools server. Workflow capabilities and rules remain on "
        "token-io-decoupling-workflow. Begin state diagnostics with database_schema_status; "
        "Root starts with workflow_open, Workers with worker_get_assignment. Root and Worker "
        "tools are discoverable together, with role checks on every call. Shared state and "
        "evidence operations route by the current bound role; Worker reads cannot paginate "
        "Root state. Mutations require current revisions, idempotency keys, and independent "
        "authorization. Materialization remains Worker-only and requires its configured "
        "service, operator grant, pinned root, and current preflight. Discovery grants no "
        "authority. " + STANDARD_INSTALL_NOTICE
    )

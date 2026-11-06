"""Agent-facing MCP descriptions for every exposed wire tool."""

from __future__ import annotations

from token_io_decoupling_transport.tool_metadata import STANDARD_INSTALL_NOTICE


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
    "fact revision/fingerprint with the exact current caller facts, reviewed context, and compiled "
    "policy identity. On stale, refresh current facts and compiled policy, "
    "regenerate/review context if needed, "
    "and obtain a new result; never reuse it or convert it to fallback. A Decisions request "
    "requires per-call outbound_data_permitted=true plus nonblank OPENAI_API_KEY and "
    "OPENAI_BASE_URL; the tool reads and explicitly uses both with fixed model gpt-6-luna, "
    "without caller endpoint/model overrides or automatic retries. These advisory results do "
    "not reserve, create, bind, dispatch, or authorize a child or Root execution; recheck current "
    "mode, permissions, budget, role uniqueness, scope, and availability before an action."
)

TOOL_DESCRIPTIONS: dict[str, str] = {
    "workflow_capabilities": _description(
        "Read workflow-local capability_details (schema_version=3), support, optional API "
        "configuration and safe binding diagnostics. No arguments, mutation or API request. "
        "At most one provider read; no plan, Memory, preflight or tools-service probe. "
        "Static rule and checkpoint calls require no database or caller binding. "
        "Diagnostics do not authenticate facts, authorize effects, persist workflow state "
        "or establish completion. Check complete compiled instructions when choosing this workflow."
    ),
    "rules_get_context": _description(
        "Return a checkpoint's complete compiled instruction bundle, without source-file lookups.",
        "Payload: node_id (registered checkpoint enum), language (en default or zh_cn),",
        "context_version (integer 2, the default), optional fragment_ids and max_chars.",
        "Version 1 is retired and rejected; old context hashes are invalid after "
        "this schema/build change.",
        "Each returned unit already contains its compiler-verified execution dependencies.",
        "Omitted or empty fragment_ids return the complete default node. Nonempty fragment_ids "
        "return only those complete compiled units, without repeating the default node; "
        "the runtime never interprets Markdown.",
        "max_chars counts returned instruction-text Unicode characters only, defaults to 12000,",
        "and is limited to 256..60000. When the whole result exceeds it, complete=false,",
        "status=incomplete_budget and fragments is empty: review diagnostics, "
        "then request a sufficient supported budget.",
        "Never execute an incomplete result or repair it by reading original owners.",
        "Missing, corrupt, mixed-build or incompatible resources fail clearly "
        "without source fallback.",
        "A complete result supplies executable text, required facts/evidence, legal branches, "
        "failure handling and next checkpoint IDs.",
        "Verify current facts, capabilities and authorization separately.",
        "owner_path/owner_section are compatibility fields containing compiled instruction "
        "IDs/titles, not paths to read.",
        "remaining_owner_refs is retained empty. build_id binds the compilation batch; "
        "context_hash identifies full node/selected-unit text and metadata "
        "independently of budget.",
        "Use the default node bundle's context_hash for checkpoint/semantic expected_rule_hash;",
        "hashes for explicit fragment selections identify a different selection. "
        "No API call or mutation.",
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
        "This stateless operation has no caller binding, revision, or idempotency key.",
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
        "credentials. No caller binding, persisted state, automatic downstream Decisions call,",
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
        "Every required RuleLoader bundle contains its compiler-expanded execution closure. "
        "Results return the locked Native route reference, selected module when usable, "
        "conditional "
        "check IDs, capability statuses (missing means unknown), source/input/rule hashes, bundle "
        "IDs and missing fragments. An available result also returns instructions containing the "
        "selected stage's executable text, build identity, module and continuation. "
        "shared_requirements gives exact rules_get_context payloads and text hashes for common "
        "hard constraints (required before any action) and the prerequisite return map "
        "(required when prerequisites are missing). Fetch and apply each triggered unit first; "
        "reuse only an exact held unit from this build with the matching hash. Missing or "
        "mismatched content blocks the dependent action. Explicit fragment selection returns "
        "only those units, avoiding repeated default-node prose.",
        "Compiled route IDs are identifiers rather than files to read. Resources must belong to "
        "the same approved build; corrupt, missing or mixed-build resources block execution. "
        "These are suggestions, not readiness, authorization, child creation or dispatch. "
        "Follow returned instructions under current capability and permission checks, recording "
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
        "The tool loads compiled child-role-selection and session-role-ownership policy resources",
        "without author-document access and returns policy/request hashes, a role suggestion",
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
        "Stateless structural checkpoint check. Payload has node_id, submission, optional "
        "language (en or zh_cn, default en), optional expected_rule_hash, optional node-matched "
        "semantic_input, and current_facts. expected_rule_hash must be the full registered-node "
        "default version-2 rules_get_context bundle for that language; extra-fragment selections "
        "bundle hashes and index_sha256 are different values and are rejected as stale. Submission "
        "facts contain 1–128 unique typed fact keys; top-level evidence references are limited to "
        "128, coverage dimensions to 3, evidence references per determined fact to 16, and named "
        "missing-evidence items to 16. Checkpoint reference URIs are at most 512 characters; "
        "evidence IDs and evidence_request_id are at most 128 characters. The canonical UTF-8 "
        "serialized submission is limited to 32 KiB. input_hash is optional; when present, it is "
        "a consistency assertion. The server normalizes submission.model_dump(mode='json', "
        "exclude={'input_hash'}), serializes with json.dumps(ensure_ascii=False, sort_keys=True, "
        "separators=(',', ':')), encodes as UTF-8, then computes SHA-256. The server always "
        "returns "
        "the computed source_input_hash. A supplied mismatch or stale expected_rule_hash returns "
        "blocked_input. The full evaluation request, including semantic_input and current_facts, "
        "is limited to 32 KiB of canonical UTF-8 JSON; oversize or invalid input is rejected, "
        "never truncated. current_facts is a flat map of at most 16 string pairs with keys of "
        "1–64 and values of 1–1,024 characters; blank strings and nested/non-string values are "
        "invalid. Returns ready_for_agent_review, incomplete_for_agent_review, or blocked_input "
        "with missing requirements, reason, source_input_hash, and current rule_hash. Optional "
        "Decisions advice may issue one configured API request; it is separate and never changes "
        "the structural result or authorizes execution. Facts are not authenticated; no workflow "
        "state is persisted or cross-call sequencing enforced."
    ),
    "evaluate_control_checkpoint": _description(
        "Stateless structural check for the Control checkpoint. Payload has submission, optional "
        "language (en or zh_cn, default en), optional expected_rule_hash, optional Control "
        "semantic_input, "
        "and current_facts. expected_rule_hash must be the full Control rules_get_context result "
        "from the default version-2 bundle for that language; extra-fragment bundle hashes and "
        "index_sha256 are distinct and rejected as stale. It uses the same "
        "1–128 facts, 128 top-level evidence references, 3 coverage dimensions, 16 nested "
        "evidence references, 16 missing-evidence items, 512-character URI, and 128-character "
        "ID/request-ID limits as workflow_evaluate. Canonical submission and full request budgets "
        "are each 32 KiB UTF-8 JSON. input_hash is optional; when supplied it must match the "
        "server-computed SHA-256 of normalized submission JSON excluding input_hash, using "
        "ensure_ascii=False, sort_keys=True, and separators=(',', ':'). expected_rule_hash is an "
        "independent staleness assertion. current_facts is a flat map of at most 16 string pairs, "
        "with 1–64 character keys and 1–1,024 character values. Oversize, blank, nested, or "
        "non-string facts are rejected without truncation. Returns ready_for_agent_review, "
        "incomplete_for_agent_review, or blocked_input with the selected Control branch when "
        "present, missing requirements, source_input_hash, and current rule_hash. Optional "
        "Decisions advice may issue one configured API request and never authorizes a transition; "
        "the structural result does not authenticate facts, persist state, or sequence calls."
    ),
}


def tool_description(name: str) -> str:
    description = TOOL_DESCRIPTIONS[name]
    return "Codex CLI MCP tool. " + description


def workflow_server_description() -> str:
    return (
        "Independent local Codex CLI server for compiled rules, navigation "
        "and structural evaluation."
    )


def workflow_server_instructions() -> str:
    return (
        "These instructions apply when the caller chooses this workflow. "
        "Call workflow_capabilities, then rules_get_context with node_id=contract "
        "and context_version=2. "
        "Read complete returned instructions; compiled IDs are not source paths. "
        "Structural checks do not authenticate facts, authorize effects "
        "or persist checkpoint state. "
        "Other tools can be used independently of this workflow. " + STANDARD_INSTALL_NOTICE
    )

# Decisions Advisory

[English](decisions-advisory.md) | [简体中文](decisions-advisory_zh_cn.md)

This module owns the optional handling of bounded semantic advice for five fixed registered nodes. It does not own their policies, choose or confirm a Core branch, authorize work, release a Slice, determine Verification, or accept the task.

## General rules

### Keep advice separate from judgment and authority

The supported nodes are `task_intent`, `output_class`, `contract_change`, `verification_impact`, and `control`, using only each node's current registered legal choices and required fact shape. Validate that a response contains exactly one answer with the requested node name and type, and that its value is one of that node's current legal choices; otherwise discard it and use direct judgment. Do not infer correctness from a confidence score or invent a confidence threshold. The mapped owner remains authoritative. Advice is a separate input for the Agent to consider; the Agent must review the direct owner, validate hard constraints, and make the actual judgment. Never replace a Core branch with an API answer or use advice to authorize mode, count, allocation, creation, dispatch, Slice release, a Control transition, verification success, or Acceptance.

An advisory request may be made only after the caller has independently verified that outbound data sharing is permitted. Supply only the bounded facts needed for the selected question and the current owner context. Caller-supplied identity, permission, source, revision, or approval assertions are not proof. Mode and count remain locked; advice cannot reopen them.

Send only the typed facts required by the selected node, the necessary current owner heading, and minimal instructions needed to express its fixed choice question. Do not send whole repositories, session transcripts, raw logs, credentials, or unrelated state. The rule-context owner governs source, language, heading scope, and current hash. If the complete necessary owner material cannot fit within the supported request budget, use direct document judgment; never silently truncate it and call it complete.

Bind each request to the supplied current facts, selected node, input hash, and current rule hash. The service does not retain cross-call state or establish caller identity, permission, provenance, sequence, or acceptance. After the response, compare echoed fingerprints and hashes with the current inputs and owners. If inputs or relevant owner text changed, discard the advice as stale. Advice is not a Core result, and it must not be cached as a semantic judgment.

Advice may suggest `continue`, `amend`, `stop`, or `evidence-on-demand` for the Control question, but only the caller's separately authorized decision has effect. Evidence-on-Demand returns to direct evidence/Context review and then Control; it never releases a Slice. Verification-impact advice can suggest covered dimensions only; it cannot report checks passed or waive changed-epoch re-verification. Any missing required owner or failed hard constraint remains blocking even if advice is favorable.

When advice is disabled, unrequested, unavailable, refused, invalid, timed out, or stale, return to the current direct owner and make the judgment there. This fallback does not relax a hard gate. Return only safe status and allowlisted failure categories; never expose raw exceptions, request details, credentials, or response bodies.

### Keep the API opt-in and invocation-local

The advisory feature defaults off. Enabling it requires trusted runtime configuration and explicit outbound-data authorization; an ordinary request parameter alone cannot enable it. Ordinary/default semantic-advice tests use mocks and send no network requests. Explicitly opted-in real tests still require outbound-data authorization and the same invocation-local configuration prerequisites stated in the applicable runtime section. Any real-request path must read both locally configured credential and endpoint values at invocation time and require both to be present and nonblank; if either is absent or blank, do not create a client or send a request. Provider-specific names and SDK handling belong only in the applicable runtime section. Do not print or persist configuration values; synthetic values are only for offline mocks.

## Codex CLI / ChatGPT Desktop optimizations

When an authorized current Session exposes the supported advisor, use it only for the registered decision questions after the caller has reviewed the bounded facts and direct owner. Keep it disabled unless trusted configuration explicitly enables it and outbound-data authorization is present. At each real invocation read both local environment values `OPENAI_API_KEY` and `OPENAI_BASE_URL`; explicitly pass both to the SDK, with no default or caller replacement. If either value is missing or blank, do not create the SDK client. Semantic-advice mock tests remain offline. An advisory response does not establish desktop identity, permission, or checkpoint completion.

## Claude Code CLI / Claude Desktop optimizations

There is currently no provider-specific advisory optimization for Claude. Follow the general rules and use only capabilities actually exposed to and authorized for the current Session.

## Related concepts

- [Workflow Routing Advice](workflow-routing-advice.md) — owns task-level stage suggestions outside the five fixed semantic-advice nodes.
- [Workflow Rule Context](../workflow-navigation/rule-context.md) — current registered owner headings and source/hash boundaries.
- [Session Role Ownership](../session-runtime/session-role-ownership.md) — trusted identity and per-operation guard evidence.
- [Coding Execution Decision Gate](execution-decision-gate.md) — decision and release ownership.
- [Coding Execution Control](../execution-control/execution-control.md) — Slice and Control transition authority.
- [Coding Delegation State Record](../delegation/delegation-state-record.md) — current Root state and Epoch basis.

# Decisions Advisory

[English](decisions-advisory.md) | [简体中文](decisions-advisory_zh_cn.md)

This module owns the optional handling of bounded semantic advice for five fixed registered nodes. It does not own their policies, choose or confirm a Core branch, authorize work, release a Slice, determine Verification, or accept the task.

## General rules

### Keep advice separate from judgment and authority

The supported nodes are `task_intent`, `output_class`, `contract_change`, `verification_impact`, and `control`, using only each node's current registered legal choices and required fact shape. Validate that a response contains exactly one answer with the requested node name and type, and that its value is one of that node's current legal choices; otherwise discard it and use direct judgment. Do not infer correctness from a confidence score or invent a confidence threshold. The mapped owner remains authoritative. Advice is a separate input for the Agent to consider; the Agent must review the direct owner, validate hard constraints, and make the actual judgment. Never replace a Core branch with an API answer or use advice to authorize mode, count, allocation, creation, dispatch, Slice release, a Control transition, verification success, or Acceptance.

Before Mode and Session pass, establish task intent and output classification from their direct authoritative sources and record advisory use as `Not applicable` because no authorized Root context exists. Do not open or initialize Root state to obtain an early suggestion. After a valid Root state exists, an authorized request may ask only for the node relevant to the current decision. Mode and count remain locked; a later task-intent or output-class suggestion cannot reopen them.

Send only the typed facts required by the selected node, the necessary current owner heading, and minimal instructions needed to express its fixed choice question. Do not send whole repositories, session transcripts, raw logs, credentials, or unrelated state. The rule-context owner governs source, language, heading scope, and current hash. If the complete necessary owner material cannot fit within the supported request budget, use direct document judgment; never silently truncate it and call it complete.

Bind each request locally to the actual project, Root session, Run, current Root Revision, selected node, normalized input hash, rule hash, and relevant Verification Epochs. A protected service wrapper must verify that any supplied Core evaluation belongs to this Root and is current, not replayed, and based on the same node, rule, Revision, and affected Epochs before requesting advice. A standalone advisor may be used without a Core evaluation; that does not make its response a Core result. After the response, recheck the same binding. If identity, Revision, rule, or a relevant Epoch changed, discard the advice as stale. A replayed operation receipt is not a fresh evaluation and must not trigger a new API request or make old advice current. Do not persist a semantic judgment cache.

Advice may describe `continue`, `amend`, `stop`, or `evidence-on-demand` for the Control node, but only the explicit trusted Root transition has effect. Evidence-on-Demand returns to the direct evidence/Context path and then Control; it is never a released Slice. Verification-impact advice can suggest covered dimensions only; it cannot report checks passed or waive changed-Epoch re-verification. Any missing required owner, hard-constraint failure, or host guard remains blocking for the dependent Enhanced action even if advice is favorable. A permitted Native judgment may continue through its own authoritative route when the advisory capability is unavailable.

When advice is disabled, unrequested, unavailable, refused, invalid, timed out, or stale, return to the current direct owner and make the judgment there. This fallback does not disable a healthy state service or relax a hard gate. Return only safe status and allowlisted failure categories; never expose raw exceptions, request details, credentials, or response bodies.

### Keep the API opt-in and invocation-local

The advisory feature defaults off. Enabling it requires trusted runtime configuration and explicit outbound-data authorization; an ordinary request parameter alone cannot enable it. Ordinary/default semantic-advice tests use mocks and send no network requests. Explicitly opted-in real tests still require outbound-data authorization and the same invocation-local configuration prerequisites stated in the applicable runtime section. Any real-request path must read both locally configured credential and endpoint values at invocation time and require both to be present and nonblank; if either is absent or blank, do not create a client or send a request. Provider-specific names and SDK handling belong only in the applicable runtime section. Do not print or persist configuration values; synthetic values are only for offline mocks.

## Codex CLI / ChatGPT Desktop optimizations

When the current Session exposes the supported advisor through an authorized embedding, use it only for the five registered nodes and after the applicable Root state and guards are verified. Keep it disabled unless trusted configuration explicitly enables the feature and outbound-data authorization is present. At each real invocation read both local environment values `OPENAI_API_KEY` and `OPENAI_BASE_URL`; explicitly pass both to the SDK, with no default or caller replacement. If either value is missing or blank, do not create the SDK client. Semantic-advice Mock tests remain offline. The verified 325-token synthetic smoke called the advisor directly with temporary Root state and source rule loading; it did not exercise the MCP handler or prove a real desktop host binding. SDK or fake-host evidence does not establish actual desktop identity or capability.

## Claude Code CLI / Claude Desktop optimizations

There is currently no provider-specific advisory optimization for Claude. Follow the general rules and use only capabilities actually exposed to and authorized for the current Session.

## Related concepts

- [Enhanced Rule Context](enhanced-rule-context.md) — current registered owner headings and source/hash boundaries.
- [Enhanced Host Binding](enhanced-host-binding.md) — trusted identity and per-operation guard evidence.
- [Coding Execution Decision Gate](execution-decision-gate.md) — decision and release ownership.
- [Coding Execution Control](execution-control.md) — Slice and Control transition authority.
- [Enhanced State Store](enhanced-state-store.md) — current Root state and Epoch basis.

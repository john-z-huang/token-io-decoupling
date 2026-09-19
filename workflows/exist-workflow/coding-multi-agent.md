# Coding Workflow — Multi-Agent Mode

[English](coding-multi-agent.md) | [简体中文](coding-multi-agent_zh_cn.md)

This route is selected by the Coding workflow and is valid only when the task record has released Multi-Agent Coding. Load the delegation policy before execution.

## Mode contract

- A Worker receives one released Interaction Slice and returns only through the parent-controlled channel; it never creates a recursive hierarchy or treats another Worker's progress as permission.
- The delegation policy owns mode, count, allocation, creation, reuse, replacement, and lifecycle; role names do not independently authorize a Session.
- If the user forbids subagents, child tasks, independent Sessions, or parallel delegation, stop this route and return to route selection; do not simulate multi-agent behavior.

## Composed inputs

Load `shared-protocols`, `agent-delegation-control`, `session-model`, and `execution-control` for this route; load `context-exchange` or `content-memo` only when the released slice needs them. The checkpoint list below is the complete route composition.

## Responsibility boundary

Use the role ownership defined in `session-model`; this route adds only the Multi-Agent conditions below.

## Route-specific environment requirements

Use the inventory and shared runtime rules from the Environment checkpoint. Continue only when it exposes the capabilities required by the task record and released slice. A Worker returns only to its direct parent and cannot create/manage Agents or contact arbitrary threads. On Local Codex, use the Skill bindings: Primary Output `gpt-5.6-luna`/`xhigh`; Change Verification `gpt-5.6-luna`/`xhigh`; Documentation/Git `gpt-5.6-luna`/`high`; Context Bootstrap `gpt-5.6-luna`/`high` or `medium` for deterministic refreshes. Escalate to `max` only after repeated failure or blockage, then return to the normal tier.

## Composed checkpoint sequence

Follow the common catalog in the Coding workflow. Multi-Agent deltas: load Context when a Worker needs reusable state; make a Decision before material dispatch; pair each released Implementation slice with a Control boundary; use a fresh independent Verification Session when allocated; route failures through Repair and a new verification epoch; then continue to Documentation, Git, and Acceptance.

## Context and dispatch

The common workflow already establishes shared protocols, Session rules, environment checks, and execution-control rules. Additionally:

1. Read [context exchange](../../references/coding/context-exchange.md) when Workers need reusable state, bounded handoff, or replacement recovery.
2. Read [content memo](../../references/coding/content-memo.md) when the dispatch enables Worker-authored content memos.
3. Use Context Bootstrap or Refresh only when it is assigned in the active delegation state. Keep the capsule factual and routing-only; it never replaces the Contract, mandatory source loading, or independent verification.
4. Keep each Worker's context-exchange subdirectory separate, and grant each Worker only the named code and context paths it needs. Follow the authority document for Worker allocation.

Before the first substantive dispatch, form a concise Decision Brief unless the task is simple, local, low-risk, obvious, reversible, and mechanically verifiable. If material facts are missing, release bounded reconnaissance only, then synthesize the result on the input side before releasing implementation.

For every released task bundle, state:

```text
Owner: Primary Output | Documentation/Comments & Git Operations | Change Verification
Objective: ...
Authorized scope/mutations: ...
Return conditions: ...
Unreleased boundary: ...
```

Mark a section `Not applicable` with a reason instead of creating a no-op Worker. Release one Interaction Slice at a time unless independent, non-conflicting parallel work is allowed by the authority document. Use Progress Signals inside a slice and a Control boundary at material boundaries.

## Verification and repair

- For a material change, perform independent Change Verification only when the task control record contains an allocated verifier. Otherwise perform the allowed final checks with the current or already allocated Agent and report independent verification as unavailable; do not alter the delegation state.
- Reuse that verifier for later Evidence-on-Demand and repaired epochs. Every changed final-state fingerprint requires independent re-evaluation; an earlier verdict is not evidence for a new state.
- On failure, release only the narrow repair scope, then send the new epoch to the same verifier. Do not begin post-verification documentation or dependent remote Git work while a material issue remains unresolved.
- After verification passes, release documentation/comment work and any Git work as separate bounded slices with explicit authorization.

## Completion

Apply the root Coding completion gate for documentation, Git, and final acceptance. The final report must distinguish real independent Sessions from same-Session logical phases and map every acceptance criterion to current evidence.

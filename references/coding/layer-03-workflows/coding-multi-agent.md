# Coding Workflow — Multi-Agent Mode

[English](coding-multi-agent.md) | [简体中文](coding-multi-agent_zh_cn.md)

This route is selected by the Coding workflow and is valid only after the Mode checkpoint releases Multi-Agent Coding. Before execution, the checkpoint composes the [mode-confirmation](../layer-01-fundamental-concepts/delegation-mode-confirmation.md), [count-gate](../layer-01-fundamental-concepts/delegation-mode-count-gate.md), [mode-reentry](../layer-01-fundamental-concepts/delegation-mode-reentry.md), [state-record](../layer-01-fundamental-concepts/delegation-state-record.md), [child-creation](../layer-01-fundamental-concepts/delegation-child-creation.md), [child-role-allocation](../layer-01-fundamental-concepts/delegation-child-role-allocation.md), [child-dispatch](../layer-01-fundamental-concepts/delegation-child-dispatch.md), [child-reuse/replacement](../layer-01-fundamental-concepts/delegation-child-reuse-replacement.md), and [child-lifecycle](../layer-01-fundamental-concepts/delegation-child-lifecycle.md) owners.

## Mode contract

- A Worker receives one released Interaction Slice and returns only through the parent-controlled channel; it never creates a recursive hierarchy or treats another Worker's progress as permission.
- The [mode-confirmation](../layer-01-fundamental-concepts/delegation-mode-confirmation.md), [count-gate](../layer-01-fundamental-concepts/delegation-mode-count-gate.md), [mode-reentry](../layer-01-fundamental-concepts/delegation-mode-reentry.md), and [state-record](../layer-01-fundamental-concepts/delegation-state-record.md) owners govern their respective root mode, count, re-entry, and state-record boundaries; [child-creation](../layer-01-fundamental-concepts/delegation-child-creation.md), [child-role-allocation](../layer-01-fundamental-concepts/delegation-child-role-allocation.md), [child-dispatch](../layer-01-fundamental-concepts/delegation-child-dispatch.md), [child-reuse/replacement](../layer-01-fundamental-concepts/delegation-child-reuse-replacement.md), and [child-lifecycle](../layer-01-fundamental-concepts/delegation-child-lifecycle.md) own their corresponding child boundaries. Role names do not independently authorize a Session.
- If the user forbids subagents, child tasks, independent Sessions, or parallel delegation, stop this route and return to route selection; do not simulate multi-agent behavior.

## Composed inputs

Compose [shared protocols](../../share/shared-protocols.md), [delegation state](../layer-01-fundamental-concepts/delegation-state-record.md), [the mode-confirmation reference](../layer-01-fundamental-concepts/delegation-mode-confirmation.md), [the mode/count gate](../layer-01-fundamental-concepts/delegation-mode-count-gate.md), [the mode-reentry reference](../layer-01-fundamental-concepts/delegation-mode-reentry.md), [child creation](../layer-01-fundamental-concepts/delegation-child-creation.md), [child role allocation](../layer-01-fundamental-concepts/delegation-child-role-allocation.md), [child dispatch](../layer-01-fundamental-concepts/delegation-child-dispatch.md), [child reuse/replacement](../layer-01-fundamental-concepts/delegation-child-reuse-replacement.md), [child lifecycle](../layer-01-fundamental-concepts/delegation-child-lifecycle.md), [session model](../layer-01-fundamental-concepts/session-model.md), [session role ownership](../layer-01-fundamental-concepts/session-role-ownership.md), [session context firewall](../layer-01-fundamental-concepts/session-context-firewall.md), and [execution control](../layer-01-fundamental-concepts/execution-control.md) for this route; load [context exchange](../layer-01-fundamental-concepts/context-exchange.md), [context workspace boundary](../layer-01-fundamental-concepts/context-exchange-workspace-boundary.md), [context handoff](../layer-01-fundamental-concepts/context-exchange-handoff.md), or [content memo](../layer-01-fundamental-concepts/content-memo.md) only when the released slice needs them. The Mode checkpoint has already validated the record; the checkpoint list below is the complete route composition.

## Responsibility boundary

Use the role ownership defined in [session role ownership](../layer-01-fundamental-concepts/session-role-ownership.md); this route adds only the Multi-Agent conditions below.

## Route-specific environment requirements

Use the inventory and shared runtime rules from the [Environment capability inventory](../layer-02-workflow-concepts/environment-capability-inventory.md). Continue only when it exposes the capabilities required by the task record and released slice. A Worker returns only to its direct parent and cannot create/manage Agents or contact arbitrary threads. On Local Codex, use the Skill bindings: Primary Output `gpt-5.6-luna`/`xhigh`; Change Verification `gpt-5.6-luna`/`xhigh`; Documentation/Git `gpt-5.6-luna`/`high`; Context Bootstrap `gpt-5.6-luna`/`high` or `medium` for deterministic refreshes. Escalate to `max` only after repeated failure or blockage, then return to the normal tier.

## Composed checkpoint sequence

The Coding selector has already completed the Contract, Environment, and Mode checkpoints as pre-route gates; do not re-run them here. Follow the common catalog by composing [Context](../layer-02-workflow-concepts/context.md), [Decision](../layer-02-workflow-concepts/decision.md), [Implementation](../layer-02-workflow-concepts/implementation.md), [Control](../layer-02-workflow-concepts/control.md), [Verification](../layer-02-workflow-concepts/verification.md), [Verification independence](../layer-02-workflow-concepts/verification-independence.md), [Verification reporting](../layer-02-workflow-concepts/verification-reporting.md), [Verification epoch](../layer-02-workflow-concepts/verification-epoch.md), [Repair](../layer-02-workflow-concepts/repair.md), [Repair scope gate](../layer-02-workflow-concepts/repair-scope-gate.md), [Repair execution](../layer-02-workflow-concepts/repair-execution.md), [Repair verification handoff](../layer-02-workflow-concepts/repair-verification-handoff.md), [Documentation](../layer-02-workflow-concepts/documentation.md), [Git](../layer-02-workflow-concepts/git.md), and [Acceptance](../layer-02-workflow-concepts/acceptance.md). Multi-Agent deltas: load Context when a Worker needs reusable state; make a Decision before material dispatch; pair each released Implementation slice with a Control boundary; use a fresh independent Verification Session when allocated; route failures through Repair and a new verification epoch; then continue to Documentation, Git, and Acceptance.

## Context and dispatch

The common workflow already establishes shared protocols, Session rules, environment checks, and execution-control rules. Additionally:

1. Read [context exchange](../layer-01-fundamental-concepts/context-exchange.md) when Workers need reusable state; additionally read [context workspace boundary](../layer-01-fundamental-concepts/context-exchange-workspace-boundary.md) when workspace or capability boundaries must be enforced, and [context handoff](../layer-01-fundamental-concepts/context-exchange-handoff.md) for bounded handoff or replacement recovery.
2. Read [content memo](../layer-01-fundamental-concepts/content-memo.md) when the dispatch enables Worker-authored content memos.
3. Use Context Bootstrap or Refresh only when it is assigned in the active delegation state. Keep the capsule factual and routing-only; it never replaces the Contract, mandatory source loading, or independent verification.
4. Keep each Worker's context-exchange subdirectory separate, and grant each Worker only the named code and context paths it needs. Follow the child role-allocation and dispatch references for Worker allocation and boundaries.

Before the first substantive dispatch, form a concise Decision Brief unless the task is simple, local, low-risk, obvious, reversible, and mechanically verifiable. If material facts are missing, release bounded reconnaissance only, then synthesize the result on the input side before releasing implementation.

For every released task bundle, state:

```text
Owner: Primary Output | Documentation/Comments & Git Operations | Change Verification
Objective: ...
Authorized scope/mutations: ...
write_content_memo: true | false
Return conditions: ...
Unreleased boundary: ...
```

The parent must explicitly publish `write_content_memo` for each released slice alongside its scope and mutations; the Worker consumes that bundle value and does not infer or rewrite it.

Mark a section `Not applicable` with a reason instead of creating a no-op Worker. Release one Interaction Slice at a time unless independent, non-conflicting parallel work is allowed by the child dispatch/lifecycle reference. Use Progress Signals inside a slice and a Control boundary at material boundaries.

## Verification and repair

- For a material change, perform independent Change Verification only when the task control record contains an allocated verifier. Otherwise perform the allowed final checks with the current or already allocated Agent and report independent verification as unavailable; do not alter the delegation state.
- Reuse that verifier for later Evidence-on-Demand and repaired epochs. Every changed final-state fingerprint requires independent re-evaluation; an earlier verdict is not evidence for a new state.
- On failure, release only the narrow repair scope, then send the new epoch to the same verifier. Do not begin post-verification documentation or dependent remote Git work while a material issue remains unresolved.
- After verification passes, release documentation/comment work and any Git work as separate bounded slices with explicit authorization.

## Completion

Apply the root Coding completion gate for documentation, Git, and final acceptance. The final report must distinguish real independent Sessions from same-Session logical phases and map every acceptance criterion to current evidence.

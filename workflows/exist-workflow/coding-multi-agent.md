sed: --: No such file or directory
# Coding Workflow — Multi-Agent Mode

[English](coding-multi-agent.md) | [简体中文](coding-multi-agent_zh_cn.md)

Read [`../coding.md`](../coding.md) first, then read `../../references/coding/agent-delegation-control.md` for the authoritative delegation state. Use this pre-composed workflow only when that document records the Multi-Agent outcome.

## Mode contract

- A Worker receives one released Interaction Slice and returns only through the parent-controlled channel. A Worker never creates a recursive execution hierarchy or treats another Worker's progress as permission.
- Follow the authority document for mode confirmation, child count, role allocation, creation, reuse, replacement, and lifecycle. Role names describe responsibilities and do not independently authorize a Session.
- If the user forbids subagents, child tasks, independent Sessions, or parallel delegation, stop this route and return to route selection; do not simulate multi-agent behavior.

## Composed inputs

This route combines the independent Coding references before executing the checkpoint sequence: `shared-protocols`, `agent-delegation-control`, `session-model`, and `execution-control`. When the released slices need them, also load `context-exchange` and `content-memo`. The authority records mode/count/lifecycle state; the other references provide message primitives, Session semantics, execution planning, and bounded context mechanics. The checkpoint list below is the complete route composition; checkpoint modules are not imported into one another.

## Responsibility boundary

- The root parent owns the Semantic Contract, material decisions, authorization, checkpoint outcomes, Worker lifecycle, and semantic acceptance.
- Primary Output owns approved implementation and provisional focused checks; it does not perform final acceptance or non-trivial Git work.
- Change Verification owns final change-result verification when the Contract requires it.
- Documentation/Comments & Git Operations owns approved post-verification documentation or comments and non-trivial Git work under an explicit release.

## Route-specific environment requirements

Use the capability inventory produced by the Environment checkpoint as follows:

- Continue this route only when the current runtime environment exposes the capabilities required by the delegation state recorded in the authority document and by the released slice.
- A Worker must return only to its direct parent and must not create or manage Agents/Sessions or contact arbitrary threads. If the runtime environment cannot guarantee these restrictions, do not dispatch a Worker.
- On local Codex, read global instructions from `~/.codex/AGENTS.md`; same-level `~/.codex/AGENTS.override.md` takes precedence, while repository instructions remain authoritative. When independent Session creation and model controls are exposed, use the current Skill's bindings: Primary Output `gpt-5.6-luna` with `reasoning_effort=xhigh`; Change Verification `gpt-5.6-luna` with `xhigh`; Documentation/Comments & Git Operations `gpt-5.6-luna` with `high`; Context Bootstrap/Refresh `gpt-5.6-luna` with `high`, or `medium` only for deterministic metadata, hash, or delta refreshes.
- Use `reasoning_effort=max` only as a narrow escalation after a repeated failure or blocker, then return to the normal tier. After changing global instructions, an active override, the Skill, or repository instructions, start a new Codex run/Session before judging whether the change was adopted.
- On ChatGPT Work, use only the model identity, reasoning controls, independent Sessions, connectors, files, and execution tools explicitly exposed by the current task. There is no fixed model binding, and a connector or attachment does not imply local execution, repository mutation, credentials, or cross-thread control.
- On standard ChatGPT, use Multi-Agent Coding only if the chat explicitly exposes the required independent Sessions, delegation route, tools, and verification capability. Do not assume shell, Python, Git, tests, sandbox, worktree, connectors, or cross-thread control, and do not substitute another runtime environment or model.
- If any required model, parameter, Session, return path, filesystem, tool, connector, or authentication capability is missing or unknown, stop at that boundary and report the blocked capability.

## Composed checkpoint sequence

Run the checkpoints in this order, skipping only conditional checkpoints with a recorded reason:

1. [Contract](../checkpoint/contract.md), [Environment](../checkpoint/environment.md), and [Mode](../checkpoint/mode.md).
2. [Context](../checkpoint/context.md) when Workers need bounded reusable state or replacement recovery.
3. [Decision](../checkpoint/decision.md) before releasing a material direction or dispatch.
4. [Implementation](../checkpoint/implementation.md) for each released slice, with [Control boundary](../checkpoint/control.md) at material boundaries.
5. [Verification](../checkpoint/verification.md) in a fresh independent Change Verification Session for material changes when the runtime environment exposes it.
6. [Repair](../checkpoint/repair.md) for a narrow failed result, followed by Verification against the new epoch.
7. [Documentation](../checkpoint/documentation.md) after verification passes.
8. [Git](../checkpoint/git.md) only for explicitly authorized effects.
9. [Acceptance](../checkpoint/acceptance.md) before completion.

## Context and dispatch

The common workflow already establishes shared protocols, Session rules, environment checks, and execution-control rules. Additionally:

1. Read [`../../references/coding/context-exchange.md`](../../references/coding/context-exchange.md) when Workers need reusable state, bounded handoff, or replacement recovery.
2. Read [`../../references/coding/content-memo.md`](../../references/coding/content-memo.md) when the dispatch enables Worker-authored content memos.
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

- For a material change, perform independent Change Verification only when the authority document records an allocated verifier. Otherwise perform the allowed final checks with the current or already allocated Agent and report independent verification as unavailable; do not alter the delegation state.
- Reuse that verifier for later Evidence-on-Demand and repaired epochs. Every changed final-state fingerprint requires independent re-evaluation; an earlier verdict is not evidence for a new state.
- On failure, release only the narrow repair scope, then send the new epoch to the same verifier. Do not begin post-verification documentation or dependent remote Git work while a material issue remains unresolved.
- After verification passes, release documentation/comment work and any Git work as separate bounded slices with explicit authorization.

## Completion

Return to [`../coding.md`](../coding.md) for documentation, Git, and final acceptance. The final report must distinguish real independent Sessions from same-Session logical phases and map every acceptance criterion to current evidence.

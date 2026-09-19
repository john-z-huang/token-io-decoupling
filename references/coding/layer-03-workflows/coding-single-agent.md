# Coding Workflow — Single-Agent Mode

[English](coding-single-agent.md) | [简体中文](coding-single-agent_zh_cn.md)

This route is selected by the Coding workflow and is valid only after the Mode checkpoint releases Single-Agent Coding. The checkpoint composes the state-record and mode/count references before execution.

## Mode contract

- Keep all work in the current Session. Treat Input-side Reasoning, Primary Output, documentation, and applicable checks as logical phases, not separate agents.
- The state-record and mode/count references own the root state and Single-Agent gate; child dispatch/lifecycle does not apply to this route.
- Keep the Contract, Context, Decision, Control boundary, verification boundary, documentation boundary, Git authorization, and completion gate from the checkpoint sequence below.
- A task-level prohibition such as “do not create subagents” or “do not use a browser” remains active for the entire task.

## Composed inputs

Compose [shared protocols](../../share/shared-protocols.md), [delegation state](../layer-01-fundamental-concepts/delegation-state-record.md), [the mode/count gate](../layer-01-fundamental-concepts/delegation-mode-count-gate.md), [session model](../layer-01-fundamental-concepts/session-model.md), and [execution control](../layer-01-fundamental-concepts/execution-control.md) for this route. The Mode checkpoint has already validated the record; the checkpoint list below is the complete route composition.

## Responsibility boundary in the current Session

Use the role ownership defined in `session-model`; this route runs those roles as logical phases in one Session and cannot provide an independent verifier.

## Route-specific environment requirements

Use the inventory and shared runtime rules from the Environment checkpoint. This route keeps all phases in the current Session; it does not create independent Sessions or Worker return paths. If a required capability is unavailable, stop the slice and report it.

## Composed checkpoint sequence

Follow the common catalog in the Coding workflow by composing [Contract](../layer-02-workflow-concepts/contract.md), [Environment](../layer-02-workflow-concepts/environment.md), [Mode](../layer-02-workflow-concepts/mode.md), [Context](../layer-02-workflow-concepts/context.md), [Decision](../layer-02-workflow-concepts/decision.md), [Implementation](../layer-02-workflow-concepts/implementation.md), [Control](../layer-02-workflow-concepts/control.md), [Verification](../layer-02-workflow-concepts/verification.md), [Repair](../layer-02-workflow-concepts/repair.md), [Documentation](../layer-02-workflow-concepts/documentation.md), [Git](../layer-02-workflow-concepts/git.md), and [Acceptance](../layer-02-workflow-concepts/acceptance.md). Single-Agent deltas: load Context only for bounded reconnaissance or recovery; make a Decision before each material direction; implement one approved slice with a Control boundary; verify the current final-state fingerprint; use Repair only after a concrete failure and re-run Verification for the new epoch; then continue to Documentation, Git, and Acceptance in the current Session.

## Single-Session execution rules

1. Stabilize `ACTIVE_CONSTRAINTS`—the short, current list of hard user, runtime, repository, permission, safety, and Session constraints—along with the Semantic Contract, acceptance criteria, and any Decision Brief before substantive work. For a simple fast path, keep the decision concise but explicit.
2. If project facts are missing, perform bounded reconnaissance as a logical phase. Do not implement until the facts and approved direction are settled.
3. Execute one approved Interaction Slice at a time. Read only the files needed for that slice, make only authorized mutations, and run provisional focused checks to guide repairs.
4. At each material boundary, record status, findings, changed scope, verification, issue, next action, and the unreleased boundary.
5. Run final checks against the current final-state fingerprint or epoch before documentation or dependent Git delivery. Same-Session checks are not independent verification.

## Verification limitation

For a material change, the Contract or risk assessment may require an independent Change Verification Session. Single-Agent mode cannot create or claim an independent verifier Session, so independent verification is unavailable on this route. Run the strongest allowed checks in the current Session, report that the result is not independent verification, and do not release dependent external Git effects while the required boundary remains unresolved.

For trivial behavior-preserving or documentation-only work, use the applicable fast path and run: `rg` for stale paths/names referenced by the changed files; a Markdown/link review covering changed local targets; `git diff --check`; `python3 scripts/check-multilingual-docs.py`; and a manual check that each changed rule still agrees with the selected Contract and route. Record each command or review result and its pass condition.

## Completion

Apply the root Coding completion gate. The final report must identify the work as Single-Agent, distinguish provisional checks from final checks, state any unavailable independent verification, and map every acceptance criterion to current evidence.

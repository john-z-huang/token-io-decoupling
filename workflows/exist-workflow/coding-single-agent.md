# Coding Workflow — Single-Agent Mode

[English](coding-single-agent.md) | [简体中文](coding-single-agent_zh_cn.md)

Read [`../coding.md`](../coding.md) first, then read `../../references/coding/agent-delegation-control.md` for the authoritative delegation state. Use this pre-composed workflow only when that document records the Single-Agent outcome.

## Mode contract

- Keep all work in the current Session. Treat Input-side Reasoning, Primary Output, documentation, and applicable checks as logical phases, not separate agents.
- Follow the authority document for all Agent/Session creation, reuse, exception, and lifecycle decisions; this route does not restate them.
- Keep the Contract, Context, Decision, Control boundary, verification boundary, documentation boundary, Git authorization, and completion gate from the checkpoint sequence below.
- A task-level prohibition such as “do not create subagents” or “do not use a browser” remains active for the entire task.

## Composed inputs

This route combines the independent Coding references before executing the checkpoint sequence: `shared-protocols`, `agent-delegation-control`, `session-model`, and `execution-control`. The policy defines mode/delegation rules; the task control record carries the current state; the other references provide shared primitives, Session semantics, and execution planning. The checkpoint list below is the complete route composition; checkpoint modules are not imported into one another.

## Responsibility boundary in the current Session

- Input-side Reasoning owns the Semantic Contract, material decisions, authorization, checkpoint outcomes, and semantic acceptance.
- Primary Output owns approved implementation and provisional focused checks.
- Documentation/Comments & Git Operations owns approved post-verification documentation or comments and non-trivial Git work under an explicit release.
- Any independent Change Verification requirement remains a requirement even though the route uses one Session; never label same-Session checks as independent. This route cannot provide an independent verifier.

## Route-specific environment requirements

Use the capability inventory produced by the Environment checkpoint as follows:

- Keep the phases required by the authority document in the current Session. This route does not define independent Session creation, Worker return paths, or role-specific model bindings.
- On local Codex, read global instructions from `~/.codex/AGENTS.md`; same-level `~/.codex/AGENTS.override.md` takes precedence, while repository instructions remain authoritative. After changing those instructions, the active override, the Skill, or repository instructions, start a new Codex run/Session before judging whether the change was adopted.
- On ChatGPT Work, use only the model, reasoning controls, files, connectors, and execution tools explicitly exposed by the current task. An attachment or connector does not imply local execution, repository mutation, credentials, or cross-thread control.
- On standard ChatGPT, do not assume shell, Python, Git, tests, sandbox, worktree, connectors, or independent Sessions. If local execution is unavailable, do not claim that tests, builds, Git operations, or filesystem validation ran.
- If a capability required by the current slice is missing or unknown, stop that slice and report it; do not replace the runtime environment, model, Session, tool, permission, or authentication path.

## Composed checkpoint sequence

Run the checkpoints in this order, skipping only conditional checkpoints with a recorded reason:

1. [Contract](../checkpoint/contract.md), [Environment](../checkpoint/environment.md), and [Mode](../checkpoint/mode.md).
2. [Context](../checkpoint/context.md) only when bounded reconnaissance, reusable file-backed state, or recovery context is needed.
3. [Decision](../checkpoint/decision.md) before each material implementation direction.
4. [Implementation](../checkpoint/implementation.md) for one approved slice at a time, with [Control boundary](../checkpoint/control.md) before the next slice or a material change.
5. [Verification](../checkpoint/verification.md) against the current final-state fingerprint or epoch.
6. [Repair](../checkpoint/repair.md) only after a concrete failure, followed by Verification for the new state.
7. [Documentation](../checkpoint/documentation.md) after the required verification decision.
8. [Git](../checkpoint/git.md) only for explicitly authorized Git effects.
9. [Acceptance](../checkpoint/acceptance.md) before reporting completion.

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

Return to [`../coding.md`](../coding.md) for the root completion gate. The final report must identify the work as Single-Agent, distinguish provisional checks from final checks, state any unavailable independent verification, and map every acceptance criterion to current evidence.

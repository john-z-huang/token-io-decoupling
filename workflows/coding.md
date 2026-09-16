# Coding Workflow

[English](coding.md) | [简体中文](coding_zh_cn.md)

Use this workflow when repository text, developer-tool output, implementation, tests, documentation, or Git state is the main work state. This file is the only Coding workflow index. It owns route selection, environment-checkpoint routing, checkpoint composition, and the final completion gate.

## Entry requirements

At task entry:

1. Read [`../references/share/shared-protocols.md`](../references/share/shared-protocols.md).
2. Read [`../references/coding/session-model.md`](../references/coding/session-model.md) before making a Session or runtime-environment decision.
3. Read [`../references/coding/execution-control.md`](../references/coding/execution-control.md) before substantive implementation, debugging, build, test, or Git-stage release.
4. Identify the actual runtime environment and complete the linked Environment checkpoint.
5. Select exactly one execution route. If a pre-composed route matches, read that route; otherwise compose the checkpoints listed below.

## Runtime environment

Before environment-dependent work, read the [Environment checkpoint](checkpoint/environment.md). That checkpoint owns runtime-environment classification and the inventory of capabilities actually exposed by the current surface. The selected workflow interprets that inventory against its own requirements; this index does not repeat either set of rules.

## Two pre-composed workflows

Two complete Coding workflows are maintained under `workflows/exist-workflow/`:

- [Single-Agent Coding](exist-workflow/coding-single-agent.md): use when the user forbids subagents, child tasks, independent Sessions, or parallel delegation, or when no concrete structural benefit requires separation.
- [Multi-Agent Coding](exist-workflow/coding-multi-agent.md): use only when the user explicitly requests multiple agents, or when the Input-side Agent identifies concrete structural benefit, hard isolation, or a capability requirement and no higher-priority constraint forbids delegation.

After reading this common workflow, if the task matches one of these routes, follow that complete document directly. Do not load both routes. If a later material fact invalidates the route, amend the Contract, stop the current slice, and select the other route explicitly.

## Checkpoint index

Load the following independent checkpoint modules only when their condition applies. Each module defines one action boundary; it is not a router for another module.

1. [Contract](checkpoint/contract.md) — always stabilize the goal, hard constraints, decisions, and acceptance conditions first.
2. [Environment](checkpoint/environment.md) — confirm the actual runtime environment and capabilities before environment-dependent work.
3. [Mode](checkpoint/mode.md) — choose exactly one execution route after the Contract and environment check.
4. [Context](checkpoint/context.md) — use when bounded reconnaissance, reusable file-backed context, or recovery context is needed.
5. [Decision](checkpoint/decision.md) — use before a material implementation or whenever a new fact changes scope, architecture, security, or compatibility.
6. [Implementation](checkpoint/implementation.md) — use for each approved change slice and its focused provisional checks.
7. [Control boundary](checkpoint/control.md) — use at a material boundary before releasing the next slice or changing authority.
8. [Verification](checkpoint/verification.md) — use after implementation and after every repaired final-state epoch.
9. [Repair](checkpoint/repair.md) — use only for a scoped repair after a failed check or verification result.
10. [Documentation](checkpoint/documentation.md) — use after the required verification decision for approved docs or comments.
11. [Git](checkpoint/git.md) — use only when the user or task explicitly authorizes Git effects.
12. [Acceptance](checkpoint/acceptance.md) — always map acceptance criteria to current evidence before reporting completion.

## How to compose checkpoints

For a task that does not match a pre-composed workflow, combine checkpoints in this order:

1. Always run Contract, Environment, and Mode.
2. Run Context only when the task needs reconnaissance beyond the current bounded slice, reusable file-backed state, or recovery from a replaced Session.
3. Run Decision before material implementation. If the task is simple, local, low-risk, reversible, and mechanically verifiable, keep the decision concise but explicit.
4. Run Implementation for one approved slice at a time. Place a Control boundary between slices and before any material change in authority or scope.
5. Run Verification after the final implementation state. If verification fails, run Repair for the narrow approved fix and then repeat Verification against the new final-state epoch.
6. Run Documentation only after the verification decision, and Git only when its exact repository, worktree, ref, remote, and effect are authorized.
7. Always finish with Acceptance. Do not report `COMPLETE` while a required capability, verification boundary, authorization, or acceptance item is unresolved.

If a checkpoint is not applicable, record the reason at the checkpoint instead of silently omitting it. If a new fact changes a material decision, return to Contract and Decision before continuing. The current parent agent owns release decisions and semantic acceptance; the selected route defines whether that ownership is a logical phase or a parent Session.

## Reference composition

The reference modules are independent and do not route to one another. This workflow combines them as follows:

- [`../references/share/shared-protocols.md`](../references/share/shared-protocols.md) — Semantic Contract baseline, parent authority, Worker return path, Dispatch Preview, progress, evidence-on-demand, and cache-aware context organization. Load for every Coding task.
- [`../references/coding/session-model.md`](../references/coding/session-model.md) — coding responsibilities, Session topology, role independence, Context Firewall, and Session affinity. Load before choosing or changing Session mode.
- [`../references/coding/execution-control.md`](../references/coding/execution-control.md) — two-level planning, Interaction Slices, release checkpoints, verification boundary, documentation boundary, Git gates, and Input-side output discipline. Load before substantive execution.
- [`../references/coding/context-exchange.md`](../references/coding/context-exchange.md) — file-backed context layout, ownership, transport, freshness, bootstrap, and replacement handoff. Load only when the selected route needs it.
- [`../references/coding/content-memo.md`](../references/coding/content-memo.md) — Worker memo language, write setting, content boundary, and refresh behavior. Load only when the multi-agent route uses Worker-authored memos.

Keep reusable semantics in their owning reference. Keep route selection and cross-module loading order here or in the selected pre-composed workflow. Do not add cross-links between reference modules.

## Completion gate

Return `COMPLETE` only after Acceptance passes. The final report must distinguish checked/passed from not run/unavailable, authorized effects from possible effects, and observed facts from assumptions or runtime-environment/model capability claims. Do not commit, push, create an Issue/PR, change remotes, or cause another external effect unless explicitly authorized.

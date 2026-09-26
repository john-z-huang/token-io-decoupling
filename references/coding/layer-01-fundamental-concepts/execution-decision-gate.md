# Coding Execution Decision Gate

[English](execution-decision-gate.md) | [简体中文](execution-decision-gate_zh_cn.md)

This module defines the Decision Brief, blocking Decision Checkpoint, solution selection, Contract updates, and implementation-release decision conditions. It does not define the planning outline, Interaction Slice fields, stage feedback, role/session semantics, context transport, or delegation lifecycle.

## General rules

### Decision Brief

For work that is not simple, local, low-risk, obvious, reversible, and mechanically verifiable, prepare a concise **Decision Brief** before the first substantive execution slice. It records the result of analysis rather than private chain-of-thought and should contain at least:

- `Problem`
- `Known facts`
- `Assumptions and unknowns`
- `Decision questions`
- `Solution envelope`
- `Risks`
- `Acceptance`
- `Stages and checkpoints`

`Acceptance` records acceptance information as a Decision Brief field; this module does not define an Acceptance workflow.

### Decision Checkpoint and implementation release

Use a blocking Decision Checkpoint when the next stage depends on high-value judgment, such as a competing architecture/API choice, a public-interface/schema/compatibility/security boundary, a material debugging fork, a substantial scope expansion, or a verification failure that changes the Contract.

If material decisions remain open, release reconnaissance only. After it returns, confirm or reject assumptions, choose the approved direction, update the Contract, and release implementation. If new evidence changes a material decision, pause that direction and repeat the decision gate. Do not release an unresolved combined mandate that asks one executor to analyze, choose, implement, and verify an undecided solution.

## Codex CLI / ChatGPT Desktop optimizations

No provider-specific optimization instructions at present; follow the general rules above.

## Claude Code CLI / Claude Desktop optimizations

No provider-specific optimization instructions at present; follow the general rules above.

## Related concepts

- [Coding Execution Control](execution-control.md) — locate Interaction Slice boundaries.
- [Coding Execution Planning](execution-planning.md) — locate the bounded planning relationship.
- [Coding Execution Stage Feedback](execution-stage-feedback.md) — locate stage-internal feedback signals.
- [Coding Session Model](session-model.md) — locate role and Session ownership.
- [Coding Child Lifecycle](delegation-child-lifecycle.md) — locate delegation release lifecycle ownership.

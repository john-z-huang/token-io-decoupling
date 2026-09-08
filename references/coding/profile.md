# Coding Runtime Profile

This module owns the current Coding Flow model bindings and reasoning-effort policy. It is deployment policy, not the Token I/O Decoupling architecture itself. Future model changes should normally update this file without changing role, context, checkpoint, or Multimodal responsibility boundaries.

The cross-Flow Profile constraints in the main [`../../SKILL.md`](../../SKILL.md) also apply.

## Session mapping

At Coding Flow startup, first confirm the current Code Agent model identity and then map responsibilities to Sessions:

- **Current Agent is explicitly `gpt-5.6-luna`**: enter **Single-Agent Luna Mode**. The current Session performs both the Input-side Reasoning Role and Primary Output Role, including project exploration, implementation, debugging, mechanical verification, and output. Do not create or require another Luna Primary Output Agent merely to preserve a two-role topology. Because this Session also owns high-value reasoning, keep its normal materialization at `reasoning_effort=xhigh`.
- **Current Agent cannot explicitly confirm it is `gpt-5.6-luna`**: constrain the current Agent as the input-side reasoning role and use an independent `gpt-5.6-luna` for the Primary Output Role, preserving the normal two-Session Coding Flow.

Role and Session semantics are defined in [`session-model.md`](session-model.md).

## Reasoning-effort selection

- In normal two-Session Coding, the independent Primary Output Luna defaults to `reasoning_effort=xhigh`. Use `xhigh` for general feature implementation, non-trivial refactoring or debugging, complex test/verification code, and other work where substantial implementation judgment is expected. Output length or project size alone does not justify increasing effort.
- Prefer `reasoning_effort=high` for bounded auxiliary materialization whose main work is developer documentation, code comments, simple unit tests, low-risk mechanical edits, or similarly constrained support work. Additional auxiliary Coding Workers should default to `high` unless their concrete task meets the `xhigh` criteria.
- Use `reasoning_effort=medium` or a lower host-supported tier only when the host explicitly exposes that tier and the task is strictly bounded, low semantic risk, and easy to verify mechanically. Suitable examples include running already-selected tests/formatters/linters and compressing results, collecting file/path metadata, exact search or extraction, literal replacements, template-driven formatting, or generated-table updates. Tiers below `medium` should normally be read-only or deterministic transformations. Do not assign Semantic Contract ownership, architecture/product decisions, cross-module implementation, complex debugging, complex test design, or public API/schema/permission changes to these lightweight Workers.

## Targeted max escalation

`reasoning_effort=max` is an exception escalation, not a default Worker setting.

Use it only for a specific task that an existing `high`/`xhigh` Worker has repeatedly failed, oscillated on, or become clearly blocked by. The parent creates a new, narrowly scoped max Worker; when possible, the predecessor first writes reusable context/handoff documents in the primary worktree as defined by [`context-exchange.md`](context-exchange.md), and the max Worker reads those documents instead of restarting project exploration from zero.

After the blocker is resolved, follow-on work returns to the normal `xhigh`/`high` tiers rather than keeping max for unrelated tasks.

Single-Agent Luna Mode may create another Agent only for fresh verification, real parallelism, clearly degraded/overgrown current context, explicit isolation benefit, or targeted `max` escalation for a specific repeatedly blocked task. Project exploration, implementation, testing, long output, or generic task complexity are not exceptions.

## Profile-local constraints

- Do not silently replace the Coding role that requires Luna with another model.
- If an independent Luna role is required but `gpt-5.6-luna` identity cannot be confirmed, the model cannot be selected explicitly, or the host cannot satisfy the reasoning-effort tier required for that dispatch, stop that substantive Coding work and briefly report the block.
- Purely read-only, strictly bounded diagnosis may continue when Luna identity is confirmed but the host cannot set reasoning effort. Do not use that exception to move complex project-state work back to the advanced parent model or to silently assign lightweight effort to a task whose Profile requires `high` or `xhigh`.

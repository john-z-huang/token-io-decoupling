# OpenAI Coding Model Profile

This file owns the concrete OpenAI model bindings and reasoning-effort policy for the current verified Coding deployment. It is deployment policy, not the Token I/O Decoupling architecture. Host-specific mechanics are supplied by the active Host Adapter; generic Session semantics are defined by [`../../coding/session-model.md`](../../coding/session-model.md) and [`../../coding/runtime.md`](../../coding/runtime.md).

## Role bindings and dual-role eligibility

At Coding Flow startup, confirm the current Session's model identity through the Host Adapter before applying this Profile:

- **Input-side Reasoning**: the current advanced parent model/session owns high-value semantic decisions.
- **Primary Output**: the required OpenAI execution model is `gpt-5.6-luna`.
- **Dual-role eligibility**: when the current Session can explicitly confirm that it is `gpt-5.6-luna` and the Host can satisfy the task's required reasoning-effort tier in that Session, this Profile declares the current Session eligible for both Input-side Reasoning and Primary Output. The generic runtime mapping therefore enters **Single-Session Coding Mode** unless a concrete structural reason requires another Session.
- **Normal two-Session mapping**: when the current Agent cannot explicitly confirm that it is `gpt-5.6-luna`, keep the current Agent constrained to the input-side reasoning responsibility and use an independent `gpt-5.6-luna` Session for Primary Output.

Single-Session Coding Mode preserves the current deployment behavior: the current Luna directly performs project exploration, implementation, debugging, mechanical verification, and output rather than delegating ordinary work to another Luna merely to preserve a two-role topology. Because the same Session also owns high-value reasoning, its ordinary substantive materialization uses `reasoning_effort=xhigh`.

## Reasoning-effort selection

- In normal two-Session Coding, the independent Primary Output Luna defaults to `reasoning_effort=xhigh`. Use `xhigh` for general feature implementation, non-trivial refactoring or debugging, complex test/verification code, and other work where substantial **execution judgment within an approved semantic plan** is expected. This effort tier does not transfer ownership of problem formulation, architecture choice, unresolved semantic trade-offs, or acceptance to the Primary Output role. Output length or project size alone does not justify increasing effort.
- Prefer `reasoning_effort=high` for bounded auxiliary materialization whose main work is developer documentation, code comments, simple unit tests, low-risk mechanical edits, or similarly constrained support work. Additional auxiliary Coding Workers should default to `high` unless their concrete task meets the `xhigh` criteria.
- Use `reasoning_effort=medium` or a lower host-supported tier only when the Host explicitly exposes that tier and the task is strictly bounded, low semantic risk, and easy to verify mechanically. Suitable examples include running already-selected tests/formatters/linters and compressing results, collecting file/path metadata, exact search or extraction, literal replacements, template-driven formatting, or generated-table updates. Tiers below `medium` should normally be read-only or deterministic transformations. Do not assign Semantic Contract ownership, architecture/product decisions, cross-module implementation, complex debugging, complex test design, or public API/schema/permission changes to these lightweight Workers.

## Targeted max escalation

`reasoning_effort=max` is an exception escalation, not a default Worker setting.

Use it only for a specific task that an existing `high`/`xhigh` Worker has repeatedly failed, oscillated on, or become clearly blocked by. The parent creates a new, narrowly scoped max Worker; when possible, the predecessor first writes reusable context/handoff documents in the primary worktree as defined by [`../../coding/context-exchange.md`](../../coding/context-exchange.md), and the max Worker reads those documents instead of restarting project exploration from zero.

After the blocker is resolved, follow-on work returns to the normal `xhigh`/`high` tiers rather than keeping max for unrelated tasks.

A current Luna Session in Single-Session Coding Mode may create another Agent only for fresh verification, real parallelism, clearly degraded/overgrown current context, explicit isolation benefit, or targeted `max` escalation for a specific repeatedly blocked task. Project exploration, implementation, testing, long output, or generic task complexity are not exceptions.

## Profile constraints

- Do not silently replace a Coding role that this Profile binds to Luna with another model.
- If an independent Luna role is required but `gpt-5.6-luna` identity cannot be confirmed, the model cannot be selected explicitly, or the Host cannot satisfy the reasoning-effort tier required for that dispatch, stop the corresponding substantive Coding work and briefly report the block.
- Purely read-only, strictly bounded diagnosis may continue when Luna identity is confirmed but the Host cannot set reasoning effort. Do not use that exception to move complex project-state work back to the advanced parent model or to silently assign lightweight effort to a task whose Profile requires `high` or `xhigh`.
- Do not infer that an advanced parent model should absorb Primary Output merely because it is technically capable of implementation. The binding above is intentional deployment policy for Token I/O separation.

# Coding Child Reuse and Replacement

[English](delegation-child-reuse-replacement.md) | [简体中文](delegation-child-reuse-replacement_zh_cn.md)

This module owns authorized follow-up, repaired epochs, and reuse or replacement relations for created children. It does not define child creation, role allocation, Dispatch Preview, Worker boundaries, lifecycle states, or context transport.

## General rules

### Authorized reuse

Repair takes priority over replacement: reuse the same child for authorized follow-ups and repaired epochs. After an error or interruption, first attempt an authorized repair through the same child; otherwise report the blocker. Reuse must not create a recursive hierarchy or peer coordination.

### Replacement relation

Replacement is distinct from ordinary same-child reuse and is allowed only as a plan-level allocation change before `child_count` is locked. Keep the count selected for this conversation; do not ask a second count question or create, spawn, or hand off to a new child during preparation. Lock the count and satisfy route release before the child-creation owner creates the planned children. Once locked, if the same child cannot be safely reused, report the blocker and set the Multi-Agent route to `blocked`; do not create a replacement child. Replacement is not peer coordination or a recursive hierarchy. This module does not define handoff or context transport; locate those rules in [context exchange](context-exchange.md).

## Codex CLI / ChatGPT Desktop optimizations

No provider-specific optimization instructions at present; follow the general rules above.

## Claude Code CLI / Claude Desktop optimizations

Use `SendMessage` with the returned Agent ID for an authorized follow-up or repair of the same child. Calling `Agent` again creates another child and consumes another slot; do not use it for reuse after count locking.

## Related concepts

- [Coding Child Creation](delegation-child-creation.md) — locate child creation capability.
- [Coding Child Role Allocation](delegation-child-role-allocation.md) — locate slot and role allocation.
- [Coding Child Dispatch](delegation-child-dispatch.md) — locate material dispatch boundaries.
- [Coding Child Lifecycle](delegation-child-lifecycle.md) — locate child state and recovery ownership.
- [Coding Context Exchange](context-exchange.md) — locate handoff and context transport ownership.

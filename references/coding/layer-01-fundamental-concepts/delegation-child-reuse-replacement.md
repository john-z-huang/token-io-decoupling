# Coding Child Reuse and Replacement

[English](delegation-child-reuse-replacement.md) | [简体中文](delegation-child-reuse-replacement_zh_cn.md)

This module owns authorized follow-up, repaired epochs, and reuse or replacement relations for created children. It does not define child creation, role allocation, Dispatch Preview, Worker boundaries, lifecycle states, or context transport.

## Authorized reuse

Reuse the same child for authorized follow-ups and repaired epochs. After an error or interruption, reuse is allowed only for an authorized repair; otherwise report the blocker. Reuse must not create a recursive hierarchy or peer coordination.

## Replacement relation

Replacement is distinct from ordinary same-child reuse and follows the parent-controlled delegation lifecycle. This module does not define handoff or context transport; locate those rules in [context exchange](context-exchange.md).

## Related concepts

- [Coding Child Creation](delegation-child-creation.md) — locate child creation capability.
- [Coding Child Role Allocation](delegation-child-role-allocation.md) — locate slot and role allocation.
- [Coding Child Dispatch](delegation-child-dispatch.md) — locate material dispatch boundaries.
- [Coding Child Lifecycle](delegation-child-dispatch-lifecycle.md) — locate child state and recovery ownership.
- [Coding Context Exchange](context-exchange.md) — locate handoff and context transport ownership.

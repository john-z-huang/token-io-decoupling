# Coding Child Reuse and Replacement

[English](delegation-child-reuse-replacement.md) | [简体中文](delegation-child-reuse-replacement_zh_cn.md)

This module owns authorized follow-up, repaired epochs, and reuse or replacement relations for created children. It does not define child creation, role allocation, Dispatch Preview, Worker boundaries, lifecycle states, or context transport.

## Authorized reuse

Repair takes priority over replacement: reuse the same child for authorized follow-ups and repaired epochs. After an error or interruption, first attempt an authorized repair through the same child; otherwise report the blocker. Reuse must not create a recursive hierarchy or peer coordination.

## Replacement relation

Replacement is distinct from ordinary same-child reuse and is allowed only during the controlled preparation phase before `child_count` is locked. It consumes or updates the still-unlocked count budget; the parent must then lock the resulting count and re-satisfy the route's release conditions before the first Dispatch. Once the count is locked, if the same child cannot be safely reused, the parent must report the blocker and set the Multi-Agent route to `blocked`; it must not create a replacement child. Replacement is not peer coordination or a recursive hierarchy. This module does not define handoff or context transport; locate those rules in [context exchange](context-exchange.md).

## Related concepts

- [Coding Child Creation](delegation-child-creation.md) — locate child creation capability.
- [Coding Child Role Allocation](delegation-child-role-allocation.md) — locate slot and role allocation.
- [Coding Child Dispatch](delegation-child-dispatch.md) — locate material dispatch boundaries.
- [Coding Child Lifecycle](delegation-child-lifecycle.md) — locate child state and recovery ownership.
- [Coding Context Exchange](context-exchange.md) — locate handoff and context transport ownership.

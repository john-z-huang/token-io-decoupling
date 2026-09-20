# Coding Child Lifecycle

[English](delegation-child-lifecycle.md) | [简体中文](delegation-child-lifecycle_zh_cn.md)

This module owns persistence and lifecycle states for created Multi-Agent children. It consumes a child whose creation, allocation, and dispatch have already been handled by their owner concepts; it does not define creation, role allocation, Dispatch Preview, Worker boundaries, reuse/replacement, or context transport.

## Lifecycle states

Keep created children visible and persistent. Do not close, shut down, archive, delete, or remove them from the task panel. While pending or running, wait or send only authorized input. A child may become completed only after returning its final result and evidence.

## Error and interruption

On error or interruption, keep the original child state explicit, preserve its available evidence, and do not close it as cleanup without authorization. First attempt an authorized repair by reusing the same child. Only while `child_count` is not locked may the parent use the controlled replacement path. After count locking, if the same child cannot be safely reused, report the blocker and set the Multi-Agent route to `blocked`; do not create a replacement child. Authorized reuse or pre-lock replacement follows the corresponding owner concept.

## Related concepts

- [Coding Child Creation](delegation-child-creation.md) — locate child creation capability.
- [Coding Child Role Allocation](delegation-child-role-allocation.md) — locate slot and role allocation.
- [Coding Child Dispatch](delegation-child-dispatch.md) — locate Dispatch Preview and Worker boundary.
- [Coding Child Reuse and Replacement](delegation-child-reuse-replacement.md) — locate authorized repair and replacement relations.
- [Coding Context Exchange](context-exchange.md) — locate context transport ownership.

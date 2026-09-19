# Coding Child Creation

[English](delegation-child-creation.md) | [简体中文](delegation-child-creation_zh_cn.md)

This module owns the capability to create a Multi-Agent child. It consumes a released Multi-Agent state with a locked count and does not reopen mode or count confirmation. It does not define role allocation, Dispatch Preview, Worker boundaries, reuse or replacement, or lifecycle.

## Creation capability

Creating a child means using a real MultiAgentV1 or MultiAgentV2 spawn operation, not a peer chat or generic task. The runtime must expose a child identity, a parent-controlled send/return path, bounded waiting, and lifecycle status. The child receives a role, an Interaction Slice, authorized scope/mutations, return conditions, and required context. If any capability is missing or unverifiable, stop and report the block.

## Related concepts

- [Coding Child Lifecycle](delegation-child-dispatch-lifecycle.md) — locate child state ownership.
- [Coding Child Role Allocation](delegation-child-role-allocation.md) — locate slot and role allocation.
- [Coding Child Dispatch](delegation-child-dispatch.md) — locate material dispatch boundaries.
- [Coding Child Reuse and Replacement](delegation-child-reuse-replacement.md) — locate authorized reuse and replacement.
- [Coding Session Model](session-model.md) — locate role and Session ownership.
- [Coding Context Exchange](context-exchange.md) — locate required context transport ownership.

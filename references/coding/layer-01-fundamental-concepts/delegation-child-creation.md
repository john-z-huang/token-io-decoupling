# Coding Child Creation

[English](delegation-child-creation.md) | [简体中文](delegation-child-creation_zh_cn.md)

This module owns the only capability to create a Multi-Agent child. Its entry requires a released Multi-Agent state, a locked positive `child_count`, and exactly `child_count` locked planned allocations; each planned allocation may have `agent: unbound` before creation. It does not reopen mode or count confirmation. A plan-level replacement before count locking is not a creation capability and cannot create a child or consume a child slot. After successful creation, this owner writes each created agent identity and actual lifecycle back to its planned allocation; it does not change mode or count or create an extra slot. It does not define role allocation, Dispatch Preview, Worker boundaries, reuse or replacement, or lifecycle.

## Creation capability

Use the runtime's real parent-controlled child mechanism. On Local Codex, use the exposed MultiAgentV1/V2 spawn operation. On Local Claude Code, use the built-in `Agent` tool with an explicit eligible `subagent_type`, per-invocation model, bounded task prompt, and return conditions; the exact provider controls and unavailable equivalents are centralized in [Runtime and Model Provider Support](runtime-provider-support.md). Never use a peer chat, an untracked generic task, or an automatic built-in Explore/Plan agent as a persistent child. Require a child identity, parent-controlled return/resume path, bounded wait, and observable lifecycle. After creation, bind its actual identity and lifecycle to the planned allocation. Missing or unverifiable capabilities block creation; they do not change the mode or count.

## Related concepts

- [Coding Child Lifecycle](delegation-child-lifecycle.md) — locate child state ownership.
- [Coding Child Role Allocation](delegation-child-role-allocation.md) — locate slot and role allocation.
- [Coding Child Dispatch](delegation-child-dispatch.md) — locate material dispatch boundaries.
- [Coding Child Reuse and Replacement](delegation-child-reuse-replacement.md) — locate authorized reuse and replacement.
- [Coding Session Model](session-model.md) — locate role and Session ownership.
- [Coding Context Exchange](context-exchange.md) — locate required context transport ownership.

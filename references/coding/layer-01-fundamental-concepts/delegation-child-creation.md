# Coding Child Creation

[English](delegation-child-creation.md) | [简体中文](delegation-child-creation_zh_cn.md)

This module owns the only capability to create a Multi-Agent child. Its entry requires a released Multi-Agent state, a locked positive `child_count`, and exactly `child_count` locked planned allocations; each planned allocation may have `agent: unbound` before creation. It does not reopen mode or count confirmation. A plan-level replacement before count locking is not a creation capability and cannot create a child or consume a child slot. After successful creation, this owner writes each created agent identity and actual lifecycle back to its planned allocation; it does not change mode or count or create an extra slot. It does not define role allocation, Dispatch Preview, Worker boundaries, reuse or replacement, or lifecycle.

## General rules

### Creation capability

Use the runtime's real parent-controlled child mechanism. Never use a peer chat or an untracked generic task as a persistent child. Require a child identity, parent-controlled return/resume path, bounded wait, and observable lifecycle. After creation, bind its actual identity and lifecycle to the planned allocation. Missing or unverifiable capabilities block creation; they do not change the mode or count.

## Codex CLI / ChatGPT Desktop optimizations

On Local Codex, use the exposed MultiAgentV1/V2 spawn operation; apply model and capability bindings from [Runtime and Model Provider Support](runtime-provider-support.md).

## Claude Code CLI / Claude Desktop optimizations

On Local Claude Code, use the built-in `Agent` tool after count and allocation release. Specify `subagent_type` as `general-purpose` or a named custom subagent, an explicit eligible model, a bounded task prompt, and return conditions. Apply the model and effort bindings from [Runtime and Model Provider Support](runtime-provider-support.md); verify the effective model in `/tasks` when available because a blocked selection may fall back to an inherited model. Do not use built-in Explore/Plan agents as persistent children; they return no reusable agent ID.

The general `Agent` call has no per-invocation effort parameter. For role-specific Sonnet effort, use an authorized `.claude/agents/<name>.md` or `~/.claude/agents/<name>.md` definition with `name`, `description`, `model: sonnet`, the required `effort`, and a suitable tool allowlist. Otherwise explicitly set and verify the session `/effort` inherited by the child before launch; omit effort for Haiku. Prefer a named reusable subagent whose allowed tools exclude `Agent` and peer messaging to prevent recursive delegation. If a custom definition is outside the authorized mutation scope, use `general-purpose` only when its effective effort and tool boundary can be verified. Block the child role when a required binding or boundary cannot be verified.

## Related concepts

- [Coding Child Lifecycle](delegation-child-lifecycle.md) — locate child state ownership.
- [Coding Child Role Allocation](delegation-child-role-allocation.md) — locate slot and role allocation.
- [Coding Child Dispatch](delegation-child-dispatch.md) — locate material dispatch boundaries.
- [Coding Child Reuse and Replacement](delegation-child-reuse-replacement.md) — locate authorized reuse and replacement.
- [Coding Session Model](session-model.md) — locate role and Session ownership.
- [Coding Context Exchange](context-exchange.md) — locate required context transport ownership.

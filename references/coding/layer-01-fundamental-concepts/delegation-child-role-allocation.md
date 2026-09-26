# Coding Child Role Allocation

[English](delegation-child-role-allocation.md) | [简体中文](delegation-child-role-allocation_zh_cn.md)

This module owns slot and auxiliary-role allocation under a locked Multi-Agent count. It does not define child creation, Dispatch Preview, Worker boundaries, reuse or replacement, lifecycle, context transport, verification, or Git policies.

## General rules

### Allocation

Assign roles only within the locked, reserved count after bounded parent fact confirmation. A reserved slot may remain `role: unassigned` until its purpose is known; assign and release its role before child creation. With one child, assign Primary Output. Primary Output, Change Verification, Documentation/Comments & Git Operations, Context Bootstrap/Refresh, and other independent responsibilities each consume a separate slot. An authorized revision of an unbound slot is not a replacement child and must not exceed the count; after creation, its child identity remains bound. If no independent verifier or auxiliary role was allocated, use the current or already allocated Agent when safe, or report it unavailable; never simulate independence by relabeling same-Session work.

### Context Bootstrap/Refresh allocation

Assign Context Bootstrap/Refresh only when reuse is likely to outweigh setup: at least two independent downstream Workers, broad discovery plus three or more routed policy modules, or a source set roughly above 20k characters / 5k token-equivalents. Skip it for one small Worker or documentation-only fast paths. These are routing heuristics, not measured runtime or quality claims.

## Codex CLI / ChatGPT Desktop optimizations

Codex `.codex/agents/*.toml` profiles can name a planned role, but registering one never creates an Agent or changes a reserved slot's child identity. Select the role and its effective `model`/`model_reasoning_effort`/`sandbox_mode` within the locked budget; a configurable global concurrent-agent limit is separate from this Skill's total child-count gate. [OpenAI: custom subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents).

## Claude Code CLI / Claude Desktop optimizations

Claude Code custom subagent definitions in `.claude/agents/` or `~/.claude/agents/` may specialize a *planned* role through `description`, `tools`, `model`, and `effort`; defining or discovering such a file does not create an Agent instance or consume another locked slot. Assign any reusable role to a slot before the creation owner invokes `Agent`. The built-in Explore/Plan agents are one-shot, so do not allocate them as durable Primary Output, verifier, or follow-up roles. Preserve the locked count even if the host exposes additional built-in agents. [Anthropic: subagent scopes and one-shot agents](https://code.claude.com/docs/en/sub-agents).

## Related concepts

- [Coding Child Creation](delegation-child-creation.md) — locate the child creation owner.
- [Coding Child Dispatch](delegation-child-dispatch.md) — locate material dispatch boundaries.
- [Coding Child Lifecycle](delegation-child-lifecycle.md) — locate child state ownership.
- [Coding Child Reuse and Replacement](delegation-child-reuse-replacement.md) — locate authorized reuse and replacement.
- [Coding Context Exchange](context-exchange.md) — locate context transport ownership.

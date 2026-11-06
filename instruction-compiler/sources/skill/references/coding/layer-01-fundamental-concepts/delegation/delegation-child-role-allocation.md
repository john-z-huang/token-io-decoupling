# Coding Child Role Allocation

[English](delegation-child-role-allocation.md) | [简体中文](delegation-child-role-allocation_zh_cn.md)

This module owns slot and auxiliary-role allocation under a locked Multi-Agent count. It does not define child creation, Dispatch Preview, Worker boundaries, reuse or replacement, lifecycle, context transport, verification, or Git policies.

## General rules

### Allocation

Reserve the locked count as unbound, unassigned slots before task context and Decision are complete. That reservation stage does not select or assign Primary Output merely because only one slot exists; the slots remain `role: unassigned`, `slice_status: pending`, and `agent: unbound`. After Root has reviewed current task context and Decision, use [Child Role Selection](child-role-selection.md) to identify one role for the proposed child; an explicit user instruction skips role-selection advice but not Root's role and policy checks. If context generation or advice is unavailable, Root may decide directly from the current owner and verified facts. Then reserve the selected role in one unassigned slot and release its role and concrete slice before child creation. Ordinary non-Skill documentation remains parent-authored and does not consume a reserved slot, including when code work is also present. Each independent role consumes a separate slot. A role on an unbound, not-yet-created slot may be revised only as a parent-authorized plan update within the current count, and the new role must not be assigned to any other reserved or created child. Once a child is created, its role and identity remain bound and cannot be recycled or replaced. If no independent verifier or auxiliary role was allocated, use the current or already allocated Agent when safe, or report it unavailable; never simulate independence by relabeling same-Session work.

### Context Bootstrap/Refresh allocation

Assign Context Bootstrap/Refresh only when reuse is likely to outweigh setup: at least two independent downstream Workers, broad discovery plus three or more routed policy modules, or a source set roughly above 20k characters / 5k token-equivalents. Skip it for one small Worker or documentation-only fast paths. These are routing heuristics, not measured runtime or quality claims.

## Codex CLI / ChatGPT Desktop optimizations

Codex `.codex/agents/*.toml` profiles can name a planned role, but registering one never creates an Agent or changes a reserved slot's child identity. Select the role and its effective `model`/`model_reasoning_effort`/`sandbox_mode` within the locked budget; a configurable global concurrent-agent limit is separate from this Skill's total child-count gate. [OpenAI: custom subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents).

When matching a released slot to a Codex role, distinguish the built-in `explorer` (read-heavy), `worker` (execution), and `default` (fallback) from a reviewed project/user custom profile. A profile choice sets an intended tool/model policy but does not bind an Agent ID, create a Session, or authorize a new slot. Resolve the effective parent-turn overrides before treating `sandbox_mode: read-only` as the verifier's or context-reader's actual restriction. If a child needs an approval the non-interactive host cannot surface, mark the dependent slice blocked instead of assigning a new profile/child to evade it. [OpenAI: native roles and approvals](https://learn.chatgpt.com/docs/agent-configuration/subagents).

## Claude Code CLI / Claude Desktop optimizations

Claude Code custom subagent definitions in `.claude/agents/` or `~/.claude/agents/` may specialize a *planned* role through `description`, `tools`, `model`, and `effort`; defining or discovering such a file does not create an Agent instance or consume another locked slot. Assign any reusable role to a slot before the creation owner invokes `Agent`. The built-in Explore/Plan agents are one-shot, so do not allocate them as durable Primary Output, verifier, or follow-up roles. Preserve the locked count even if the host exposes additional built-in agents. [Anthropic: subagent scopes and one-shot agents](https://code.claude.com/docs/en/sub-agents).

## Related concepts

- [Coding Child Creation](delegation-child-creation.md) — locate the child creation owner.
- [Coding Child Role Selection](child-role-selection.md) — locate the decision that precedes role reservation.
- [Coding Child Dispatch](delegation-child-dispatch.md) — locate material dispatch boundaries.
- [Coding Child Lifecycle](delegation-child-lifecycle.md) — locate child state ownership.
- [Coding Child Reuse and Replacement](delegation-child-reuse-replacement.md) — locate authorized reuse and replacement.
- [Coding Context Exchange](../context-exchange/context-exchange.md) — locate context transport ownership.

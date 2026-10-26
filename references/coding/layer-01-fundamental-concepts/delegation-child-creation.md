# Coding Child Creation

[English](delegation-child-creation.md) | [简体中文](delegation-child-creation_zh_cn.md)

This module owns the only capability to create a Multi-Agent child. It consumes a released mode/count gate, a reserved slot with an assigned role, an eligible output type, and a released concrete Interaction Slice; it does not reconfirm mode/count, assign roles, or define replacement or lifecycle policy. Creation writes back only the actual Agent identity and initial lifecycle, without adding a slot.

## General rules

### Creation capability

As part of creating a child, the parent must select and set the role-required model and reasoning-effort controls in the child-creation operation, using applicable runtime bindings. If the operation cannot set or establish the required configuration, block child creation. This check is limited to creation. If the operation accepts the required controls but exposes no additional runtime-resolved observation, task work can proceed without one. Do not ask the child to inspect or report its own model or effort.
Use the runtime's real parent-controlled child mechanism. Before creating a child, require the released Multi-Agent gate, locked positive count, a reserved unbound allocation with an assigned role, and a current `slice_status: released` Interaction Slice with explicit objective, allowed paths/mutations, return conditions, and memo dispatch switch. Include the locked [session audit visibility](session-audit-visibility.md) values in the released task snapshot so the Worker can apply its message visibility and summary cadence. The output must be actual code/configuration implementation or authorship/editing of this Skill's instructions or reference documents. Ordinary non-Skill documentation, including documentation accompanying code changes, is authored by the root parent and must not trigger child creation. Do not initialize a child at session start or merely because Multi-Agent was selected. Do not treat a reserved slot or released mode alone as child-creation authorization. Never use a peer chat or an untracked generic task as a persistent child. Require a child identity, parent-controlled return/resume path, bounded wait, and observable lifecycle. After creation, bind its actual identity and lifecycle to the same allocation; never free the slot for another child. Missing or unverifiable capabilities block creation; they do not change mode or count.

## Codex CLI / ChatGPT Desktop optimizations

On Local Codex, use the exposed MultiAgentV1/V2 spawn operation; apply model and capability bindings from [Runtime and Model Provider Support](runtime-provider-support.md).

For Codex custom children, an authorized `.codex/agents/<name>.toml` can specify `name`, `description`, `developer_instructions`, `model`, `model_reasoning_effort`, `sandbox_mode`, and `mcp_servers`. The parent must set the role-required model and effort in the parent-controlled spawn operation; block creation if it cannot apply the required controls. If the operation accepts them without exposing an additional runtime-resolved observation, proceed without requiring one. Do not ask the child to inspect or report these settings. Registering a profile is not spawning or allocating a new child, and a host-wide concurrency limit is not this conversation's locked child count. Claude's `.claude/agents/*.md` frontmatter is not a Codex configuration format. [OpenAI: custom subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents).

### Native child profiles and inherited permissions

Current local Codex exposes built-in `default`, `worker`, and `explorer` profiles; a reviewed custom profile under `.codex/agents/` or `~/.codex/agents/` may specialize a released role. Confirm `agents.enabled` and the actual spawn capability before child creation. Set the role-required model and effort in the spawn operation, resolving applicable custom-file and runtime precedence there; block creation if the required controls cannot be set or established. Check inherited `sandbox_mode`/`mcp_servers`/`skills.config` as a separate permission boundary. Live parent `/permissions` or CLI sandbox overrides can be reapplied to a spawned child; do not treat a read-only TOML default as an enforcement proof. The runtime's `agents.max_concurrent_threads_per_session` is a simultaneous-thread cap, **not** the conversation's locked total child count. [OpenAI: subagent profiles, precedence and permissions](https://learn.chatgpt.com/docs/agent-configuration/subagents).

## Claude Code CLI / Claude Desktop optimizations

On Local Claude Code, use the built-in `Agent` tool after count and allocation release. Specify `subagent_type` as `general-purpose` or a named custom subagent, the role-required model and effort, a bounded task prompt, and return conditions. Apply the bindings from [Runtime and Model Provider Support](runtime-provider-support.md); block creation if the operation cannot set or establish the required controls. If the operation accepts the controls, proceed without requiring an additional runtime-resolved observation. Do not ask the child to inspect or report its own settings. Do not use built-in Explore/Plan agents as persistent children; they return no reusable agent ID.

The general `Agent` call has no per-invocation effort parameter. For role-specific Sonnet effort, use an authorized `.claude/agents/<name>.md` or `~/.claude/agents/<name>.md` definition with `name`, `description`, `model: sonnet`, the required `effort`, and a suitable tool allowlist. Otherwise explicitly set the parent session `/effort` before launch; omit effort for Haiku. Prefer a named reusable subagent whose allowed tools exclude `Agent` and peer messaging to prevent recursive delegation. If a custom definition is outside the authorized mutation scope, use `general-purpose` only when the creation operation can set or establish the required model and effort. Block child creation if required controls cannot be applied.

### Native subagent definition and creation guard

When the authorized role repeats across slices, prefer a reviewed project or personal custom agent definition in `.claude/agents/` or `~/.claude/agents/`; use `name`/`description` for selection and explicit `tools`/`disallowedTools` and `maxTurns` to bound it. Omit `Agent` from a worker's allowed tools (or explicitly disallow it) and exclude peer-messaging tools; current Claude Code can otherwise let a subagent spawn nested agents. Use `skills` to preload only references essential to that role, not the entire Skill or unrelated concept owners. A plugin-shipped agent ignores its own `hooks`, `mcpServers`, and `permissionMode` frontmatter; use an authorized project/user agent or session settings if those controls are required.

The actual `Agent` call must still wait for the existing released slice and reserved unbound allocation. A `SubagentStart` hook can inject context but **cannot block creation**, so it is not a substitute for a pre-creation gate. In Claude Desktop, call `Agent` only if the active Session directly exposes and authorizes that built-in tool; otherwise record it as unavailable and block the dependent slice. Resolve the effective model using creation-time controls and the runtime owner rather than inferring tool availability from the app identity.

Official references: [custom subagents and frontmatter](https://code.claude.com/docs/en/sub-agents), [SubagentStart hook](https://code.claude.com/docs/en/hooks).

When available on a reviewed project/user custom subagent, `background` and `isolation: worktree` are execution controls for an already authorized slot. Background children can have restricted interactive permission/tool access: if the released task needs those tools, use an available foreground invocation instead of silently dropping requirements. Worktree isolation separates repository copies, not the parent Context root's per-Worker path permissions. [Anthropic: subagents](https://code.claude.com/docs/en/sub-agents).

## Related concepts

- [Coding Child Lifecycle](delegation-child-lifecycle.md) — locate child state ownership.
- [Coding Child Role Allocation](delegation-child-role-allocation.md) — locate slot and role allocation.
- [Coding Child Dispatch](delegation-child-dispatch.md) — locate material dispatch boundaries.
- [Coding Child Reuse and Replacement](delegation-child-reuse-replacement.md) — locate authorized reuse and replacement.
- [Coding Session Model](session-model.md) — locate role and Session ownership.
- [Coding Context Exchange](context-exchange.md) — locate required context transport ownership.
- [Coding Session Audit Visibility](session-audit-visibility.md) — locate session audit configuration.

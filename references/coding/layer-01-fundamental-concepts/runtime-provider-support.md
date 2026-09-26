# Coding Runtime and Model Provider Support

[English](runtime-provider-support.md) | [简体中文](runtime-provider-support_zh_cn.md)

This module owns the supported runtime branches, their identifying evidence, and branch-specific model controls and profile bindings. It does not choose the task mode, create Sessions, or treat a model name alone as proof of the runtime.

## General rules

### Supported runtime branches

- **Local Codex**: the task exposes local filesystem/shell or worktree capabilities and Codex Agent tools.
- **Local Claude Code**: the task explicitly exposes a Claude Code Session together with local filesystem/shell or worktree capabilities.
- **ChatGPT Work**: the task exposes Work Sessions/connectors/files, but local execution is not implied.
- **Standard ChatGPT**: do not assume local execution or independent Sessions unless explicitly exposed.

If the available metadata cannot distinguish these branches, use this exact fallback question: `I cannot determine the current runtime environment from the available metadata. In your next instruction, explicitly state whether it is "local Codex", "local Claude Code", "ChatGPT Work", or "standard ChatGPT", then resume.`

## Codex CLI / ChatGPT Desktop optimizations

- On Local Codex, use the exposed model/Session controls and restart after changing global instructions, overrides, the Skill, or repository instructions.
- On ChatGPT Work, use only explicitly exposed models, Sessions, files, connectors, and execution tools.
- On Standard ChatGPT, do not assume local execution, Git, worktrees, or independent Sessions.

### Local Codex independent-Session model profile

For independent role assignments on Local Codex, these are required bindings, not product-wide availability claims:

| Role | Model | Reasoning parameter |
| --- | --- | --- |
| Primary Output | `gpt-6-luna` | `medium` |
| Change Verification | `gpt-6-luna` | `medium` |
| Documentation/Comments & Git Operations | `gpt-6-luna` | `medium` |
| Context Bootstrap/Refresh | `gpt-6-luna` | `medium`; `low` for deterministic refreshes |

The capability inventory must verify each assigned binding's exposed model identity and reasoning parameter. If a required binding is missing or unknown, record it in `unavailable_capabilities` and block the dependent slice or route. Raise only the affected slice to `high` when concrete complexity or repeated failure/blockage warrants it; return to the normal tier afterward. Escalate to `max` only when `high` was insufficient and repeated failure/blockage continues, then return to the normal tier.

## Claude Code CLI / Claude Desktop optimizations

- On Local Claude Code, record the exact model identifier or alias exposed by the active Session and use only its exposed parameter controls. Apply the Claude Code model selection below; do not infer a model or assume a reasoning control.

### Local Claude Code model selection

Use only the `sonnet` and `haiku` aliases, or verified model identifiers in the `claude-sonnet-*` and `claude-haiku-*` families. Before using an active Session or launching an Agent, confirm the effective model resolves to one of these families. Never launch an Agent with `claude-opus-*`, an Opus alias, or any model above or outside the Sonnet/Haiku families. Do not use an unresolved default, inherited model, or fallback as a substitute for this check.

- **Single-Agent Coding:** keep one active model for all logical phases. Use Sonnet for material coding, decisions, repair, or verification; Haiku is allowed for simple, bounded, mechanically checkable work. If the active model is ineligible or insufficient for the task and an allowed switch is unavailable, block the dependent work rather than continuing on that model.
- **Multi-Agent Coding, only after its mode and capability gates release it:** assign Sonnet to Primary Output, Change Verification, Documentation/Comments & Git Operations, and Context Bootstrap. Assign Haiku only to a deterministic Context Refresh; use Sonnet when the refresh requires semantic judgment. Confirm each Agent's effective model before launch. These bindings do not authorize creating independent Sessions or changing the locked child count.

For Claude Code, apply these effort bindings only when the selected Sonnet version exposes the stated level. Haiku does not support an effort parameter; do not set or claim one for Haiku.

| Role | Model | Effort level |
| --- | --- | --- |
| Primary Output | `sonnet` | `medium` |
| Change Verification | `sonnet` | `medium` |
| Documentation/Comments & Git Operations | `sonnet` | `medium` |
| Context Bootstrap/Refresh | `sonnet` | `medium`; `low` for deterministic refreshes |
| Deterministic Context Refresh only | `haiku` | Not supported; omit effort |

For Single-Agent Coding, use Sonnet at `medium` for material work, with the same affected-slice escalation rule below. A Haiku-only Single-Agent task must remain simple, bounded, and mechanically checkable; it has no effort control. Verify the effective model and effort before relying on a binding, including any organization cap or inherited setting. Raise only the affected Sonnet slice to `high` for concrete complexity or repeated failure/blockage, then restore `medium`. Use `max` only if `high` was insufficient and repeated failure/blockage continues, and only when the active Sonnet model exposes `max`; then restore `medium`. Do not select `xhigh` or `ultracode` in this profile. If the required model or supported effort binding is missing or cannot be verified, record it in `unavailable_capabilities` and block the dependent slice or route; do not switch to Opus or a higher model.

### Runtime tool correspondence

Use this table for provider-specific operations; the workflow concepts remain shared.

| Codex-specific control used by this Skill | Claude Code correspondence | Required handling on Claude Code |
| --- | --- | --- |
| Non-blocking timed user-input tool for the 15-second mode question | No documented native `AskUserQuestion` timeout or equivalent asynchronous reply tool | Send the mode question as ordinary progress text, use a wall-clock timer for 15 seconds while the turn remains active, and inspect any reply the host exposes by the deadline. Do not call blocking `AskUserQuestion`. If the host cannot surface a reply during the active turn, record that limitation and apply the default after 15 seconds; do not wait indefinitely. |
| Parent task panel / task-control record | No durable equivalent to the Codex parent task panel. `/tasks` shows subagent runs only temporarily. | Keep the structured mode/count and slice record in the parent conversation; read it back before route release. Do not use `/tasks` as the canonical record. |
| `MultiAgentV1/V2` child spawn | Built-in `Agent` tool | After the released count and allocation, invoke `Agent` with an explicit `subagent_type` (`general-purpose` or a named custom subagent), `model: sonnet` for material roles or `model: haiku` only for deterministic refresh, and a bounded task prompt. Verify the effective model in `/tasks` when available; a blocked model may fall back to an inherited one. Never use Explore or Plan as a persistent child because they return no reusable agent ID. |
| Codex reasoning parameter per spawned child | Custom subagent frontmatter `effort`, or an explicitly set session `/effort` inherited by the child; no general per-invocation `Agent` effort parameter | For a role-specific Sonnet effort, use an authorized `.claude/agents/<name>.md` or `~/.claude/agents/<name>.md` definition with `name`, `description`, `model: sonnet`, `effort: medium` and an appropriate tool allowlist. When no custom definition is needed, set and verify the Sonnet session effort before launch. Omit effort for Haiku. If the required effective effort cannot be verified, block that binding. |
| Codex send/wait/status lifecycle | `SendMessage` to the returned agent ID, `Agent` result, and `/tasks` while available | Save the returned ID in the parent record, wait for the result with a bounded runtime wait, and use `SendMessage` to resume that same child. A new `Agent` invocation creates a new child and consumes another slot. Keep completed/error state in the parent record after `/tasks` stops showing it. |
| Codex independent child Session / task UI | Claude Code subagent has its own context inside the parent session; no identical independent Codex task UI | Treat the subagent as the allocated child context, return only to the parent, and report its actual isolation and verification independence accurately. Do not create an agent team or peer channel as a substitute. |
| Codex worktree and tool-scope controls | Claude Code `EnterWorktree`/`ExitWorktree` or custom-agent `isolation: worktree`, plus `tools`/`disallowedTools` | Use these only when the current task explicitly releases worktree isolation or tool restrictions. They do not by themselves enforce named filesystem path permissions; if a required path boundary cannot be enforced, block the dependent slice. Otherwise use the normal shared worktree and ordinary Claude Code tools. |
| Codex-specific restart after policy changes | No identical hot-reload guarantee | Start a fresh Claude Code session after changing `CLAUDE.md`, Skill, or agent definitions when the current session cannot prove it loaded the changed instructions. Do not assume `/tasks` or `/agents` reloads them. |

For a reusable Claude Code child, prefer a named custom subagent that denies `Agent` and peer messaging tools, preserving the no-recursive-child rule. If a custom definition is outside the authorized mutation scope, use the built-in `general-purpose` type with explicit model and a bounded prompt only when its effective effort and tool boundary can be verified; otherwise block that child role. No Claude Code control is required for a Codex-only UI convenience when the parent record and result already provide the needed evidence.

## Related concepts

- [Coding Session Model](session-model.md) — locate Single-Agent and Multi-Agent Session mapping.
- [Coding Session Role Ownership](session-role-ownership.md) — locate role responsibilities.

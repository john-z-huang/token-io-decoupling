# Coding Runtime and Model Provider Support

[English](runtime-provider-support.md) | [简体中文](runtime-provider-support_zh_cn.md)

This module owns the supported runtime branches, their identifying evidence, and branch-specific model controls and profile bindings. It does not choose the task mode, create Sessions, or treat a model name alone as proof of the runtime.

## Supported runtime branches

- **Local Codex**: the task exposes local filesystem/shell or worktree capabilities and Codex Agent tools.
- **Local Claude Code**: the task explicitly exposes a Claude Code Session together with local filesystem/shell or worktree capabilities.
- **ChatGPT Work**: the task exposes Work Sessions/connectors/files, but local execution is not implied.
- **Standard ChatGPT**: do not assume local execution or independent Sessions unless explicitly exposed.

If the available metadata cannot distinguish these branches, use this exact fallback question: `I cannot determine the current runtime environment from the available metadata. In your next instruction, explicitly state whether it is "local Codex", "local Claude Code", "ChatGPT Work", or "standard ChatGPT", then resume.`

## Branch-specific capability use

- On Local Codex, use the exposed model/Session controls and restart after changing global instructions, overrides, the Skill, or repository instructions.
- On Local Claude Code, record the exact model identifier or alias exposed by the active Session and use only its exposed parameter controls. Apply the Claude Code model selection below; do not infer a model or assume a reasoning control.
- On ChatGPT Work, use only explicitly exposed models, Sessions, files, connectors, and execution tools.
- On Standard ChatGPT, do not assume local execution, Git, worktrees, or independent Sessions.

## Local Claude Code model selection

Use only the `sonnet` and `haiku` aliases, or verified model identifiers in the `claude-sonnet-*` and `claude-haiku-*` families. Claude Code spells the smaller family `haiku`, not `hiku`. Before using an active Session or launching an Agent, confirm the effective model resolves to one of these families. Never launch an Agent with `claude-opus-*`, an Opus alias, or any model above or outside the Sonnet/Haiku families. Do not use an unresolved default, inherited model, or fallback as a substitute for this check.

- **Single-Agent Coding:** keep one active model for all logical phases. Use Sonnet for material coding, decisions, repair, or verification; Haiku is allowed for simple, bounded, mechanically checkable work. If the active model is ineligible or insufficient for the task and an allowed switch is unavailable, block the dependent work rather than continuing on that model.
- **Multi-Agent Coding, only after its mode and capability gates release it:** assign Sonnet to Primary Output, Change Verification, Documentation/Comments & Git Operations, and Context Bootstrap. Assign Haiku only to a deterministic Context Refresh; use Sonnet when the refresh requires semantic judgment. Confirm each Agent's effective model before launch. These bindings do not authorize creating independent Sessions or changing the locked child count.

This Claude Code profile sets no reasoning parameter. Use a parameter only when the current surface exposes and the selected task requires it. If a required Sonnet or Haiku binding is unavailable or cannot be verified, record it in `unavailable_capabilities` and block the dependent slice or route; do not escalate to Opus or a higher model.

## Local Codex independent-Session model profile

For independent role assignments on Local Codex, these are required bindings, not product-wide availability claims:

| Role | Model | Reasoning parameter |
| --- | --- | --- |
| Primary Output | `gpt-6-luna` | `medium` |
| Change Verification | `gpt-6-luna` | `medium` |
| Documentation/Comments & Git Operations | `gpt-6-luna` | `medium` |
| Context Bootstrap/Refresh | `gpt-6-luna` | `medium`; `low` for deterministic refreshes |

The capability inventory must verify each assigned binding's exposed model identity and reasoning parameter. If a required binding is missing or unknown, record it in `unavailable_capabilities` and block the dependent slice or route. Raise only the affected slice to `high` when concrete complexity or repeated failure/blockage warrants it; return to the normal tier afterward. Escalate to `max` only when `high` was insufficient and repeated failure/blockage continues, then return to the normal tier.

## Related concepts

- [Coding Session Model](session-model.md) — locate Single-Agent and Multi-Agent Session mapping.
- [Coding Session Role Ownership](session-role-ownership.md) — locate role responsibilities.

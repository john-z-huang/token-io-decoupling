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
- On Local Claude Code, record the exact Claude model identifier or alias exposed by the active Session and use only its exposed parameter controls. When the current Session handles all logical phases, it uses that active model. Do not infer a model or assume a reasoning control. This support does not declare a Claude Code independent-Session role profile.
- On ChatGPT Work, use only explicitly exposed models, Sessions, files, connectors, and execution tools.
- On Standard ChatGPT, do not assume local execution, Git, worktrees, or independent Sessions.

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

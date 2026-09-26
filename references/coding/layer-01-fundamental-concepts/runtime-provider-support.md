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

### Desktop sessions and exposed tools

For ChatGPT Desktop and Claude Desktop, use only tools, commands, or APIs directly exposed and authorized for the current Agent Session. Identify the active runtime and its capabilities from Session metadata and the exposed tool inventory. If a necessary step is only available through a channel that repository instructions prohibit, stop the Skill task and report the blocker; do not route the step through an adapter or helper. When an optional capability is absent, block only the dependent route or slice.

## Codex CLI / ChatGPT Desktop optimizations

- On Local Codex, use the exposed model/Session controls and restart after changing global instructions, overrides, the Skill, or repository instructions.

### Local Codex independent-Session model profile

For independent role assignments on Local Codex, these are required bindings, not product-wide availability claims:

| Role | Model | Reasoning parameter |
| --- | --- | --- |
| Primary Output | `gpt-6-luna` | `medium` |
| Change Verification | `gpt-6-luna` | `medium` |
| Documentation/Comments & Git Operations | `gpt-6-luna` | `medium` |
| Context Bootstrap/Refresh | `gpt-6-luna` | `medium`; `low` for deterministic refreshes |

The capability inventory must verify each assigned binding's exposed model identity and reasoning parameter. If a required binding is missing or unknown, record it in `unavailable_capabilities` and block the dependent slice or route. Raise only the affected slice to `high` when concrete complexity or repeated failure/blockage warrants it; return to the normal tier afterward. Escalate to `max` only when `high` was insufficient and repeated failure/blockage continues, then return to the normal tier.

### Codex instruction-loading correspondence

Codex natively discovers `AGENTS.md` along its instruction hierarchy; do not create a `CLAUDE.md` copy or require Claude Code's `@AGENTS.md` import for Codex. After an authorized instruction change, verify the running Session actually loaded the current instructions or restart it; a child-status view is not proof of instruction freshness. [OpenAI: AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md).

### Desktop runtime identification

ChatGPT Desktop can host **Chat**, **Work**, and **Codex** Sessions. Use Session metadata and exposed tools to identify the active runtime before treating it as local Codex: Work has its own hosted Agent workflows, and a Chat or Work Session does not imply a local shell or a child of a project-bound Codex Session. A quick Codex Session is not automatically bound to the project. In Remote sessions, the repository remains on the connected host. [OpenAI: desktop experiences](https://learn.chatgpt.com/docs/use-chatgpt), [OpenAI: subagent availability](https://learn.chatgpt.com/docs/agent-configuration/subagents), [OpenAI: worktree host](https://learn.chatgpt.com/docs/environments/git-worktrees).

### Effective local configuration

Codex CLI, IDE, and Codex in the ChatGPT desktop app can share the active host's `~/.codex/config.toml` and trusted project `.codex/config.toml`; project-local config, rules, and hooks are skipped for an untrusted project. Several config layers can apply at once — session flags and CLI overrides, trusted project `.codex/config.toml` files, the selected profile, user `~/.codex/config.toml`, managed policy such as system config, MDM, or delivered organization requirements, plugins, and packaged defaults — and the host decides their effective precedence rather than the order in which they are named here. Resolve the active value from the running Session instead of assuming a fixed order: in a CLI Session that exposes them, run `/status` to inspect the active model, approval policy, and writable roots, then `/debug-config`, which prints the config-layer stack in precedence order together with the active requirements and policy sources. If these commands are unavailable, use only settings and metadata directly exposed to the current Session; mark hidden layers unavailable instead of guessing. A spawned subagent also inherits the parent turn's live permission/sandbox overrides. Check `AGENTS.override.md`, nested instruction precedence and `project_doc_max_bytes` before claiming a large instruction file loaded in full. These checks do not change this Skill's fixed role-model profile. [OpenAI: config precedence](https://learn.chatgpt.com/docs/config-file/config-basic), [OpenAI: inspect settings](https://learn.chatgpt.com/docs/developer-settings), [OpenAI: instruction discovery](https://learn.chatgpt.com/docs/agent-configuration/agents-md), [OpenAI: child overrides](https://learn.chatgpt.com/docs/agent-configuration/subagents).

## Claude Code CLI / Claude Desktop optimizations

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

After changing `CLAUDE.md`, this Skill, or an agent definition, start a new Claude Code session if the current session cannot prove it loaded the changed instructions; `/tasks` and `/agents` do not establish that proof.

### Claude Code Plan-mode startup and Session boundary

`claude --permission-mode plan` selects read-only Plan mode **when launching a new Claude Code CLI Session**. It is not a command for switching an already running Parent or Worker Session into Plan mode: do not invoke it from the active Session's shell merely to plan the current slice. For an existing Session, use only a Plan-mode control actually exposed and authorized within that same Session; if none exists, follow the general bounded planning and decision process without claiming Plan-mode protection. A separately launched CLI Session is not the recorded Parent or an allocated Child and does not inherit this Skill's locked mode/count, released Interaction Slice, or live task record by virtue of its launch flags. Plan-mode tool permissions do not authorize implementation or change the Skill's Contract and release gates. [Anthropic: CLI permission mode](https://code.claude.com/docs/en/cli-reference), [Anthropic: Plan mode](https://code.claude.com/docs/en/common-workflows).

### Claude Desktop connectors and tool inventory

Claude Desktop Sessions can expose Claude Code capabilities, remote connectors, or local MCP tools; the app identity alone does not establish which are available. Use `Agent`, `SendMessage`, `/tasks`, shell, or hooks only when the current Session directly exposes them. For hosted resources, call an authorized remote connector; for machine-local resources, use an authorized local MCP/desktop-extension tool. Check the exposed tool's read/write scope before use. A connector provides data or actions, not an independent Coding Session, a parent-controlled Agent identity, or a locked child slot. If a required capability is absent, record it and block the dependent route or slice.

Claude Desktop can load local MCP definitions from `claude_desktop_config.json`; the standalone CLI does not read that file automatically. Inspect the MCP tools exposed to each Session instead of assuming the Desktop and CLI tool inventories match. Do not treat CLI `--allowedTools` or `--disallowedTools` arguments as controls on a Desktop Session. [Anthropic: Desktop local MCP](https://support.claude.com/en/articles/10949351-getting-started-with-local-mcp-servers-on-claude-desktop), [Anthropic: remote connectors](https://support.claude.com/en/articles/11725091-when-to-use-desktop-and-web-connectors).

### Claude Code instruction loading

In Claude Code, project instructions are loaded from `CLAUDE.md`. When a repository's canonical rules live in `AGENTS.md`, an authorized `CLAUDE.md` can import them with `@AGENTS.md` instead of copying their policy. Use `/context` to inspect loaded memory/instruction files; neither this view nor `CLAUDE.md` is the live parent mode/count record. A remote Desktop MCP connector executes through Anthropic's infrastructure, not through the desktop's localhost, so verify its actual network reachability and permissions. [Anthropic: memory](https://code.claude.com/docs/en/memory), [Anthropic: remote MCP](https://support.claude.com/en/articles/11175166-get-started-with-custom-connectors-using-remote-mcp).

## Related concepts

- [Coding Session Model](session-model.md) — locate Single-Agent and Multi-Agent Session mapping.
- [Coding Session Role Ownership](session-role-ownership.md) — locate role responsibilities.
- [Coding Delegation Mode Confirmation](delegation-mode-confirmation.md) — locate timed mode selection.
- [Coding Child Creation](delegation-child-creation.md) — locate runtime child-launch controls.
- [Coding Child Reuse and Replacement](delegation-child-reuse-replacement.md) — locate child follow-up controls.
- [Coding Delegation State Record](delegation-state-record.md) — locate the canonical parent record.
- [Coding Child Lifecycle](delegation-child-lifecycle.md) — locate runtime status observation.
- [Coding Context Exchange Workspace Boundary](context-exchange-workspace-boundary.md) — locate worktree and tool-scope controls.

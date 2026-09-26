# Coding Session Context Firewall

[English](session-context-firewall.md) | [简体中文](session-context-firewall_zh_cn.md)

This module owns the Context Firewall: raw-state ingress limits, bounded inspection, fact-return boundaries, and ephemeral project localization. It does not define role responsibilities, Session semantics, file-backed context transport, or workflow acceptance.

## General rules

### Raw-state ingress

In a multi-Session Coding run, the input-side Session reads only bounded, read-only environment and code evidence needed for the prerequisite confirmations owned by [session role ownership](session-role-ownership.md), not an open-ended repository scan. Primary Output consumes further source/configuration state only within released scope; Change Verification consumes final-state evidence; Documentation/Comments & Git Operations consumes Git state and approved documentation scope. Each returns only next-decision facts and exact source pointers.

Raw-state ingress is bounded by potential output volume, state sensitivity, and repository impact, not the command name. A single Session has no cross-Session firewall but still reads progressively and compresses raw state.

### Semantic ownership and ephemeral localization

The firewall limits raw-state ingress without transferring semantic authority; follow [session role ownership](session-role-ownership.md). Temporary project-localization facts belong to the observing Session and are not promoted to long-lived Contract state.

## Codex CLI / ChatGPT Desktop optimizations

Codex custom agent profiles may narrow source/tool exposure with `sandbox_mode: read-only` and selected `mcp_servers`; `developer_instructions` can request bounded source pointers but is not a permission boundary. Inspect inherited settings because omitted custom-agent fields inherit the parent. These settings are not Claude's `tools`/`disallowedTools` frontmatter and do not imply Claude Desktop Chat's connector Tool-access mode. [OpenAI: custom subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents).

### Local bounded tools and Skill/MCP disclosure

Use the runtime's exposed local code-search/file-reading tools for targeted symbols and small source ranges, returning stable paths and evidence pointers instead of complete build logs or recursive repository dumps. For Codex role-specific access, a reviewed custom agent may set `sandbox_mode: read-only` and narrow `mcp_servers`; an omitted key can inherit parent settings and a live permission override can affect the spawned child. Local Codex skills reveal metadata first, load `SKILL.md` when selected and references only on demand; select only concept owners needed by the current slice. The CLI/IDE/Desktop Codex host can share MCP configuration; `/mcp` verifies available connections. Do not treat a plugin or a separate Chat Session's tool access as a separate Codex child or a permission grant. [OpenAI: skills progressive disclosure](https://learn.chatgpt.com/docs/build-skills), [OpenAI: MCP host configuration](https://learn.chatgpt.com/docs/extend/mcp), [OpenAI: custom agents](https://learn.chatgpt.com/docs/agent-configuration/subagents).

## Claude Code CLI / Claude Desktop optimizations

### Native bounded reads and deferred MCP discovery

On local Claude Code, start repository localization with targeted `Glob`/`Grep` and small `Read` ranges, then return paths, line pointers, and compressed facts; do not route an entire recursive listing or build log through the parent. MCP Tool Search is enabled by default: Claude Code defers MCP tool definitions and loads them when needed. If `ANTHROPIC_BASE_URL` points to a non-first-party host, Claude Code normally disables Tool Search because most proxies do not forward `tool_reference` blocks; for a new session, launch with `ENABLE_TOOL_SEARCH=true claude` only when the model and proxy support those blocks. Microsoft Foundry deployments hosted on Azure reject Tool Search server-side, so the environment forces upfront loading and the variable cannot override it. `CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS` also keeps Tool Search disabled and cannot be overridden with `ENABLE_TOOL_SEARCH`. When Tool Search is unavailable, expect MCP tools to load upfront and do not claim deferred-loading savings. An authorized desktop extension/local MCP server may expose local resources in Desktop Chat, whereas a remote connector accesses its remote service; in both cases inspect the actual tool scope and avoid assuming local shell, unrestricted filesystem, or an independent Agent.

Official references: [MCP Tool Search in Claude Code](https://code.claude.com/docs/en/mcp), [Desktop connector boundary](https://support.claude.com/en/articles/11725091-when-to-use-desktop-and-web-connectors), [local MCP extension](https://support.claude.com/en/articles/10949351-getting-started-with-local-mcp-servers-on-claude-desktop).

A Claude Code project/user custom subagent can scope an inline `mcpServers` definition to the child, keeping unneeded tool descriptions out of the parent context; plugin-shipped agent definitions do not necessarily honor that field. Inspect the MCP tools directly exposed to a Desktop Agent Session and use only those needed and authorized for its released slice. [Anthropic: subagent MCP scope](https://code.claude.com/docs/en/sub-agents).

## Related concepts

- [Coding Session Model](session-model.md) — locate Session semantics and affinity.
- [Coding Session Role Ownership](session-role-ownership.md) — locate role responsibility ownership.
- [Coding Context Exchange](context-exchange.md) — locate file-backed context transport.
- [Coding Delegation State Record](delegation-state-record.md) — locate task-control state ownership.
- [Coding Execution Control](execution-control.md) — locate bounded stage and slice ownership.

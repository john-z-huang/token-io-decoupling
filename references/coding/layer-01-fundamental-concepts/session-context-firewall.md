# Coding Session Context Firewall

[English](session-context-firewall.md) | [简体中文](session-context-firewall_zh_cn.md)

This module owns the Context Firewall: raw-state ingress limits, bounded inspection, fact-return boundaries, and ephemeral project localization. It does not define role responsibilities, Session semantics, file-backed context transport, or workflow acceptance.

## General rules

### Raw-state ingress

In a multi-Session Coding run, the input-side Session reads only bounded, read-only environment and code evidence needed for the prerequisite confirmations owned by [session role ownership](session-role-ownership.md), not an open-ended repository scan. Primary Output consumes further source/configuration state only within released scope; Change Verification consumes final-state evidence; Documentation/Comments & Git Operations consumes Git state and approved documentation scope. Each returns only next-decision facts and exact source pointers.

Raw-state ingress is bounded by potential output volume, state sensitivity, and repository impact, not the command name. A single Session has no cross-Session firewall but still reads progressively and compresses raw state.

### Semantic ownership and ephemeral localization

The firewall limits raw-state ingress without transferring semantic authority; follow [session role ownership](session-role-ownership.md). Ephemeral UI/project localization belongs to the observing Session and is not promoted to long-lived Contract state.

## Codex CLI / ChatGPT Desktop optimizations

No provider-specific optimization instructions at present; follow the general rules above.

## Claude Code CLI / Claude Desktop optimizations

No provider-specific optimization instructions at present; follow the general rules above.

### Native bounded reads and deferred MCP discovery

On local Claude Code, start repository localization with targeted `Glob`/`Grep` and small `Read` ranges, then return paths, line pointers, and compressed facts; do not route an entire recursive listing or build log through the parent. If MCP tools are configured, use Claude Code's **MCP Tool Search** to discover the relevant tool only when needed rather than forcing every MCP schema into the session. Tool Search is runtime/provider dependent (not guaranteed through third-party proxy endpoints); verify it is active before claiming deferred-loading savings. An authorized desktop extension/local MCP server may expose local resources in Desktop Chat, whereas a remote connector accesses its remote service; in both cases inspect the actual tool scope and avoid assuming local shell, unrestricted filesystem, or an independent Agent.

Official references: [MCP Tool Search in Claude Code](https://code.claude.com/docs/en/mcp), [Desktop connector boundary](https://support.claude.com/en/articles/11725091-when-to-use-desktop-and-web-connectors), [local MCP extension](https://support.claude.com/en/articles/10949351-getting-started-with-local-mcp-servers-on-claude-desktop).

## Related concepts

- [Coding Session Model](session-model.md) — locate Session semantics and affinity.
- [Coding Session Role Ownership](session-role-ownership.md) — locate role responsibility ownership.
- [Coding Context Exchange](context-exchange.md) — locate file-backed context transport.
- [Coding Delegation State Record](delegation-state-record.md) — locate task-control state ownership.
- [Coding Execution Control](execution-control.md) — locate bounded stage and slice ownership.

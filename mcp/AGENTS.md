# MCP Server development instructions

[English](AGENTS.md) | [简体中文](AGENTS_zh_cn.md)

This file owns the client-support boundary for the MCP Server, packages, tests, metadata, and documentation under `mcp/`. Read the repository's [multilingual rules](../MULTI_LINGUAL.md) before documentation changes.

## Supported clients

- The MCP Server supports only Codex and ChatGPT Desktop. Claude Code, Claude Desktop, and other Code Agents are unsupported.
- When changing code under `mcp/`, consider only Codex-based Agent behavior and the supported desktop client. Do not add compatibility branches, adapters, configuration, examples, tests, or tool instructions for other Code Agents. Repository-wide cross-provider parity checks do not apply to this directory.
- Remove obsolete unsupported-client paths and claims instead of maintaining fallback routes. Shared protocol or operating-system abstractions do not establish support for additional clients.
- Supported scope does not prove an available or verified host integration. Continue to verify exposed capabilities, trusted identity, guards, and permissions; preserve unavailable results and fail-closed behavior.

## Scope and authority

This restriction applies to the MCP Server and does not remove native runtime instructions outside `mcp/`. It grants no additional filesystem, network, credential, Agent-creation, or Git authorization.

## Related documents

- [MCP development guide](DEVELOPMENT.md)
- [Codex caller matching](CODEX_CALLER_CONTEXT.md)

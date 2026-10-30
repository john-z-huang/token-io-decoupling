# MCP Server development instructions

[English](AGENTS.md) | [简体中文](AGENTS_zh_cn.md)

This file owns the client-support boundary for the MCP Server, packages, tests, metadata, and documentation under `mcp/`. Read the repository's [multilingual rules](../MULTI_LINGUAL.md) before documentation changes.

## Supported clients

- The MCP Server targets a locally available Codex CLI, including the local Codex CLI/app-server path used by local Work. Cloud ChatGPT conversations and remote Work are not direct clients, and other Code Agents are not supported as direct clients.
- When another Agent runs in its own environment with Codex CLI installed and configures this MCP Server there by following this repository's instructions, the supported route is that environment's local Codex CLI only; this does not add an adapter or direct support for the other Agent or a cloud surface. The server does not ask callers to select or classify an environment.
- When changing code under `mcp/`, consider Codex CLI behavior across those contexts. Do not add compatibility branches, adapters, configuration, examples, tests, or tool instructions for other Code Agents. Repository-wide cross-provider parity checks do not apply to this directory.
- Remove obsolete unsupported-client paths and claims instead of maintaining fallback routes. Shared protocol or operating-system abstractions do not establish support for additional clients.
- The fixed client scope does not prove an available or verified host integration. Continue to verify exposed capabilities, trusted identity, guards, and permissions; preserve unavailable results and fail-closed behavior.

## Scope and authority

This restriction applies to the MCP Server and does not remove native runtime instructions outside `mcp/`. It grants no additional filesystem, network, credential, Agent-creation, or Git authorization.

## Related documents

- [MCP development guide](DEVELOPMENT.md)
- [Codex caller matching](CODEX_CALLER_CONTEXT.md)

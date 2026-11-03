# Project development MCP

[English](README.md) | [简体中文](README_zh_cn.md)

This independent project hosts development tools for the Token I/O Decoupling repository. It supports local Codex CLI MCP clients under the repository's [client boundary](../mcp/AGENTS.md).

## Current capability

The first stage of [#190](https://github.com/john-z-huang/token-io-decoupling/issues/190), tracked in [#192](https://github.com/john-z-huang/token-io-decoupling/issues/192), provides a standalone stdio server and one deterministic, read-only `dev_capabilities` tool. Its initialization instructions and discovered tool metadata identify implemented and unavailable capabilities. The tool does not read repository contents, write files, call OpenAI, access Git/GitHub, read chats or write Memory.

Rule mapping and compilation, project-specific compliance checks, and Skill-instruction maintenance remain unavailable at this stage. Existing product tools and maintenance scripts retain their current behavior until their designated migration stages. This service does not grant authority for later writes or external operations.

## Run and inspect

From the repository root, create or reuse this independent project's environment and install its locked dependencies:

```bash
uv sync --project mcp-project-dev --locked --group dev
uv run --project mcp-project-dev --locked token-io-decoupling-dev --help
uv run --project mcp-project-dev --locked token-io-decoupling-dev --version
uv run --project mcp-project-dev --locked token-io-decoupling-dev --stdio
```

The last command starts MCP stdio transport; connect a negotiated MCP client to inspect initialization and `tools/list`. Server output on stdout is reserved for the protocol. This does not register a server in user configuration or install/update a user Skill.

## Responsibilities and migration

Use the repository's [development Skill](../.agents/skills/token-io-decoupling-dev/SKILL.md) for project maintenance and its [responsibility and migration inventory](../.agents/skills/token-io-decoupling-dev/references/responsibility-migration.md) for component ownership and staged moves. Product packages remain under `mcp/`; the development project has its own package and environment. Development components may reuse necessary product libraries; product packages must not depend on this project or the development Skill.

## Offline checks

```bash
uv run --project mcp-project-dev --locked pytest -q mcp-project-dev/tests
uv run --project mcp-project-dev --locked ruff check mcp-project-dev
uv run --project mcp-project-dev --locked ruff format --check mcp-project-dev
uv run --project mcp-project-dev --locked ty check --project mcp-project-dev
```

These checks do not run the final Codex SDK inspection. Follow the [repository testing boundary](../AGENTS.md#codex-sdk-final-test-boundary) and the stage-6 acceptance order before that inspection.

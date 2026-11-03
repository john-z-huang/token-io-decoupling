# Project development MCP

[English](README.md) | [简体中文](README_zh_cn.md)

This independent project hosts development tools for the Token I/O Decoupling repository. It supports local Codex CLI MCP clients under the repository's [client boundary](../mcp/AGENTS.md).

## Current capability

The independent stdio server introduced in [#192](https://github.com/john-z-huang/token-io-decoupling/issues/192) exposes deterministic, read-only `dev_capabilities`. With a trusted project root configured at startup, [#193](https://github.com/john-z-huang/token-io-decoupling/issues/193) adds `compile_runtime_instructions` and the read-only `check_runtime_instructions_freshness`. Initialization instructions and discovered tool metadata describe their inputs, results, limits, and side effects.

Compilation reads reviewed local mappings and policy Markdown and writes one fixed generated resource. Freshness checking validates those inputs and compares the generated resource without writing. These tools do not call OpenAI, access the network or Git/GitHub, read chats, or write Memory. Project-specific compliance checks and Skill-instruction maintenance remain unavailable until their designated stages of [#190](https://github.com/john-z-huang/token-io-decoupling/issues/190). Product runtime loading and existing maintenance scripts retain their current behavior.

## Run and inspect

From the repository root, create or reuse this independent project's environment and install its locked dependencies:

```bash
uv sync --project mcp-project-dev --locked --group dev
uv run --project mcp-project-dev --locked token-io-decoupling-dev --help
uv run --project mcp-project-dev --locked token-io-decoupling-dev --version
uv run --project mcp-project-dev --locked token-io-decoupling-dev --stdio
```

The last command starts MCP stdio transport with capability discovery only. To enable the compiler tools, run from the repository root and pass its absolute path at startup:

```bash
uv run --project mcp-project-dev --locked token-io-decoupling-dev --project-root "$PWD" --stdio
```

Connect a negotiated MCP client to inspect initialization and `tools/list`; each tool accepts an empty argument object. Tool calls cannot change the project root, manifest, output path, model, or permissions. Server stdout is reserved for the protocol. Starting the server does not register it in user configuration or install/update a user Skill.

## Responsibilities and migration

Use the repository's [development Skill](../.agents/skills/token-io-decoupling-dev/SKILL.md) for project maintenance and its [responsibility and migration inventory](../.agents/skills/token-io-decoupling-dev/references/responsibility-migration.md) for component ownership and staged moves. Product packages remain under `mcp/`; the development project has its own package and environment. Development components may reuse necessary product libraries; product packages must not depend on this project or the development Skill.

## Compile and check

Maintain the reviewed mapping in `mcp-project-dev/compiler-manifest.v1.json` under the configured root. `compile_runtime_instructions` validates its sources, reference classifications, complete dependencies, bilingual structure, versions, hashes, and budgets before publishing `mcp-project-dev/generated/runtime-instructions.v1.json`. Validation failure leaves the existing output intact. Review drafts are separate from the publishing manifest.

For a changed existing output, the manifest's `output_baseline_sha256` must match the current artifact's verified `canonical_sha256`; it is not the raw file hash. A supplied baseline is checked even for an identical output. Without a baseline, only creation or a byte-identical no-op is allowed. Inspect the result and use `check_runtime_instructions_freshness`; only `fresh` confirms a match with the current validated inputs. Missing, stale, or failed results require resolution before consuming the artifact.

The [compiler contract](../.agents/skills/token-io-decoupling-dev/references/compiler-contract.md) owns the schema, provenance, compatibility, and limit details. This stage does not switch the product loader to compiled resources or grant other file writes.

## Offline checks

```bash
uv run --project mcp-project-dev --locked pytest -q mcp-project-dev/tests
uv run --project mcp-project-dev --locked ruff check mcp-project-dev
uv run --project mcp-project-dev --locked ruff format --check mcp-project-dev
uv run --project mcp-project-dev --locked ty check --project mcp-project-dev
```

These checks do not run the final Codex SDK inspection. Follow the [repository testing boundary](../AGENTS.md#codex-sdk-final-test-boundary) and the stage-6 acceptance order before that inspection.

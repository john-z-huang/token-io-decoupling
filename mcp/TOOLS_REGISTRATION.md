# Two MCP executables and Codex registration

[English](TOOLS_REGISTRATION.md) | [简体中文](TOOLS_REGISTRATION_zh_cn.md)

This document owns the two standalone MCP executable inventories and their Codex registration. The [development guide](DEVELOPMENT.md) owns building, installing, and final inspection; existing state and tool owners retain their authorization contracts.

## Two standalone executables

The MCP runtime has two separately installed executables. Each starts a stdio MCP server with no startup arguments:

| Executable and Codex registration | Inventory |
| --- | --- |
| `token-io-decoupling-workflow` | The unchanged 17 capability, rule, planning, routing, and evaluation tools. |
| `token-io-decoupling-tools` | 51 tools: 9 Root, 6 Worker, 3 shared, and 33 development workflow tools. |

The administrative `token-io-decoupling` command is not an MCP runtime. It provides setup, Skill installation, and environment-forwarding repair. Its `setup codex` command resolves, verifies, and registers the two current MCP executables. It operates only on those two registration tables; it does not recognize or migrate other registrations. Users may also register them separately with their absolute executable paths:

```sh
codex mcp add token-io-decoupling-workflow -- /absolute/path/to/token-io-decoupling-workflow
codex mcp add token-io-decoupling-tools -- /absolute/path/to/token-io-decoupling-tools
```

## Inventory and operation boundaries

The inventories are fixed in [the tool manifest](packages/token_io_decoupling_core/src/token_io_decoupling_core/server_tools.py). The tools executable depends on `dev-workflow-standards-tools` from the fixed commit `ba5ecc95d9f9da77aca22c17e712d6c8d2a05987`, subdirectory `mcp-server`, of [its source repository](https://github.com/john-z-huang/dev-workflow-standards/tree/ba5ecc95d9f9da77aca22c17e712d6c8d2a05987/mcp-server). Building and installing must resolve this pinned dependency and its packaged resources; no adjacent developer checkout or absolute local dependency path is required. Updating it requires reviewing tool signatures, annotations, descriptions, and validation-error redaction against the fixed manifest.

Discovery does not grant authority. Root and Worker tools remain checked against the actual current role on every call. Shared reads and evidence writes remain role scoped, and a Worker cannot paginate Root state. Request metadata, recorded allocations, project paths, revisions, and idempotency checks still apply. `materialize_decoupled_output` still requires a registered Worker, confirmed assignment, separately configured materializer, operator grant, and current preflight. See [Worker output materialization](OUTPUT_MATERIALIZATION.md).

Development tools retain their repository-root validation, side-effect annotations, API input review, and write-authorization requirements. The tools executable reuses their published schemas, annotations, descriptions, and validation-error redaction. A development tool's availability does not establish an Enhanced Worker binding or authorize Git/GitHub effects. API-backed operations require both nonblank process `OPENAI_API_KEY` and `OPENAI_BASE_URL`, explicitly use fixed `gpt-6-luna`, and have no default credential, endpoint, or model fallback.

The tools executable forwards the API and proxy variable names plus `OPENAI_TIMEOUT_MAX_RETRIES`; it never writes their values. Setup uses empty argument lists for both executables, preserves other settings in either target registration, and leaves unrelated configuration entries untouched. The two MCP processes retain their separate configuration and capability requirements.

## Setup safety and idempotency

`token-io-decoupling setup codex --dry-run` reads the configuration and preflights only the two current target sections, but starts no MCP subprocess and writes nothing. A real setup resolves the installed workflow and tools executables, verifies their current inventories, and updates only their two target tables with empty argument lists. It preserves other settings in those target tables and all unrelated configuration entries. It does not inspect, classify, remove, or migrate other registrations; any one-time cleanup of older installations is an administrative delivery action outside this maintained command. Malformed current target sections, unsupported transport fields, invalid supported setting types, or conflicting environment-variable sources fail closed; there is no override flag. These checks validate the settings setup uses and do not claim broader policy-conflict detection.

Setup writes a regular configuration file atomically, preserves its mode, checks that the file has not changed before replacement, and rejects unsupported TOML layouts instead of silently moving unrelated content. Avoid concurrent configuration writers: the input check is not a global lock. Repeating a successful setup when both target registrations are already correct is a no-op. On failure, report the last confirmed state.

## Verification

Tests compare both inventories with the expected manifests and cover role rejection, external schemas and annotations, redaction, preservation of target and unrelated configuration, setup preview, and safe conflict handling with temporary configuration. Installed stdio checks cover both executables and their exact inventories. The ordered [final inspection](DEVELOPMENT.md#codex-sdk-final-inspection) runs only after all ordinary checks pass, builds and installs the current artifacts, then uses a fresh Codex CLI instance for bounded, read-only inspection of the two executables. It performs no model turn and does not mutate real user configuration.

Registering two executables does not by itself establish measured Token savings; both tool inventories remain available.

## Related concepts

- [MCP development guide](DEVELOPMENT.md)
- [Codex caller matching](CODEX_CALLER_CONTEXT.md)
- [Worker output materialization](OUTPUT_MATERIALIZATION.md)

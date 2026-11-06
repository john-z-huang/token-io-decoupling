# Independent MCP services and Codex registration

[English](TOOLS_REGISTRATION.md) | [简体中文](TOOLS_REGISTRATION_zh_cn.md)

Tools and workflow can be installed, registered and run separately. The [development guide](DEVELOPMENT.md) owns checks and final inspection. Each operation consumes current inputs and resource state; no workflow node, prior tool call or follow-up call is required.

## Distribution and inventory

| Distribution / executable | Fixed inventory |
| --- | --- |
| `token-io-decoupling-tools` | 41 operations: 33 upstream helpers, three task-plan operations, two Memory queries, candidate preflight, protected output materialization and optional `tools_capabilities`. |
| `token-io-decoupling-workflow` | 11 compiled rule, navigation, advisory and structural-evaluation tools. |
| `token-io-decoupling` | Optional full-installation admin command; no MCP runtime of its own. |

Runtime packages depend on shared core/transport, never on each other. Compiled resources and the rule loader belong to workflow; core and transport contain no rules. Tools runtime, CLI, schemas and metadata do not load workflow or the Coding Skill. Workflow does not initialize or probe tools backends.

## Selected-service setup

Each runtime distribution owns its console script and can register itself without the admin package:

```sh
/absolute/path/to/token-io-decoupling-tools setup codex
/absolute/path/to/token-io-decoupling-workflow setup codex
```

The optional admin command accepts `setup codex --server tools|workflow|both`; the default is `both`. Append `--dry-run` for a configuration read and selected-table preflight without discovery or writes. Real setup resolves only the selected distributions' entry-point metadata and executable paths, checks their exact inventories and atomically upserts only their target tables. Unselected and unrelated tables, existing enabled/disabled state, approvals, timeouts, cwd and extra environment names are preserved. Malformed selected configuration and concurrent changes fail rather than being overwritten.

A full `uv tool install` must expose dependency-owned scripts using `--with-executables-from token-io-decoupling-workflow --with-executables-from token-io-decoupling-tools`. Independent runtime installs expose their own script directly. See the [installation guide](../../../../../INSTALL.md).

## Operation and configuration boundaries

Tools reuse upstream schemas, annotations, callbacks, input review and validation-error redaction from the pinned `dev-workflow-standards-tools` revision. The exposed tool descriptions are local operation contracts; the upstream server's workflow instructions and calling order are not appended. There is no prerequisite diagnostic, route or content-generation call.

Task plans and Memory are served only by tools. `--task-plan-factory`, `--compliance-factory` and `--output-materializer-factory` are tools startup options; operator code imports their types from `token_io_decoupling_tools`. Workflow rejects the migrated options. Wire payloads and existing plan/Memory data are preserved. Update operator imports and enabled_tools/disabled_tools filters when reloading an older installation.

Current resource checks remain local: revisions protect plan updates; completion/archive validate existing plan state; materialization validates an existing prepared artifact, trusted per-call identity and assignment, an independent operator grant, pinned paths, baselines, fresh preflight and write-time authority. An existing resource does not establish a prior tool invocation or workflow release. Missing materializer configuration remains unavailable.

Local tools need no API configuration. API operations use their required nonblank process `OPENAI_API_KEY` and `OPENAI_BASE_URL`, fixed model and outbound-input review; missing configuration affects only dependent operations. Setup forwards names, not values, and tools also forwards `OPENAI_TIMEOUT_MAX_RETRIES`. Discovery and hashes grant no authority.

## Verification

Tests verify disjoint inventories, sibling/admin import rejection, real independent wheel installation, direct stdio calls, selected-service registration, configuration preservation, redaction and protected-write rejection. Archive tests cover five distributions, no rule resources in core, approved workflow/Skill batches and detached rebuilding. The ordered [final inspection](DEVELOPMENT.md#codex-sdk-final-inspection) runs all applicable checks, builds and installs the current full wheel set in temporary uv directories, then uses a fresh read-only Codex CLI with zero model turns. It does not change real user configuration.

# Token I/O Decoupling

[English](README.md) | [简体中文](README_zh_cn.md)

Use independent MCP tools for development, task plans and Memory, with an optional compiled Coding workflow. Each tool accepts its own operation inputs; it requires no workflow node, mode, checkpoint, earlier tool call or follow-up call. Resource validation and host authorization remain local to the operation.

## Install tools only

From a source checkout, install the tools distribution and its two shared dependencies:

```sh
uv tool install --force --reinstall --managed-python --python 3.14 \
  --with ./mcp/packages/token_io_decoupling_core \
  --with ./mcp/packages/token_io_decoupling_transport \
  ./mcp/packages/token_io_decoupling_tools
"$(uv tool dir --bin)/token-io-decoupling-tools" setup codex
```

This installs and registers only tools: no workflow package, compiled rules or Coding Skill. Reload that MCP service. Choose any tool from its published schema; `tools_capabilities` is an optional dependency diagnostic. Local tools work without API configuration. API operations and configured plan/materialization backends report their own missing dependencies.

The tools service exposes 41 operations: 33 upstream development helpers, task-plan update/complete/archive, two Memory queries, candidate preflight, protected output materialization and diagnostics. The Memory queries use the server startup project's `.serena/memories`; plan storage is configured separately. Protected writes retain identity, independent grant, path, baseline and preflight checks. Existing resource state can come from any compatible writer.

## Optional workflow and full installation

The separate workflow package exposes 11 rule, navigation, advice and evaluation tools. Install it independently using the same two `--with` dependencies and `./mcp/packages/token_io_decoupling_workflow`, then run `token-io-decoupling-workflow setup codex` from the uv tool bin directory. It neither imports nor installs tools.

For the full distribution and optional Coding Skill:

```sh
bash scripts/install-codex-mcp.sh
"$(uv tool dir --bin)/token-io-decoupling" skills install
```

Use `skills update` for an existing managed Skill. The full installer registers both services; `token-io-decoupling setup codex --server tools` or `--server workflow` selects one. Loading the Coding Skill explicitly adopts its workflow. Tools-only tasks do not load it or enter its route.

MCP support remains local Codex CLI, including its local app-server path. Other Agents may consume the generated workflow documents; this does not add direct MCP client support. Instructions, hashes and diagnostics do not authorize effects or prove completion.

## Repository boundaries

| Part | Responsibility |
| --- | --- |
| `mcp/packages/token_io_decoupling_tools` | Independent tools, plans, Memory, preflight and protected materialization. |
| `mcp/packages/token_io_decoupling_workflow` | Independent workflow runtime and approved compiled rule resources. |
| `mcp/packages/token_io_decoupling_core` and `token_io_decoupling_transport` | Shared contracts, guards, transport and selected-service setup; no workflow resources or service imports. |
| `mcp/` root distribution | Compatible full installation, administration and optional Skill ZIP. |
| [Private development Skill](.agents/skills/token-io-decoupling-dev/SKILL.md) | Repository guidance, tests and release checks. |
| `instruction-compiler/` | Private author policies and deterministic compilation. |

Private development files and compiler sources are excluded from product archives. Generated resources must not be edited by hand. See [installation and migration](INSTALL.md).

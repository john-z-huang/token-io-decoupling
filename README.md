# Token I/O Decoupling

[English](README.md) | [简体中文](README_zh_cn.md)

Token I/O Decoupling delivers a Coding workflow through two local MCP servers and a generated Skill. Instructions provide current actions, guards, evidence and exact continuations. Shared or conditional instructions have explicit loading requirements; Agents do not search the author documents to reconstruct a workflow.

## First installation

From the source checkout, with the [prerequisites](INSTALL.md#prerequisites) available:

```sh
bash scripts/install-codex-mcp.sh
"$(uv tool dir --bin)/token-io-decoupling" skills install
```

The first command checks compiled-resource freshness, builds and installs all four runtime packages, and registers both MCP executables with Codex. The second installs the same-batch Skill to `~/.agents/skills/token-io-decoupling-skill`. Reload the two MCP servers and start a new Agent session.

## Update

After obtaining the desired checkout revision, run from its root:

```sh
bash scripts/install-codex-mcp.sh
"$(uv tool dir --bin)/token-io-decoupling" skills update
```

Updating the tool does not update the installed Skill automatically. Use `install` for a first Skill installation and `update` for an existing managed snapshot. The [installation guide](INSTALL.md) owns prerequisites, building distributable files, wheel-only installation, verification and recovery.

## Start a Coding task

Load the installed `token-io-decoupling-skill` after following the [installation guide](INSTALL.md). With MCP, begin with `workflow_capabilities`, then `rules_get_context` using `node_id=contract` and `context_version=2`. Follow the returned exact instructions and obtain triggered shared units before dependent actions. Explicit nonempty `fragment_ids` return only those units; omit them for a complete default checkpoint. Version 1 is rejected.

The MCP servers support local Codex CLI, including local Work through that CLI. Other Code Agents may use the generated documents without these MCP servers. Static rule queries need no API credentials or network. Optional API-backed tools require the configured environment and per-call authorization described in the installation guide.

Instructions, hashes, capability reports and structural review statuses do not establish identity, authorize effects or prove completion. Protected operations retain their own guards. Runtime use needs neither author sources nor the private compiler and development Skill.

## Repository components

| Part | Location and responsibility |
|---|---|
| Product | `mcp/` runtime packages; executable tools, guards, compiled core resources and the packaged Skill ZIP. |
| Private development Skill | [Development entry](.agents/skills/token-io-decoupling-dev/SKILL.md); project guidance, checks, product tests and release coordination. |
| Private compiler | `instruction-compiler/`; author policy, execution dependencies, deterministic generation and compiler tests. |

Private development and compiler inputs are excluded from wheels, Skill ZIPs and sdists. Do not hand-edit generated resources. Root `scripts/` contains only the installation entry; development scripts and documentation tests live in the private development Skill.

## Related documents

- [Installation and updates](INSTALL.md).
- [Project development](.agents/skills/token-io-decoupling-dev/SKILL.md).

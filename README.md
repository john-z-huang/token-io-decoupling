# Token I/O Decoupling

[English](README.md) | [简体中文](README_zh_cn.md)

`token-io-decoupling` is an Agent orchestration Skill that separates high-value semantic decisions from high-volume state consumption and output materialization.

It maintains the **Coding** workflow for repository and development work. Multimodal material is retained only as standalone reference content, not as an executable workflow. Start with [Skill entry](docs/skill/SKILL.md); it routes each task to the references required for its current stage.

## Install the Skill separately

Keep this development checkout outside user Skill directories. After installing the built CLI (see the MCP setup guide), run:

```bash
token-io-decoupling skills install
token-io-decoupling skills update
```

The default destination is `~/.agents/skills/token-io-decoupling-skill`; `--name NEW-NAME` selects another lower-case hyphenated name. The old name `token-io-decoupling` is always refused. The installer never modifies or deletes the old checkout, refuses symlink paths and existing unknown directories, and updates only an unchanged installation it owns. Preserve local edits elsewhere before updating. A failed update restores the previous installation when publication fails; an interrupted process may leave a lock or staging directory, which should be inspected before manual recovery.

Skill sources live in [docs/skill](docs/skill/SKILL.md). Wheels and source distributions carry an independent snapshot including bilingual workflows, references and supporting docs/scripts. Installation uses that snapshot without reading or cloning a checkout; source edits take effect only after rebuilding/reinstalling the CLI and explicitly updating the Skill. Installed `_project/` resources are generated supporting snapshots, not additional source owners. MCP registration remains a separate `setup codex` action.

For legacy coexistence, use the new Skill name in requests. Existing sessions may retain old instructions: after preserving and relocating your old development checkout, manually disable its old Skill discovery entry through your existing configuration, then start a fresh session using the new name. The installer does not remove the old project or automatically resolve duplicate discovery. Do not install a checkout itself into a Skill directory again.

## MCP support and document-only use

This project's MCP Server is developed only for local Codex CLI. Local ChatGPT Work uses it through local Codex CLI. Other Code Agents, cloud ChatGPT chats, and remote ChatGPT Work do not directly support this server. They can use it only by installing Codex CLI in their own environment and following this project's instructions to install the server for that CLI; this does not add support for those hosts or Agents. Codex CLI calls these tools without a runtime-environment judgment step; actual capability, identity, permission, and guard checks still apply. See the [MCP client boundary](mcp/AGENTS.md).

Other Code Agents may use the Skill through its documents without this MCP Server. The project will continue maintaining instructions compatible with other Code Agents alongside Codex CLI support; MCP Server development remains focused on Codex CLI.

## Install the MCP servers in Codex

With `uv`, Bash 3.2 or later, and the Codex CLI available, run one command from any working directory:

```sh
bash /absolute/path/to/skill/scripts/install-codex-mcp.sh
```

The [installer](scripts/install-codex-mcp.sh) installs or updates this checkout's MCP package, resolves its installed executable automatically, registers all four profiles, and merges the required environment-variable forwarding names. The installed tool's bin directory need not be on `PATH`. Use the same command again after source updates. Add `--dry-run` to preview without installing or changing configuration, `--profile root` to register only one profile, or `--replace` to explicitly replace conflicting registrations. Reload the affected MCP servers afterward. See the [setup guide](mcp/DEVELOPMENT.md#uv-tool-installation-and-codex-setup) for prerequisites, options, and failure handling.

## Documentation

- [Skill entry](docs/skill/SKILL.md): primary routing entry point.
- [Coding references](docs/skill/references): independent Coding and shared protocol modules used by the workflows.
- [Multilingual rules](MULTI_LINGUAL.md): bilingual documentation rules.
- [Enhanced architecture](docs/skill/ENHANCED_ARCHITECTURE.md): optional MCP state, rule context, semantic advice, and verified host boundaries; Native remains the default.
- [MCP development guide](mcp/DEVELOPMENT.md): local Python checks and package builds.

The optional Decisions integration is disabled by default. Every real request, including test requests, must read both local `OPENAI_API_KEY` and `OPENAI_BASE_URL`; missing either prevents a request. Follow the development guide for explicit enablement and testing. The current production entry has no verified Codex CLI host binding and therefore exposes only public diagnostics and rule context.

`token-io-decoupling setup codex` registers the selected profiles and automatically merges `OPENAI_API_KEY` and `OPENAI_BASE_URL` into each server's `env_vars`, including existing matching registrations. Reload the servers afterward. For a registered server with any name, use `setup codex-env --server NAME` or the [standalone repair script](scripts/configure-codex-mcp-env.py); both support `--dry-run`. See the [environment forwarding instructions](mcp/DEVELOPMENT.md#codex-stdio-environment-forwarding). Forwarding makes configuration available to the process; it does not enable Decisions or establish a host binding.

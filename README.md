# Token I/O Decoupling

[English](README.md) | [简体中文](README_zh_cn.md)

`token-io-decoupling` is an Agent orchestration Skill that separates high-value semantic decisions from high-volume state consumption and output materialization.

It maintains the **Coding** workflow for repository and development work. Multimodal material is retained only as standalone reference content, not as an executable workflow. Start with [Skill entry](SKILL.md); it routes each task to the references required for its current stage.

## Install the MCP servers in Codex

With `uv`, Bash 3.2 or later, and the Codex CLI available, run one command from any working directory:

```sh
bash /absolute/path/to/skill/scripts/install-codex-mcp.sh
```

The [installer](scripts/install-codex-mcp.sh) installs or updates this checkout's MCP package, resolves its installed executable automatically, registers all four profiles, and merges the required environment-variable forwarding names. The installed tool's bin directory need not be on `PATH`. Use the same command again after source updates. Add `--dry-run` to preview without installing or changing configuration, `--profile root` to register only one profile, or `--replace` to explicitly replace conflicting registrations. Reload the affected MCP servers afterward. See the [setup guide](mcp/DEVELOPMENT.md#uv-tool-installation-and-codex-setup) for prerequisites, options, and failure handling.

## Documentation

- [Skill entry](SKILL.md): primary routing entry point.
- [Coding references](references/): independent Coding and shared protocol modules used by the workflows.
- [Multilingual rules](MULTI_LINGUAL.md): bilingual documentation rules.
- [Enhanced architecture](ENHANCED_ARCHITECTURE.md): optional MCP state, rule context, semantic advice, and verified host boundaries; Native remains the default.
- [MCP development guide](mcp/DEVELOPMENT.md): local Python checks and package builds.

The optional Decisions integration is disabled by default. Every real request, including test requests, must read both local `OPENAI_API_KEY` and `OPENAI_BASE_URL`; missing either prevents a request. Follow the development guide for explicit enablement and testing. The current production entry has no verified Codex or ChatGPT Desktop host binding and therefore exposes only public diagnostics and rule context.

`token-io-decoupling setup codex` registers the selected profiles and automatically merges `OPENAI_API_KEY` and `OPENAI_BASE_URL` into each server's `env_vars`, including existing matching registrations. Reload the servers afterward. For a registered server with any name, use `setup codex-env --server NAME` or the [standalone repair script](scripts/configure-codex-mcp-env.py); both support `--dry-run`. See the [environment forwarding instructions](mcp/DEVELOPMENT.md#codex-stdio-environment-forwarding). Forwarding makes configuration available to the process; it does not enable Decisions or establish a host binding.

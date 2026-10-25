# Token I/O Decoupling

[English](README.md) | [简体中文](README_zh_cn.md)

`token-io-decoupling` is an Agent orchestration Skill that separates high-value semantic decisions from high-volume state consumption and output materialization.

It maintains the **Coding** workflow for repository and development work. Multimodal material is retained only as standalone reference content, not as an executable workflow. Start with [Skill entry](SKILL.md); it routes each task to the references required for its current stage.

## Documentation

- [Skill entry](SKILL.md): primary routing entry point.
- [Coding references](references/): independent Coding and shared protocol modules used by the workflows.
- [Multilingual rules](MULTI_LINGUAL.md): bilingual documentation rules.
- [Enhanced architecture](ENHANCED_ARCHITECTURE.md): optional MCP state, rule context, semantic advice, and verified host boundaries; Native remains the default.
- [MCP development guide](mcp/DEVELOPMENT.md): local Python checks and package builds.

The optional Decisions integration is disabled by default. Every real request, including test requests, must read both local `OPENAI_API_KEY` and `OPENAI_BASE_URL`; missing either prevents a request. Follow the development guide for explicit enablement and testing. The current production entry has no verified Codex or ChatGPT Desktop host binding and therefore exposes only public diagnostics and rule context.

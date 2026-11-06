---
name: token-io-decoupling-dev
description: Maintain this repository's MCP runtime, instruction compiler, generated Skill, checks and release tooling. Use for development of token-io-decoupling itself.
---

# Token I/O Decoupling development

[English](SKILL.md) | [简体中文](SKILL_zh_cn.md)

This project-private Skill owns maintenance procedures and verification for this repository. It is excluded from product archives and installation.

1. Consult the [project development guidance](AGENTS.md), then select this Skill's applicable procedures using the current task and user directions.
2. Runtime implementation belongs to mcp; instruction author sources and executable dependency contracts belong to instruction-compiler. Generated product resources and the delivered Skill must not be hand-edited.
3. Use scoped Serena code queries and the available workflow/development MCP tools when they cover the task. Use authorized CLI for uncovered operations; the current user directive determines the released scope.
4. For instruction changes, update both source languages and relevant dependency/branch scenarios, compile, review generated behavior, then verify source freshness. Missing or ambiguous required execution dependencies block release.
5. This Skill's scripts own repository checks. Invoke development checks and documentation regressions directly from this private Skill. Root scripts retains only the installation entrypoint; development/test forwarding aliases are removed. Product tests belong to tests/mcp; compiler tests belong to the compiler.
6. Follow the [MCP development guide](references/mcp/DEVELOPMENT.md) for package checks and the ordered final coordinator. All other applicable checks precede build, isolated uv tool installation and fresh CLI inspection. SDK use is test-only, bounded read-only and zero model turns.
7. Preserve generic runtime identity, independent grants, path/baseline/preflight and write-time guards. Project-specific author-document checking stays private. Hashes establish neither semantic correctness nor authority.
8. Before acceptance, inspect archive contents, same-batch manifests and detached-sdist rebuilding. Existing task authorization determines permitted Git and remote effects.

## Related concepts

- [MCP development boundary](references/mcp/AGENTS.md).
- [External reference registry](references/EXTERNAL_REFERENCES.md), only for instruction development.
- [Author workflow architecture](../../../instruction-compiler/sources/skill/WORKFLOW_ARCHITECTURE.md).

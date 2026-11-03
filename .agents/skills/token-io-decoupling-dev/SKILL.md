---
name: token-io-decoupling-dev
description: Maintain the Token I/O Decoupling development tools, rule compiler, and project compliance checks; use for repository-development automation, not runtime task orchestration.
---

# Token I/O Decoupling Development

[English](SKILL.md) | [简体中文](SKILL_zh_cn.md)

This Skill owns development-time project maintenance: mapping product rules into compiler inputs, building and validating development checks, and maintaining this Skill. The product Skill and product MCP server continue to own runtime task orchestration, stable workflow state, permissions, and user-side installation.

Use only capabilities the independent development MCP project reports as available. Start its local Codex CLI server with an absolute `--project-root` to enable fixed-path compiler tools; without it, only capability discovery is available. The reviewed fixed manifest and versioned runtime resource are available; review JSON remains non-publishing evidence. Root must approve future mapping changes before publication. Compliance checks and output materialization remain unavailable. Follow the [compiler contract](references/compiler-contract.md) and the [node and branch mapping](references/node-mapping.md), and consult the [responsibility and migration map](references/responsibility-migration.md) before changing boundaries or planning a later migration.

Development code may reuse product core components when a real need exists. Product runtime code must never depend on this development project.

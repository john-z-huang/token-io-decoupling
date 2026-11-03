---
name: token-io-decoupling-dev
description: Maintain the Token I/O Decoupling development tools, rule compiler, and project compliance checks; use for repository-development automation, not runtime task orchestration.
---

# Token I/O Decoupling Development

[English](SKILL.md) | [简体中文](SKILL_zh_cn.md)

This Skill owns development-time project maintenance: mapping product rules into compiler inputs, building and validating development checks, and maintaining this Skill. The product Skill and product MCP server continue to own runtime task orchestration, stable workflow state, permissions, and user-side installation.

Use the independent development MCP project only for capabilities it actually reports as available. It currently exposes read-only capability discovery; compilation, compliance checks, and output materialization are unavailable. Consult the [responsibility and migration map](references/responsibility-migration.md) before changing boundaries or planning a later migration.

Development code may reuse product core components when a real need exists. Product runtime code must never depend on this development project.

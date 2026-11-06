# Project development guidance

[English](AGENTS.md) | [简体中文](AGENTS_zh_cn.md)

This project-private file guides development of token-io-decoupling itself. It is excluded from product wheels, installed Skills and source distributions.

## Working approach

- Prefer the installed `token-io-decoupling-skill` (see the [installation guide](../../../INSTALL.md)), and the [dev-workflow-standards Skill](https://github.com/john-z-huang/dev-workflow-standards) as references.
- Prefer applicable MCP tools from these two projects when they are actually exposed and authorized in the current session. Use suitable authorized alternatives when a tool is unavailable or does not fit the task.
- Use judgment to select and reconcile useful instructions for the current task. These references need not be followed in full, and a task does not automatically require every workflow step.
- Authorization comes from the user and host. A Skill recommendation or an available tool does not grant additional permissions.

## Scope

This guidance applies only while maintaining this repository. Product runtime belongs to `mcp`, instruction authoring and generation to `instruction-compiler`, and repository maintenance to this private development Skill. Product use in other projects follows its own current instructions and authorization.

## Related concepts

- [Development Skill](SKILL.md)
- [MCP development guide](references/mcp/DEVELOPMENT.md)
- [Documentation language guidance](references/MULTI_LINGUAL.md)

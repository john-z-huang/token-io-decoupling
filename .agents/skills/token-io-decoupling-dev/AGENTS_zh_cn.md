# 项目开发指导

[English](AGENTS.md) | [简体中文](AGENTS_zh_cn.md)

本文仅指导 token-io-decoupling 项目自身的开发，属于项目私有内容，不进入产品 wheel、已安装 Skill 或源码分发包。

## 工作方式

- 优先参考 已安装的 `token-io-decoupling-skill`（见[安装指南](../../../INSTALL_zh_cn.md)）和 [dev-workflow-standards Skill](https://github.com/john-z-huang/dev-workflow-standards)。
- 当前会话实际暴露、已获授权且适合任务时，优先使用这两个项目的 MCP 工具；工具不可用或不适用时，采用合适的已授权替代方式。
- 根据当前任务自行判断、选择和协调有用的指令，无须完整遵循参考指令，也不因任务启动就自动执行全部工作流步骤。
- 授权仍来自用户与宿主；Skill 建议和工具可用性不产生额外权限。

## 适用范围

本指导仅用于维护本仓库。产品运行时属于 `mcp`，指令作者源与生成属于 `instruction-compiler`，仓库维护属于本私有开发 Skill。在其他项目使用产品时，遵循该任务当前的指令与授权。

## 相关概念

- [开发 Skill](SKILL_zh_cn.md)
- [MCP 开发指南](references/mcp/DEVELOPMENT_zh_cn.md)
- [文档语言指导](references/MULTI_LINGUAL_zh_cn.md)

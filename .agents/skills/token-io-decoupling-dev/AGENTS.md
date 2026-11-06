# 项目开发指导


本文仅指导 token-io-decoupling 项目自身的开发，属于项目私有内容，不进入产品 wheel、已安装 Skill 或源码分发包。

## 工作方式

- 优先参考 已安装的 `token-io-decoupling-skill`（见[安装指南](../../../INSTALL.md)）和 [dev-workflow-standards Skill](https://github.com/john-z-huang/dev-workflow-standards)。
- 当前会话实际暴露、已获授权且适合任务时，优先使用这两个项目的 MCP 工具；工具不可用或不适用时，采用合适的已授权替代方式。
- 根据当前任务自行判断、选择和协调有用的指令，无须完整遵循参考指令，也不因任务启动就自动执行全部工作流步骤。
- 授权仍来自用户与宿主；Skill 建议和工具可用性不产生额外权限。

## 适用范围

本指导仅用于维护本仓库。产品运行时属于 `mcp`，指令作者源与生成属于 `instruction-compiler`，仓库维护属于本私有开发 Skill。在其他项目使用产品时，遵循该任务当前的指令与授权。

## 相关概念

- [开发 Skill](SKILL.md)
- [MCP 开发指南](references/mcp/DEVELOPMENT.md)
- [文档语言指导](references/MULTI_LINGUAL.md)

本仓库文档与指令只维护无语言后缀的简体中文单源；代码标识符和协议字段保持英文。

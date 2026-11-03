---
name: token-io-decoupling-dev
description: 维护 Token I/O Decoupling 开发工具、规则编译器和项目合规检查；适用于仓库开发自动化，不用于运行时任务编排。
---

# Token I/O Decoupling 开发

[English](SKILL.md) | [简体中文](SKILL_zh_cn.md)

本 Skill 负责开发期项目维护：将产品规则映射为编译器输入、构建和验证开发检查，以及维护本 Skill。产品 Skill 与产品 MCP Server 继续负责运行时任务编排、稳定工作流状态、权限和用户侧安装。

仅使用独立开发 MCP 项目实际报告为可用的能力。目前它只提供只读能力发现；编译、合规检查和输出物化均不可用。变更边界或规划后续迁移前，请查阅[职责与迁移映射](references/responsibility-migration_zh_cn.md)。

确有需要时，开发代码可以复用产品核心组件。产品运行时代码不得依赖此开发项目。

---
layout: default
title: Token I/O Decoupling
lang: zh-CN
---

# Token I/O Decoupling

本项目提供可独立使用的本地 Codex CLI MCP 工具，以及可选的中文 Coding Skill。Code Agent 根据简短流程指令、当前上下文、关键事件 Hook 和实际工具结果选择执行路径；workflow 只交付无状态规则、检查和建议，不保存任务状态或推进业务 DAG。

先阅读[产品说明](https://github.com/john-z-huang/token-io-decoupling/blob/main/README.md)，再按照[安装指南](https://github.com/john-z-huang/token-io-decoupling/blob/main/INSTALL.md)配置所需服务。只有明确采用工作流时才加载 `token-io-decoupling-skill`；独立 tools 不要求工作流前置调用。其他 Code Agent 可以结合自身获准工具消费生成文档，不因此成为直接 MCP 客户端。

产品运行时与项目私有开发 Skill、指令编译器分离。开发规范、脚本、测试和作者源不进入产品归档；仅维护本仓库时读取[开发 Skill](https://github.com/john-z-huang/token-io-decoupling/blob/main/.agents/skills/token-io-decoupling-dev/SKILL.md)。

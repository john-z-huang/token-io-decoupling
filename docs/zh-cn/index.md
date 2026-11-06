---
layout: default
title: Token I/O Decoupling
lang: zh-CN
---

[English]({{ '/' | relative_url }}) | [简体中文](.)

# Token I/O Decoupling

本项目通过本地 Codex CLI MCP 工具与生成的双语 Skill 交付 Coding 工作流。当前步骤指令包含动作、条件、证据、失败边界和精确继续位置，无需查阅原始 owner。

先阅读[产品说明](https://github.com/john-z-huang/token-io-decoupling/blob/main/README_zh_cn.md)，按照[安装指南](https://github.com/john-z-huang/token-io-decoupling/blob/main/INSTALL_zh_cn.md)完成安装，再加载已安装的 `token-io-decoupling-skill`。其它 Code Agent 可在实际能力范围内使用纯文档 Skill。

产品运行时同私有开发 Skill、指令编译器分离。开发规范、脚本、测试和作者源不进入发布产品包。仅维护本项目时读取[开发 Skill](https://github.com/john-z-huang/token-io-decoupling/blob/main/.agents/skills/token-io-decoupling-dev/SKILL_zh_cn.md)。

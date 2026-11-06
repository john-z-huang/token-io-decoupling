# 工作流导航可用性

[English](navigation-availability.md) | [简体中文](navigation-availability_zh_cn.md)

本文档负责可选工作流导航或结构检查不可用时的处置；不负责策略、调用方身份、权限或检查点结果。

## 通用规范

作者 owner 继续作为开发期政策权威，执行消费其批准的编译指令。可选导航选择有界指令单元，结构检查核对所供输入；其可用性不能建立运行时身份、受保护操作能力、权限或工作流状态。

可选导航不可用时，可由实际已可用且获授权的同构建生成纯文档指令入口提供明确的当前单元。这是交付入口替代，不是作者源回退。必需指令资源缺失、不完整、损坏或不兼容时阻塞依赖工作，不查找作者文档、不推断政策或跳过要求。可选导航不需要时，记录附理由的 `Not applicable`，直接消费对应已交付指令。

无状态结构检查不能取代编译指令审阅、解释证据、授权、Slice 释放、Control、验证或验收。它们不保留规范工作流状态、不建立跨调用顺序，也不能将所供 Hash 变为证明。

## Codex CLI / ChatGPT Desktop 特别优化指令

`rules_get_context` 不可用时，只能使用实际可用且获授权的同构建生成纯文档 Skill，保留明确单元标识与继续位置。资源错误阻塞受影响路径，不允许作者源回退；结构评估除非另有独立要求，否则仍属可选。不得虚构另一持久化工作流后端，也不将不可用结果当作通过。

## Claude Code CLI / Claude Desktop 特别优化指令

本项目 MCP Server 不支持 Claude 直接客户端。使用实际可用且获授权的文档能力消费生成的纯文档 Skill，遵循同构建和失败检查；该 MCP 优化记为 `Not applicable`。

## 相关概念

- [工作流规则上下文](rule-context_zh_cn.md) — 负责有界规则导航。
- [检查点结构检查](checkpoint-structure-checks_zh_cn.md) — 负责对所供事实执行可选结构检查。
- [Coding Execution Control](../execution-control/execution-control_zh_cn.md) — 负责 Slice 与 Control 的授权边界。

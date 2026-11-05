# 工作流导航可用性

[English](navigation-availability.md) | [简体中文](navigation-availability_zh_cn.md)

本文档负责可选工作流导航或结构检查不可用时的处置；不负责策略、调用方身份、权限或检查点结果。

## 通用规范

工作流当前 owner 文档仍具权威性。导航工具及其注册表是可选辅助能力，用于定位有界的当前规则正文和检查所供输入结构。其可用性不能证明运行时身份、受保护操作能力、权限或工作流状态。

若导航不可用或不完整，且当前 Session 的授权能力可以访问相关权威 owner，则直接阅读该 owner。阅读范围限制在当前判断所需内容。若无法获取必需 owner，则仅阻塞依赖它的工作；不得推断其策略或跳过要求。可选导航不需要时，记录附有理由的 `Not applicable`。

无状态结构检查不能取代直接审阅 owner、解释证据、授权、Slice 释放、Control、验证或验收。它们不保留规范工作流状态，不建立跨调用顺序，也不能将调用方提供的 Hash 变为证明。

## Codex CLI / ChatGPT Desktop 特别优化指令

若 `rules_get_context` 或结构评估工具不可用，且当前内容可访问，则直接阅读当前 owner 并继续，同时记录限制。若权威 owner 不可访问，则阻塞依赖该判断的工作。不得选择其他持久化工作流后端，也不得将不可用结果视为通过。

## Claude Code CLI / Claude Desktop 特别优化指令

当前没有 Claude 专属的导航优化。遵循通用规范，使用当前 Session 实际暴露的能力。

## 相关概念

- [工作流规则上下文](rule-context_zh_cn.md) — 负责有界规则导航。
- [检查点结构检查](checkpoint-structure-checks_zh_cn.md) — 负责对所供事实执行可选结构检查。
- [Coding Execution Control](../execution-control/execution-control_zh_cn.md) — 负责 Slice 与 Control 的授权边界。

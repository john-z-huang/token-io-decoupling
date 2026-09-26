# Coding Execution Planning

[English](execution-planning.md) | [简体中文](execution-planning_zh_cn.md)

本文档负责两级执行规划：将已批准方向转换为有界计划和阶段提纲，并安排 reconnaissance 在实现放行之前发生。不定义决策门禁策略、Interaction Slice 字段、阶段反馈、角色/Session 语义、上下文传输或委派生命周期。

## 通用规范

### 两级规划

将已批准方向转换为有界的检查、实现和定向检查步骤。计划记录阶段提纲以及每个阶段预期产出的证据，但不把阶段写成命令列表。

### 从 reconnaissance 到实现放行

在实质性决策前需要项目事实时，规划一个有界 reconnaissance slice，返回压缩事实、有证据支持的选项和未解决问题。随后由决策门禁确认或否定方向，再放行实现。规划不批准新的语义或架构方向。

## Codex CLI / ChatGPT Desktop 特别优化指令

目前没有针对该厂商的特别优化指令；遵循上述通用规范。

## Claude Code CLI / Claude Desktop 特别优化指令

目前没有针对该厂商的特别优化指令；遵循上述通用规范。

## 相关概念

- [Coding Execution Control](execution-control_zh_cn.md) — 定位 Interaction Slice 放行和边界控制。
- [Coding Execution Decision Gate](execution-decision-gate_zh_cn.md) — 定位 Decision Brief 和实现放行决策。
- [Coding Execution Stage Feedback](execution-stage-feedback_zh_cn.md) — 定位有界阶段反馈。
- [Coding Session Model](session-model_zh_cn.md) — 定位角色和 Session 归属。
- [Coding Context Exchange](context-exchange_zh_cn.md) — 定位上下文传输归属。
- [Coding 子 Agent Dispatch 与生命周期](delegation-child-lifecycle_zh_cn.md) — 定位委派生命周期归属。

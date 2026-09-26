# Coding Execution Stage Feedback

[English](execution-stage-feedback.md) | [简体中文](execution-stage-feedback_zh_cn.md)

本文档定义有界阶段、Progress Signals 和阶段内使用 Decision Checkpoint 的方式。不定义 Decision Brief、方案选择、Contract 更新、Interaction Slice 字段、角色/Session 语义、上下文传输或委派生命周期。

## 通用规范

### 有界阶段

对于高不确定性工作，预先声明一组短小、能够产出证据的阶段。每个阶段以观察结果或决策边界结束，而不是命令列表。

### Progress Signals 与阶段反馈

在声明的阶段边界，只返回下一步决策所需的压缩进度信号：实质状态、发现、变更范围、验证、问题和所需动作。普通读取、局部编辑、formatter/lint 修复、直接测试修复和重复 compile/test 循环留在已批准阶段内。不要仅为了汇报低价值机械步骤增加 checkpoint 或执行 slice。

如果阶段证据显示下一阶段依赖高价值判断，应将信号交给 Decision Gate。Decision Gate 负责方案选择和 Contract 更新；本文档不重复这些策略。

## Codex CLI / ChatGPT Desktop 特别优化指令

目前没有针对该厂商的特别优化指令；遵循上述通用规范。

## Claude Code CLI / Claude Desktop 特别优化指令

目前没有针对该厂商的特别优化指令；遵循上述通用规范。

## 相关概念

- [Coding Execution Control](execution-control_zh_cn.md) — 定位 Interaction Slice 边界。
- [Coding Execution Planning](execution-planning_zh_cn.md) — 定位有界计划和阶段提纲归属。
- [Coding Execution Decision Gate](execution-decision-gate_zh_cn.md) — 定位高价值决策条件。

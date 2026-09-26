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

Codex 已配置的 `PostToolUse` 或 `SubagentStop` Hook 可以提供工具或子代理的观察结果，供父级压缩 Progress Signal；`PreCompact` 可以标记上下文将被压缩的边界。这些可选事件不证明语义验收，也不应导致完整工具日志或 transcript 倾倒。[OpenAI：工具与生命周期 Hooks](https://learn.chatgpt.com/docs/hooks)。

## Claude Code CLI / Claude Desktop 特别优化指令

### Hook 辅助的精简阶段证据

持久 Claude Code 子代理的 `SubagentStop` 提供 `last_assistant_message`，父级可直接消费精简阶段结果，不必重读完整子代理 transcript。工具执行本身失败时，`PostToolUseFailure` 可提供错误信息，供执行者在**现有**阶段边界汇报；不得把每次失败命令都升级成新的高价值决策检查点。这两种事件都不能替代明确的进度证据、最终验证或父级的 Control 选择。只有当前 Claude Code Runtime 实际安装 Hooks 时才使用，不能套用于无关 Desktop Chat 对话。

官方依据：[SubagentStop 与 PostToolUseFailure 事件数据](https://code.claude.com/docs/en/hooks)。

已配置的 `PostToolUse` 可以在阶段边界提供实际工具结果，但不能替代压缩的 Progress Signal。Desktop Code 的 diff review 是修改行的证据，不是测试通过或独立验证完成的证明。[Anthropic：Hooks](https://code.claude.com/docs/en/hooks)、[Anthropic：Desktop diff review](https://code.claude.com/docs/en/desktop)。

## 相关概念

- [Coding Execution Control](execution-control_zh_cn.md) — 定位 Interaction Slice 边界。
- [Coding Execution Planning](execution-planning_zh_cn.md) — 定位有界计划和阶段提纲归属。
- [Coding Execution Decision Gate](execution-decision-gate_zh_cn.md) — 定位高价值决策条件。

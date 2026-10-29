# Coding Execution Planning

[English](execution-planning.md) | [简体中文](execution-planning_zh_cn.md)

本文档负责两级执行规划：将已批准方向转换为有界计划和阶段提纲，并安排 reconnaissance 在实现放行之前发生。不定义决策门禁策略、Interaction Slice 字段、阶段反馈、角色/Session 语义、上下文传输或委派生命周期。

## 通用规范

### 两级规划

将已批准方向转换为有界的检查、实现和定向检查步骤。计划记录阶段提纲以及每个阶段预期产出的证据，但不把阶段写成命令列表。

### 从 reconnaissance 到实现放行

在实质性决策前需要项目事实时，规划一个有界 reconnaissance slice，返回压缩事实、有证据支持的选项和未解决问题。随后由决策门禁确认或否定方向，再放行实现。规划不批准新的语义或架构方向。工作流的任务特定决策节点选择是否消费[规划意图下的计划 Memory 生命周期](planning-intent-plan-memory-lifecycle_zh_cn.md)；偶然提及规划、探索或计划不触发。`/plan` 等专用规划模式是可选起草方式。普通两级执行提纲和实时任务记录备注不是 Memory 计划文档。

## Codex CLI / ChatGPT Desktop 特别优化指令

在交互式 Codex CLI 或向 Agent Session 直接暴露 `/plan` 命令的环境中，调用 `/plan` 进入 Plan mode；也可以附加首次规划请求，例如 `/plan Propose a migration plan for this service`。Codex 会据此在实现前起草执行计划。Codex 正在工作时该命令不可用；若当前 Session 未暴露直接 `/plan` 控制，则使用通用有界规划流程。用户意图触发计划生命周期时，使用[规划意图下的计划 Memory 生命周期](planning-intent-plan-memory-lifecycle_zh_cn.md)持久化精简综合内容并核验存储条目；`/plan` 是可选起草方式，transcript 不是计划记录。必需 Memory 工具或权限不可用时，报告限制并阻塞依赖持久化，不得回退到文件。父级任务记录仍负责实时任务状态。[OpenAI：Slash commands](https://learn.chatgpt.com/docs/developer-commands)。

## Claude Code CLI / Claude Desktop 特别优化指令

已运行的 Claude Code Session 只有在同一 Session 直接暴露且授权 Plan-mode 控制时，才使用该模式草拟只读阶段计划；仅在启动时生效的参数及 Session 身份边界由[运行环境与模型厂商支持](../session-runtime/runtime-provider-support_zh_cn.md)负责。否则使用通用有界规划流程。用户意图触发计划生命周期时，使用 [规划意图下的计划 Memory 生命周期](planning-intent-plan-memory-lifecycle_zh_cn.md) 持久化精简综合阶段/证据提纲；Claude Plan mode 是可选起草方式；并遵守 Serena 工具实际暴露情况及有效权限。transcript 不能代替计划记录，也不得用于绕过权限；能力不可用时报告并阻塞依赖持久化，不得回退到文件。父级任务记录仍负责实时任务状态。编辑文件前仍须确认 Interaction Slice 已放行且工具权限实际生效。`/tasks` 报告运行中／后台 Agent 工作，不是持久计划记录，不能代替阶段检查点。[Anthropic：工作流](https://code.claude.com/docs/en/common-workflows)、[Anthropic：后台 Agent](https://code.claude.com/docs/en/sub-agents)。

## 相关概念

- [规划意图下的计划 Memory 生命周期](planning-intent-plan-memory-lifecycle_zh_cn.md) — 定位计划文档持久化与归档生命周期。
- [Coding Execution Control](../execution-control/execution-control_zh_cn.md) — 定位 Interaction Slice 放行和边界控制。
- [Coding Execution Decision Gate](execution-decision-gate_zh_cn.md) — 定位 Decision Brief 和实现放行决策。
- [Coding Execution Stage Feedback](../execution-control/execution-stage-feedback_zh_cn.md) — 定位有界阶段反馈。
- [Coding Session Model](../session-runtime/session-model_zh_cn.md) — 定位角色和 Session 归属。
- [Coding Context Exchange](../context-exchange/context-exchange_zh_cn.md) — 定位上下文传输归属。
- [Coding 子 Agent 生命周期](../delegation/delegation-child-lifecycle_zh_cn.md) — 定位委派生命周期归属。

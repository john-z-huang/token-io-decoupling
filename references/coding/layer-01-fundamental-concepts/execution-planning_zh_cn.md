# Coding Execution Planning

[English](execution-planning.md) | [简体中文](execution-planning_zh_cn.md)

本文档负责两级执行规划：将已批准方向转换为有界计划和阶段提纲，并安排 reconnaissance 在实现放行之前发生。不定义决策门禁策略、Interaction Slice 字段、阶段反馈、角色/Session 语义、上下文传输或委派生命周期。

## 通用规范

### 两级规划

将已批准方向转换为有界的检查、实现和定向检查步骤。计划记录阶段提纲以及每个阶段预期产出的证据，但不把阶段写成命令列表。

### 从 reconnaissance 到实现放行

在实质性决策前需要项目事实时，规划一个有界 reconnaissance slice，返回压缩事实、有证据支持的选项和未解决问题。随后由决策门禁确认或否定方向，再放行实现。规划不批准新的语义或架构方向。

## Codex CLI / ChatGPT Desktop 特别优化指令

在交互式 Codex CLI 或向 Agent Session 直接暴露 `/plan` 命令的环境中，调用 `/plan` 进入 Plan mode；也可以附加首次规划请求，例如 `/plan Propose a migration plan for this service`。Codex 会据此在实现前起草执行计划。Codex 正在工作时该命令不可用；若当前 Session 未暴露直接 `/plan` 控制，则使用通用有界规划流程。最终阶段大纲应保留在父级任务记录或获准计划产物中，不能以 Plan mode transcript 另立政策 owner。[OpenAI：Slash commands](https://learn.chatgpt.com/docs/developer-commands)。

## Claude Code CLI / Claude Desktop 特别优化指令

已运行的 Claude Code Session 只有在同一 Session 直接暴露且授权 Plan-mode 控制时，才使用该模式草拟只读阶段计划；仅在启动时生效的参数及 Session 身份边界由[运行环境与模型厂商支持](runtime-provider-support_zh_cn.md)负责。否则使用通用有界规划流程。阶段与证据大纲应保留在获准计划产物或父级任务记录中，不能以 Plan-mode 对话历史另立政策 owner。编辑文件前仍须确认 Interaction Slice 已放行且工具权限实际生效。`/tasks` 报告运行中／后台 Agent 工作，不是持久计划记录，不能代替阶段检查点。[Anthropic：工作流](https://code.claude.com/docs/en/common-workflows)、[Anthropic：后台 Agent](https://code.claude.com/docs/en/sub-agents)。

## 相关概念

- [Coding Execution Control](execution-control_zh_cn.md) — 定位 Interaction Slice 放行和边界控制。
- [Coding Execution Decision Gate](execution-decision-gate_zh_cn.md) — 定位 Decision Brief 和实现放行决策。
- [Coding Execution Stage Feedback](execution-stage-feedback_zh_cn.md) — 定位有界阶段反馈。
- [Coding Session Model](session-model_zh_cn.md) — 定位角色和 Session 归属。
- [Coding Context Exchange](context-exchange_zh_cn.md) — 定位上下文传输归属。
- [Coding 子 Agent 生命周期](delegation-child-lifecycle_zh_cn.md) — 定位委派生命周期归属。

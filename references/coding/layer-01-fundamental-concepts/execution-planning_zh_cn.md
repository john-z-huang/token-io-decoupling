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

Claude Code 可在启动时使用 `claude --permission-mode plan` 进入只读 Plan mode；交互式 CLI 中可按 `Shift+Tab` 直到 Plan mode 生效。Plan mode 会读取文件并提出方案，在获批前不会修改文件。应复用通用规则中的阶段与证据大纲，不把 `/plan` 的对话历史另立为政策 owner。计划完成后仍须检查 Interaction Slice 获准及工具权限，才能编辑文件。`/tasks` 报告运行中／后台 Agent 工作，不是持久计划记录，不能代替阶段检查点。其他 Session 只有在向 Agent 直接暴露 Plan-mode 命令或控制时才使用该模式。[Anthropic：工作流](https://code.claude.com/docs/en/common-workflows)、[Anthropic：后台 Agent](https://code.claude.com/docs/en/sub-agents)。

## 相关概念

- [Coding Execution Control](execution-control_zh_cn.md) — 定位 Interaction Slice 放行和边界控制。
- [Coding Execution Decision Gate](execution-decision-gate_zh_cn.md) — 定位 Decision Brief 和实现放行决策。
- [Coding Execution Stage Feedback](execution-stage-feedback_zh_cn.md) — 定位有界阶段反馈。
- [Coding Session Model](session-model_zh_cn.md) — 定位角色和 Session 归属。
- [Coding Context Exchange](context-exchange_zh_cn.md) — 定位上下文传输归属。
- [Coding 子 Agent 生命周期](delegation-child-lifecycle_zh_cn.md) — 定位委派生命周期归属。

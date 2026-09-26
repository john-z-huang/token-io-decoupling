# Coding Execution Control

[English](execution-control.md) | [简体中文](execution-control_zh_cn.md)

本文档负责 Interaction Slice 控制：slice 放行字段、边界行为和 Control Checkpoint 选择。它假定规划、决策门禁、阶段反馈、角色/Session 上下文、运行环境能力、上下文传输和委派生命周期由各自 owner 概念提供，不定义这些策略。

## 通用规范

### Interaction Slice

对于非简单工作，每次只放行一个 **Interaction Slice**。每个 slice 必须写明：

- `Objective`：必须产出的结果；
- `Authorized scope/mutations`：允许的路径、行为和写入；
- `Return conditions`：结束 slice 的证据或里程碑；
- `Unreleased boundary`：仍被阻塞的下一个子系统、风险域、语义选择或变更。

Slice 是控制单元，不是逐命令脚本。只要 Contract 和边界未变，执行者可以继续处理低决策密度的机械步骤；到达 return conditions 或跨越未放行边界前必须暂停。简单的快路径任务可以将实现和聚焦检查保留在一个 slice 中。

### Slice 顺序

只有相互独立且不冲突的 slice 才可并行放行。存在依赖、共享写入目标或有序结果时必须顺序放行。上下文传输和仅限父级的反馈遵循各自 owner 协议，本文档不定义这些内容。

### Control Checkpoint

到达实质性边界时，消费[执行阶段反馈](execution-stage-feedback_zh_cn.md)定义的 Progress Signal，附加当前 `Unreleased boundary`，再选择一个最终控制结果：`Continue`、`Amend` 或 `Stop`。`Continue` 只放行下一个有界 Slice；`Amend` 必须先修改 Contract 或边界再恢复执行。`Evidence-on-Demand` 是暂停放行并请求证据的中间动作，取得证据后重新经过本检查点；它不是第四种最终授权结果。单代理路线中这是内部推理暂停，不模拟发给自己的消息。

## Codex CLI / ChatGPT Desktop 特别优化指令

目前没有针对该厂商的特别优化指令；遵循上述通用规范。

## Claude Code CLI / Claude Desktop 特别优化指令

目前没有针对该厂商的特别优化指令；遵循上述通用规范。

### 工具边界守卫与语义 Control 的区分

已获准的 Claude Code `PreToolUse` Hook 可以拒绝某项具体 `Bash`、`Write`、`Edit` 或具有外部影响的 MCP 操作，防止其越过可机器校验的已放行路径/权限边界。`Stop` Hook 可以在当前 Agent 结束前请求最终证据检查。这些都只是**守卫**，不是 `Continue`、`Amend`、`Stop` 的替代决策权：父级仍须消费 Progress Signal，并按通用规则批准每个新 Slice。Hook 的退出/deny 信号、Desktop 可视化审查或 MCP 连接器不得暗中扩大 Contract 或子代理预算。不得声称 Desktop Chat/Cowork 具备这些原生 Hooks。

官方依据：[Claude Code Hooks 与决策](https://code.claude.com/docs/en/hooks)。

## 相关概念

- [Coding Execution Planning](execution-planning_zh_cn.md) — 定位有界规划和 reconnaissance 到实现放行的关系。
- [Coding Execution Decision Gate](execution-decision-gate_zh_cn.md) — 定位 Decision Brief 和决策放行规则。
- [Coding Execution Stage Feedback](execution-stage-feedback_zh_cn.md) — 定位有界阶段反馈规则。
- [Coding Context Exchange](context-exchange_zh_cn.md) — 定位上下文传输归属。
- [Coding 子 Agent 生命周期](delegation-child-lifecycle_zh_cn.md) — 定位已放行 slice 的委派生命周期归属。

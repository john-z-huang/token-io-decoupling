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

可用且已启用时，Codex `PreToolUse` 可在受支持的 `Bash`、编辑或 MCP 调用执行前拒绝操作；`PostToolUse` 只能在调用**结束后**观察。Codex 的 plan／只读及其他权限模式属于工具控制，不等于本 Skill 的 `Continue` 决策。Hook 覆盖并非完整，不能把它作为文件系统或语义授权边界的唯一证明。[OpenAI：Hooks](https://learn.chatgpt.com/docs/hooks)。

### 原生审批与聚焦审查

已配置且可信时，Codex `PreToolUse` 可通过受支持的阻止决策拒绝本地工具调用；对该事件返回 `continue: false` **不是**受支持的阻止格式。`PostToolUse` 在副作用发生后才报告，不能追认授权。阶段边界可用 Desktop Codex review pane 或 CLI `/diff` 检查真实工作树 diff，再由父级完成语义上的 `Continue`／`Amend`／`Stop` 选择。review pane 的 stage／revert 是独立仓库修改，不证明 Contract 或最终 Verification 已通过。[OpenAI：PreToolUse 输出契约](https://learn.chatgpt.com/docs/hooks)、[OpenAI：Code review](https://learn.chatgpt.com/docs/code-review)、[OpenAI：CLI diff](https://learn.chatgpt.com/docs/developer-commands)。

## Claude Code CLI / Claude Desktop 特别优化指令

### 工具边界守卫与语义 Control 的区分

已获准的 Claude Code `PreToolUse` Hook 可以拒绝某项具体 `Bash`、`Write`、`Edit` 或具有外部影响的 MCP 操作，防止其越过可机器校验的已放行路径/权限边界。`Stop` Hook 可以在当前 Agent 结束前请求最终证据检查。这些都只是**守卫**，不是 `Continue`、`Amend`、`Stop` 的替代决策权：父级仍须消费 Progress Signal，并按通用规则批准每个新 Slice。Hook 的退出/deny 信号、Desktop 可视化审查或 MCP 连接器不得暗中扩大 Contract 或子代理预算。不得声称 Desktop Chat/Cowork 具备这些原生 Hooks。

官方依据：[Claude Code Hooks 与决策](https://code.claude.com/docs/en/hooks)。

Claude Code 的 `PostToolUse` 在操作后提供观察结果，不能倒过来授权已经执行的操作。Desktop Code 的 permission-mode selector 管理工具审批，不是本 Skill 的 Contract／Control 决策。[Anthropic：Hooks](https://code.claude.com/docs/en/hooks)、[Anthropic：Desktop Code](https://code.claude.com/docs/en/desktop)。

## 相关概念

- [Coding Execution Planning](execution-planning_zh_cn.md) — 定位有界规划和 reconnaissance 到实现放行的关系。
- [Coding Execution Decision Gate](execution-decision-gate_zh_cn.md) — 定位 Decision Brief 和决策放行规则。
- [Coding Execution Stage Feedback](execution-stage-feedback_zh_cn.md) — 定位有界阶段反馈规则。
- [Coding Context Exchange](context-exchange_zh_cn.md) — 定位上下文传输归属。
- [Coding 子 Agent 生命周期](delegation-child-lifecycle_zh_cn.md) — 定位已放行 slice 的委派生命周期归属。

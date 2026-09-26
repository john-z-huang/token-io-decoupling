# Coding Session Model

[English](session-model.md) | [简体中文](session-model_zh_cn.md)

本模块负责 Coding 的 Session 语义、单代理与多代理 Session 映射、Primary Execution Session Affinity，以及复用/worktree 隔离边界。它消费 owner 概念提供的职责归属和当前工作流的状态；不定义职责责任、Context Firewall、运行环境 eligibility、执行参数、dispatch 格式、上下文文件传输或验收流程。

## 通用规范

### Session 语义

模式、拓扑、职责分配、生命周期、复用、替换、例外和不可用处理由当前工作流提供。职责名称本身不能授权新建 Session 或改变拓扑。

单代理 Coding 中，当前 Session 执行逻辑上的决策、实现、文档、Git 和允许的检查阶段；逻辑职责不表示存在独立 Agent。多代理 Coding 中，只使用当前工作流明确提供的子级执行上下文；具体 Session 隔离由运行环境决定：

```text
根父上下文 → Input-side Reasoning
已分配 Primary 子级上下文 → Primary Output
已分配 verifier 子级上下文 → Change Verification
已分配文档/Git 子级上下文 → Documentation/Comments & Git Operations
```

未分配的职责在独立子级上下文层面不可用。不得通过给同一上下文的工作改名来模拟独立性。

### Primary Execution Session 与 Affinity

维持一个 Primary Execution Session：多代理模式下为已分配的 Primary Output Session，否则为当前 Session。相关探索、实现、诊断、测试、修复和局部执行优先复用它，以保留稳定上下文。Session 应保持 sticky but not immortal；生命周期变化遵循当前工作流的已记录状态。

Session 隔离与 Git worktree 隔离不同。工作区和文件系统隔离条件由[上下文工作区边界](context-exchange-workspace-boundary_zh_cn.md)定义；不得仅因复用 Session 就声称命中缓存或获得其他运行时收益。

## Codex CLI / ChatGPT Desktop 特别优化指令

已分配的 Codex 子代理使用独立子 Session 和任务界面。只报告运行环境实际暴露的隔离能力。

### 桌面对话、Child 和 Worktree 是不同身份

Desktop Codex 的项目 chat 是根 Session；只有当前 Session 暴露的工具报告明确父子关系时，spawned subagent thread 才是该 chat 的 Child；可见面板本身不是 Agent 工具。在 `Worktree` 新建的 chat 属于独立对话及 Git checkout；`Handoff` 只在 Local 和 Worktree 间移动**同一个 chat**，不会转换父子代理身份。Codex 管理的 worktree 可能是 detached HEAD 且可清理；复用工作目录或 pin 住 chat 都不能证明验证者具有独立模型上下文。同一应用内的普通 Chat 或 Work 会话也不会默默成为当前 Codex Child。[OpenAI：子代理线程](https://learn.chatgpt.com/docs/agent-configuration/subagents)、[OpenAI：worktree 与 Handoff](https://learn.chatgpt.com/docs/environments/git-worktrees)、[OpenAI：Desktop 模式](https://learn.chatgpt.com/docs/use-chatgpt)。

## Claude Code CLI / Claude Desktop 特别优化指令

Claude Code 子代理在父会话中拥有独立上下文，没有完全相同的 Codex 独立任务界面。把它视为已分配的子级上下文，只向父级返回，并准确报告实际隔离和验证独立性。不得以 agent team 或 peer channel 替代。父级记录和结果已提供所需证据时，不必为 Codex 专有界面便利功能寻找 Claude Code 对应项。

Claude Code 子代理的 `Agent` 调用及返回 ID 标识父 Session 内的一个子代理上下文；内置 Explore 和 Plan 属于一次性 Agent，不返回可恢复 ID。后续可能需要获准 follow-up 时，保留父级身份与返回的 ID。`/resume` 恢复的是 Claude Code 会话，不是任意一次性子代理。[Anthropic：子代理上下文与恢复](https://code.claude.com/docs/en/sub-agents)。

Claude Desktop 的 **Code 标签页**可将不同的本地 Session 隔离到各自 Git worktree；这些是独立桌面 Session，不能默认为当前 `Agent` 调用所分配的 Child。普通 Desktop Chat 没有文档证明具备等价的 Code 标签页 worktree Session 控制。没有经核验的父级可控 Agent 身份时，不得把独立面板或 worktree 算作锁定数量内的子代理。[Anthropic：Desktop Session](https://code.claude.com/docs/en/desktop)。

## 相关概念

- [Coding Session Role Ownership](session-role-ownership_zh_cn.md) — 定位职责责任归属。
- [Coding Session Context Firewall](session-context-firewall_zh_cn.md) — 定位原始状态进入边界。
- [Coding Delegation State Record](delegation-state-record_zh_cn.md) — 定位任务控制状态归属。
- [Coding Context Exchange](context-exchange_zh_cn.md) — 定位文件化上下文传输归属。
- [Coding Execution Control](execution-control_zh_cn.md) — 定位 Interaction Slice 和 Session 边界控制。

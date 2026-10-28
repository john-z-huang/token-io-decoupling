# Coding Session Model

[English](session-model.md) | [简体中文](session-model_zh_cn.md)

本模块负责 Coding 的 Session 语义、单代理与多代理 Session 映射、Primary Execution Session Affinity，以及复用/worktree 隔离边界。它消费 owner 概念提供的职责归属和当前工作流的状态；不定义职责责任、Context Firewall、运行环境 eligibility、执行参数、dispatch 格式、项目上下文传输或验收流程。

## 通用规范

### Session 语义

模式、拓扑、职责分配、生命周期、复用、替换、例外和不可用处理由当前工作流提供。职责名称本身不能授权新建 Session 或改变拓扑。

本文中的 Session 指宿主识别的完整 Session 生命周期，而不是一次用户/助手交互。同一 Session 的后续轮次、compact 或恢复都沿用其模式、数量和子代理身份。具有新 Session 身份的 Fork 开始独立生命周期，必须重新通过门禁。

Fork 会以新的根身份开启新的 Coding Session。在开展依赖工作前，必须重新通过模式/数量选择，即使来源 Session 使用过 Single-Agent 模式也一样。绑定到来源 Session 的子代理身份在 Fork 中属于其他会话：不得将其采纳为已创建子代理、复用或恢复、计入新会话预算，或提供给当前会话候选选择。新状态记录由[委派模式重入](delegation-mode-reentry_zh_cn.md)和[委派状态记录](delegation-state-record_zh_cn.md) owner 负责。

单代理 Coding 中，当前 Session 执行逻辑上的决策、实现、文档、Git 和允许的检查阶段；逻辑职责不表示存在独立 Agent。多代理 Coding 中，只使用当前工作流明确提供的子级执行上下文；具体 Session 隔离由运行环境决定：

```text
根父上下文 → Input-side Reasoning
已分配 Primary 子级上下文 → Primary Output
已分配 verifier 子级上下文 → Change Verification
已分配文档/Git 子级上下文 → Documentation/Comments & Git Operations
```

未分配的职责在独立子级上下文层面不可用。不得通过给同一上下文的工作改名来模拟独立性。
不得从预留名额数量推断职责；一个名额不会自动表示 Primary Output。只有审阅当前任务上下文和 Decision 后才能选择职责，再由职责选择与分配 owner 记录到未分配名额中。

### Primary Execution Session 与 Affinity

维持一个 Primary Execution Session：Single-Agent 模式下为当前 Session；Multi-Agent 模式下为已经创建且分配了 `Primary Output` 的子代理（如果存在）。在该子代理创建前，当前根 Session 仍是活跃决策上下文，但这不隐含创建 Primary 子代理。相关探索、实现、诊断、测试、修复和局部执行优先复用已分配的 Primary Session，以保留稳定上下文。Session 应保持 sticky but not immortal；生命周期变化遵循当前工作流的已记录状态。

Session 隔离与 Git worktree 隔离不同。工作区和文件系统隔离条件由[上下文工作区边界](context-exchange-workspace-boundary_zh_cn.md)定义；不得仅因复用 Session 就声称命中缓存或获得其他运行时收益。

## Codex CLI / ChatGPT Desktop 特别优化指令

已分配的 Codex 子代理使用独立子 Session。只有运行时元数据或直接暴露的子代理／线程工具能够证明该关系；只报告这些来源明确显示的隔离能力。

对 Codex 而言，Session 从宿主 Session 开始持续到其结束，不会因每轮用户/助手交互而重置。对同一 Session 执行 compact、重新打开或恢复时，沿用其模式/数量及子代理身份记录。Fork 会创建新的 Session 身份，必须重新通过模式重入门禁。

### Desktop Session 与子代理身份

在 ChatGPT Desktop 中，只有当前 Session 暴露的工具报告明确父子关系时，才将 spawned Codex thread 记为 Child。通过工具创建或转移另一个 Session／worktree 本身不能建立子代理身份；Codex 管理的 worktree 可能是 detached HEAD 且可清理。只有暴露的工具报告相关关系时，Chat 或 Work Session 才能算作 Codex Child。[OpenAI：子代理线程](https://learn.chatgpt.com/docs/agent-configuration/subagents)、[OpenAI：worktree 行为](https://learn.chatgpt.com/docs/environments/git-worktrees)、[OpenAI：Desktop 模式](https://learn.chatgpt.com/docs/use-chatgpt)。

## Claude Code CLI / Claude Desktop 特别优化指令

Claude Code 子代理在父会话中拥有独立上下文。将其视为已分配的子级上下文，只向父级返回，并准确报告实际隔离和验证独立性。不得以 agent team 或 peer channel 替代。

Claude Code 子代理的 `Agent` 调用及返回 ID 标识父 Session 内的一个子代理上下文；内置 Explore 和 Plan 属于一次性 Agent，不返回可恢复 ID。后续可能需要获准 follow-up 时，保留父级身份与返回的 ID。`/resume` 恢复的是 Claude Code 会话，不是任意一次性子代理。[Anthropic：子代理上下文与恢复](https://code.claude.com/docs/en/sub-agents)。

Claude Desktop 只有在当前 Session 直接暴露内建 `Agent` 或 `SendMessage` 工具时才能调用。单独识别出的 Session、连接器工具调用或 worktree 不属于已分配的 Child，除非父级控制的工具结果明确报告这一身份关系。[Anthropic：子代理上下文与生命周期](https://code.claude.com/docs/en/sub-agents)、[Anthropic：Desktop MCP 工具](https://support.claude.com/en/articles/10949351-getting-started-with-local-mcp-servers-on-claude-desktop)。

## 相关概念

- [Coding Session Role Ownership](session-role-ownership_zh_cn.md) — 定位职责责任归属。
- [Coding Session Context Firewall](session-context-firewall_zh_cn.md) — 定位原始状态进入边界。
- [Coding Delegation State Record](delegation-state-record_zh_cn.md) — 定位任务控制状态归属。
- [Coding Delegation Mode Re-entry](delegation-mode-reentry_zh_cn.md) — 定位 Fork 的全新模式/数量选择。
- [Coding Child Role Selection](child-role-selection_zh_cn.md) — 定位新子代理职责的选择判断。
- [Coding Task Assignment](task-assignment_zh_cn.md) — 定位 Root 和现有子代理的选择。
- [Coding Context Exchange](context-exchange_zh_cn.md) — 定位文件化上下文传输归属。
- [Coding Execution Control](execution-control_zh_cn.md) — 定位 Interaction Slice 和 Session 边界控制。

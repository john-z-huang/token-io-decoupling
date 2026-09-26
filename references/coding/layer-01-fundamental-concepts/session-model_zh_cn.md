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

维持一个 Primary Execution Session：多代理模式下是已分配的 Primary Output Session，否则是当前 Session。相关探索、实现、诊断、测试、修复和局部执行优先复用它，以保留稳定上下文。Session 应保持 sticky but not immortal；生命周期变化遵循当前工作流的已记录状态。

Session 隔离与 Git worktree 隔离不同。同一开发需求的 Worker 通常共享 primary worktree；隔离 worktree 必须有明确放行的隔离范围。不得仅因复用 Session 就宣称一定命中缓存或获得其他运行时收益。

## Codex CLI / ChatGPT Desktop 特别优化指令

已分配的 Codex 子代理使用独立子 Session 和任务界面。只报告运行环境实际暴露的隔离能力。

## Claude Code CLI / Claude Desktop 特别优化指令

Claude Code 子代理在父会话中拥有独立上下文，没有完全相同的 Codex 独立任务界面。把它视为已分配的子级上下文，只向父级返回，并准确报告实际隔离和验证独立性。不得以 agent team 或 peer channel 替代。父级记录和结果已提供所需证据时，不必为 Codex 专有界面便利功能寻找 Claude Code 对应项。

## 相关概念

- [Coding Session Role Ownership](session-role-ownership_zh_cn.md) — 定位职责责任归属。
- [Coding Session Context Firewall](session-context-firewall_zh_cn.md) — 定位原始状态进入边界。
- [Coding Delegation State Record](delegation-state-record_zh_cn.md) — 定位任务控制状态归属。
- [Coding Context Exchange](context-exchange_zh_cn.md) — 定位文件化上下文传输归属。
- [Coding Execution Control](execution-control_zh_cn.md) — 定位 Interaction Slice 和 Session 边界控制。

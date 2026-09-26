# Coding 子 Agent 复用与替换

[English](delegation-child-reuse-replacement.md) | [简体中文](delegation-child-reuse-replacement_zh_cn.md)

本文档负责已创建子 Agent 的获准 follow-up、修复 epoch 以及复用或替换关系。不定义子 Agent 创建、职责分配、Dispatch Preview、Worker 边界、生命周期状态或上下文传输。

## 通用规范

### 获准复用

修复优先于 replacement：对获准的 follow-up 和修复 epoch 复用同一个子 Agent。发生错误或中断后，先通过同一个子 Agent 尝试获准修复；否则报告阻塞。复用不得创建递归层级或 peer 协调。

### 替换关系

替换不同于普通的同一子 Agent 复用，只能在 `child_count` 尚未锁定时调整计划级 allocation。保持本次会话选定的数量；准备阶段不得再次询问数量，也不得创建、spawn 或 handoff 到新子 Agent。先锁定数量并满足路线放行条件，child-creation owner 才能创建计划中的子 Agent。数量锁定后，如果同一个子 Agent 无法安全复用，报告阻塞并将多代理路线置为 `blocked`；不得创建 replacement child。替换不是 peer 协调，也不是递归层级。本模块不定义 handoff 或上下文传输；相关规则定位于 [context exchange](context-exchange_zh_cn.md)。

## Codex CLI / ChatGPT Desktop 特别优化指令

目前没有针对该厂商的特别优化指令；遵循上述通用规范。

## Claude Code CLI / Claude Desktop 特别优化指令

获准跟进或修复同一子代理时，使用返回的 Agent ID 调用 `SendMessage`。再次调用 `Agent` 会创建另一个子代理并消耗另一个名额；数量锁定后不得将其用于复用。

## 相关概念

- [Coding Child Creation](delegation-child-creation_zh_cn.md) — 定位子 Agent 创建能力。
- [Coding Child Role Allocation](delegation-child-role-allocation_zh_cn.md) — 定位名额和职责分配。
- [Coding Child Dispatch](delegation-child-dispatch_zh_cn.md) — 定位实际派发边界。
- [Coding Child Lifecycle](delegation-child-lifecycle_zh_cn.md) — 定位子 Agent 状态和恢复归属。
- [Coding Context Exchange](context-exchange_zh_cn.md) — 定位 handoff 和上下文传输归属。

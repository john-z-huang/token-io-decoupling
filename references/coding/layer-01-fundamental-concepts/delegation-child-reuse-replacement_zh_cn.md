# Coding 子 Agent 复用与替换

[English](delegation-child-reuse-replacement.md) | [简体中文](delegation-child-reuse-replacement_zh_cn.md)

本文档负责已创建子 Agent 的获准 follow-up、修复 epoch 以及复用或替换关系。不定义子 Agent 创建、职责分配、Dispatch Preview、Worker 边界、生命周期状态或上下文传输。

## 获准复用

对获准的 follow-up 和修复 epoch 复用同一个子 Agent。发生错误或中断后，只有获准的修复才允许复用；否则报告阻塞。复用不得创建递归层级或 peer 协调。

## 替换关系

替换不同于普通的同一子 Agent 复用，并遵循父级控制的 delegation lifecycle。本模块不定义 handoff 或上下文传输；相关规则定位于 [context exchange](context-exchange_zh_cn.md)。

## 相关概念

- [Coding Child Creation](delegation-child-creation_zh_cn.md) — 定位子 Agent 创建能力。
- [Coding Child Role Allocation](delegation-child-role-allocation_zh_cn.md) — 定位名额和职责分配。
- [Coding Child Dispatch](delegation-child-dispatch_zh_cn.md) — 定位实际派发边界。
- [Coding Child Lifecycle](delegation-child-dispatch-lifecycle_zh_cn.md) — 定位子 Agent 状态和恢复归属。
- [Coding Context Exchange](context-exchange_zh_cn.md) — 定位 handoff 和上下文传输归属。

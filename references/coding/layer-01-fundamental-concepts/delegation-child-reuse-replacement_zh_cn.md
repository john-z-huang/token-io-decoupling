# Coding 子 Agent 复用与替换

[English](delegation-child-reuse-replacement.md) | [简体中文](delegation-child-reuse-replacement_zh_cn.md)

本文档负责已创建子 Agent 的获准 follow-up、修复 epoch 以及复用或替换关系。不定义子 Agent 创建、职责分配、Dispatch Preview、Worker 边界、生命周期状态或上下文传输。

## 获准复用

修复优先于 replacement：对获准的 follow-up 和修复 epoch 复用同一个子 Agent。发生错误或中断后，先通过同一个子 Agent 尝试获准修复；否则报告阻塞。复用不得创建递归层级或 peer 协调。

## 替换关系

替换不同于普通的同一子 Agent 复用，只能发生在 `child_count` 尚未锁定的受控准备阶段。锁定前的 replacement path 仅用于计划级恢复：父级可以更新拟定的 allocation 或数量，但不得创建、spawn 或 handoff 到新子 Agent，也不得消耗子 Agent 名额。随后父级必须重新确认或更新方案，锁定最终数量，并在第一次 Dispatch 前重新满足路线放行条件。只有在此之后，child-creation owner 才能把实际 successor 或 replacement child 作为最终锁定集合的一部分创建。数量锁定后，如果同一个子 Agent 无法安全复用，父级必须报告阻塞并将多代理路线置为 `blocked`，不得创建 replacement child。替换不是 peer 协调，也不是递归层级。本模块不定义 handoff 或上下文传输；相关规则定位于 [context exchange](context-exchange_zh_cn.md)。

## 相关概念

- [Coding Child Creation](delegation-child-creation_zh_cn.md) — 定位子 Agent 创建能力。
- [Coding Child Role Allocation](delegation-child-role-allocation_zh_cn.md) — 定位名额和职责分配。
- [Coding Child Dispatch](delegation-child-dispatch_zh_cn.md) — 定位实际派发边界。
- [Coding Child Lifecycle](delegation-child-lifecycle_zh_cn.md) — 定位子 Agent 状态和恢复归属。
- [Coding Context Exchange](context-exchange_zh_cn.md) — 定位 handoff 和上下文传输归属。

# Coding 子 Agent 派发

[English](delegation-child-dispatch.md) | [简体中文](delegation-child-dispatch_zh_cn.md)

本文档负责实际派发前的 Dispatch Preview 和 Worker 边界。它消费已获授权的子 Agent 和 slice；不定义子 Agent 创建、职责分配、复用或替换、生命周期或 Interaction Slice 字段。

## Dispatch Preview 和返回边界

每次实际派发前，都要对已授权的 slice 发出简洁 preview。Worker 只能返回其直接父级；不得创建、fork、handoff、向其他 Agent 或 Session 发消息、替换或协调其他 Agent 或 Session，也不得联系任意线程。Worker findings 不得改变 root mode 或 count。

## Named path 和 slice 放行

每个 Worker 的 context-exchange 目录必须保持分离，并且只授予 named paths。除非明确允许独立且不冲突的并行工作，否则一次只放行一个 Interaction Slice。Interaction Slice 字段和边界控制归 [execution control](execution-control_zh_cn.md) 定义。

## 相关概念

- [Coding Child Creation](delegation-child-creation_zh_cn.md) — 定位子 Agent 创建能力。
- [Coding Child Role Allocation](delegation-child-role-allocation_zh_cn.md) — 定位名额和职责分配。
- [Coding Child Lifecycle](delegation-child-lifecycle_zh_cn.md) — 定位子 Agent 状态和恢复归属。
- [Coding Child Reuse and Replacement](delegation-child-reuse-replacement_zh_cn.md) — 定位获准的复用和替换。
- [Coding Context Exchange](context-exchange_zh_cn.md) — 定位 named-path 上下文传输归属。
- [Coding Execution Control](execution-control_zh_cn.md) — 定位 Interaction Slice 边界控制。

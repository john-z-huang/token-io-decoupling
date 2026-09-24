# Coding 子 Agent 派发

[English](delegation-child-dispatch.md) | [简体中文](delegation-child-dispatch_zh_cn.md)

本文档负责实际派发前的 Dispatch Preview 和 Worker 边界。它消费已获授权的子 Agent 和 slice；不定义子 Agent 创建、职责分配、复用或替换、生命周期或 Interaction Slice 字段。

## Dispatch Preview 和返回边界

分配子代理或进行实质性派发前，父级必须亲自分析指令、确认项目环境，并核实定义任务所需的代码细节。记录支持性路径与事实，然后对已授权 slice 发出包含精确目标、允许改动和返回条件的简洁 preview。不得分配子代理完成这些前置确认。若所需事实尚未确认，slice 留在父级，直至确认完成。Worker 只能返回其直接父级；不得创建、fork、handoff、向其他 Agent 或 Session 发消息、替换或协调其他 Agent 或 Session，也不得联系任意线程。与已确认前提冲突的 Worker findings 须返回父级重新决策，不能改变 root mode 或 count。

## Named path 和 slice 放行

每个 Worker 的 context-exchange 目录必须保持分离，并且只授予 named paths。除非明确允许独立且不冲突的并行工作，否则一次只放行一个 Interaction Slice。Interaction Slice 字段和边界控制归 [execution control](execution-control_zh_cn.md) 定义。

## 相关概念

- [Coding Child Creation](delegation-child-creation_zh_cn.md) — 定位子 Agent 创建能力。
- [Coding Child Role Allocation](delegation-child-role-allocation_zh_cn.md) — 定位名额和职责分配。
- [Coding Child Lifecycle](delegation-child-lifecycle_zh_cn.md) — 定位子 Agent 状态和恢复归属。
- [Coding Child Reuse and Replacement](delegation-child-reuse-replacement_zh_cn.md) — 定位获准的复用和替换。
- [Coding Context Exchange](context-exchange_zh_cn.md) — 定位 named-path 上下文传输归属。
- [Coding Execution Control](execution-control_zh_cn.md) — 定位 Interaction Slice 边界控制。

# 规划输出选择

[English](planning-output-selection.md) | [简体中文](planning-output-selection_zh_cn.md)

本检查点负责当前任务是否消费计划记忆产出生命周期。


## 触发与输入

在 S06/M07 且已建立当前事实和 Decision 输入后，判断用户目标是否要求规划、探索或产出/更新计划。应用[Execution Planning](../layer-01-fundamental-concepts/execution-planning/execution-planning_zh_cn.md)，且仅在触发时应用[Planning Intent Plan Memory Lifecycle](../layer-01-fundamental-concepts/execution-planning/planning-intent-plan-memory-lifecycle_zh_cn.md)。

## 决策与结果

1. 保留用户的规划意图和触发该分支的 Decision 证据。
2. 意图触发时，通过计划记忆生命周期 owner 创建或更新简明计划，随后读回存储项，并在依赖工作前将其与预期结果比较。
3. 若没有该意图，记录带有目标证据的 `Not applicable`；继续普通 Decision 规划及其执行计划。
4. 向路线调度返回已核实的计划/读回证据、`Not applicable` 或阻塞结果。归档只由 Acceptance 负责。

## 失败边界

必需持久化能力不可用或写入/回读失败时，阻塞依赖工作。本选择不授权额外效果、不改变用户目标，也不削弱计划记忆 owner 的命名、不可变、归档和失败规则。

## 相关概念

- [规划意图下的计划 Memory 生命周期](../layer-01-fundamental-concepts/execution-planning/planning-intent-plan-memory-lifecycle_zh_cn.md)

# 规划输出选择

[English](planning-output-selection.md) | [简体中文](planning-output-selection_zh_cn.md)

本检查点根据生命周期 owner 判断当前任务默认共享计划的输出及其持久化/核验证据。

## 触发与输入

每项 Coding 任务均消费当前用户目标、存在时的 Issue/讨论、已核实项目事实、Decision 和任何明确持久化限制。应用[执行规划](../layer-01-fundamental-concepts/execution-planning/execution-planning_zh_cn.md)和[任务计划 Memory 生命周期](../layer-01-fundamental-concepts/execution-planning/task-plan-memory-lifecycle_zh_cn.md)。

## 决策与结果

1. 保留任务目标、来源、当前事实和拟议方案。有无 Issue 均默认选择共享计划；没有明确规划请求不是跳过条件。
2. 确认准确项目、所选仓库存储范围、对应活动/归档命名空间、活动计划身份、允许贡献和必需访问。共享存储时，核实同仓库各工作区复用同一规划映射，其他仓库保持隔离。身份/映射缺失或冲突时阻塞，不静默回退另一存储范围。创建或更新精简计划，确认获准持久化操作，并仅在生命周期 owner 要求时核验存储内容。向调用方返回计划身份、存储映射、持久化确认及任何必需核验证据。
3. 仅用户明确禁止或更高优先级持久化限制才允许 `Not applicable`，同时记录准确限制、来源和获授权的上下文内规划替代方式。与明确持久化要求冲突时阻塞；工具缺失、权限不明或持久化失败不是跳过条件。
4. 按生命周期 owner 规定的阶段、交接、暂停或完成边界记录实质更新。影响授权、范围、验收、方向或依赖动作的变化，须在该动作前记录并分析。普通进度汇报本身不触发计划写入。归档仍以 Acceptance 完成为条件。

## 失败边界

必需访问不可用、持久化失败或 owner 要求的核验失败时阻塞依赖工作。本选择不授权实施、不改变用户目标，也不削弱名称、更新协调、角色边界、归档或不可变规则。

## 相关概念

- [任务计划 Memory 生命周期](../layer-01-fundamental-concepts/execution-planning/task-plan-memory-lifecycle_zh_cn.md)

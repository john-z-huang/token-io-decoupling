# Contract 检查点

[English](contract.md) | [简体中文](contract_zh_cn.md)

## 动作

1. 用一句话说明用户要求的结果。
2. 记录硬性限制：用户禁止事项、允许的运行环境、仓库和 worktree 范围、允许使用的工具和路径、安全限制，以及明确授权的外部影响。
3. 记录已经确定的实质性决策、未解决问题和验收条件。
4. 区分已观察到的事实与假设。未解决的实质性问题不得进入实现发布。

5. Mode 和 Session 通过前，必须从直接权威来源确定任务意图和符合条件的输出分类。此时将建议标记为 `Not applicable`，因为尚无已授权 Root 上下文；不得提前初始化状态。已授权上下文存在后，建议仍独立于 Contract，不能授权其范围。遵循[Decisions 建议](../layer-01-fundamental-concepts/decisions-advisory_zh_cn.md)。

## 通过条件

目标、约束、决策和验收条件都已明确。如果缺少必要信息，停止依赖该信息的切片，并询问或报告具体缺少的输入。

## 边界

本检查点不选择执行模式，不检查整个仓库，不实现修改，不验证结果，不写文档，也不执行 Git 操作。

## 相关概念

- [Coding Execution Decision Gate](../layer-01-fundamental-concepts/execution-decision-gate_zh_cn.md) — 定位 Decision Brief 和放行条件归属。
- [Coding Execution Planning](../layer-01-fundamental-concepts/execution-planning_zh_cn.md) — 定位有界规划归属。

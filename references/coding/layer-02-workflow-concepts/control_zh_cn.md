# 控制边界检查点

[English](control.md) | [简体中文](control_zh_cn.md)

## 动作

1. 报告 `Status`、`Findings`、`Changed`、`Verification`、`Issue`、`Need` 和 `Unreleased boundary`。
2. 检查下一步是否引入公共接口、schema 或迁移、兼容性变化、安全敏感行为、新风险域、难以逆转的修改、范围扩大或外部影响。
3. 选择一个结果：在已批准范围内继续、修改 Contract 和决策、停止，或请求 Evidence-on-Demand。
4. 只有结果明确后才能发布下一切片。单代理模式将其作为逻辑暂停；多代理模式由父级控制发布。

## 通过条件

下一步要么已在当前范围内发布，要么已暂停并明确需要的修改、证据、能力或授权。

## 边界

本检查点控制发布和权限，不静默批准范围扩大，不替代验证，也不授予 Git 或外部影响授权。

## 相关概念

- [Coding Execution Control](../layer-01-fundamental-concepts/execution-control_zh_cn.md) — 定位 Interaction Slice 和控制边界归属。
- [Coding Execution Decision Gate](../layer-01-fundamental-concepts/execution-decision-gate_zh_cn.md) — 定位决策和放行条件归属。
- [Coding Delegation State Record Worker Boundary](../layer-01-fundamental-concepts/delegation-state-record-worker-boundary_zh_cn.md) — 定位父级控制的 Worker 放行边界。

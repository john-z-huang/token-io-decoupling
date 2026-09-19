# 修复检查点

[English](repair.md) | [简体中文](repair_zh_cn.md)

本检查点负责诊断失败证据、受影响路径和最小修复候选。发现候选超出已批准边界时，报告诊断结果；不授权或执行修复，也不定义验证 epoch。

## 动作

1. 说明失败证据、受影响路径和能够解决问题的最小修复。
2. 识别可能解决失败的最小候选，不预设其已获授权。
3. 如果候选改变范围、架构、安全、兼容性或其他实质性决策，则停止修复路线，并将该诊断结果返回 Contract 和决策检查点。

## 通过条件

失败证据、受影响路径和最小修复候选已经明确，或诊断结果已经指出缺少的决策或能力。

## 边界

本检查点不授权或执行修复，不运行修复检查，不定义验证 epoch，也不授权大范围清理、文档、Git 影响或外部影响。

## 相关概念

- [Coding Execution Decision Gate](../layer-01-fundamental-concepts/execution-decision-gate_zh_cn.md) — 定位实质性决策和放行条件归属。
- [Coding Execution Control](../layer-01-fundamental-concepts/execution-control_zh_cn.md) — 定位已批准 slice 和返回边界归属。
- [Coding Delegation State Record Worker Boundary](../layer-01-fundamental-concepts/delegation-state-record-worker-boundary_zh_cn.md) — 定位命名路径的 Worker 访问边界。

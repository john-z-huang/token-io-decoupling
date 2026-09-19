# 修复范围门禁

[English](repair-scope-gate.md) | [简体中文](repair-scope-gate_zh_cn.md)

本检查点负责候选修复的兼容性和授权门禁。它消费已诊断的修复候选；不诊断失败、不执行修复，也不定义验证 epoch。

## Contract 和决策兼容性

1. 确认候选修复仍在已批准的 Contract 和决策内。
2. 如果它改变范围、架构、安全、兼容性或其他实质性决策，则暂停，并在授权执行前返回 Contract 和决策检查点。

## 通过条件

候选修复已在批准范围内获得明确授权，或已在执行前明确需要的 Contract、决策或能力。

## 边界

本检查点不诊断失败证据，不选择修复内容，不执行修复，不运行聚焦检查，也不创建验证 epoch。

## 相关概念

- [Coding Execution Decision Gate](../layer-01-fundamental-concepts/execution-decision-gate_zh_cn.md) — 定位实质性决策和放行条件归属。
- [Coding Execution Control](../layer-01-fundamental-concepts/execution-control_zh_cn.md) — 定位批准范围和修改边界。
- [Coding Delegation State Record Worker Boundary](../layer-01-fundamental-concepts/delegation-state-record-worker-boundary_zh_cn.md) — 定位父级控制的授权边界。

# 验证报告检查点

[English](verification-reporting.md) | [简体中文](verification-reporting_zh_cn.md)

本检查点负责验证结果分类、未解决项目报告和阻塞影响报告。不定义独立 Session、检查内容、证据捕获、epoch 失效或修复。

## 动作

1. 记录通过、失败、不可用和假设的检查，以及剩余风险。
2. 明确报告每个未解决的验证项目及其阻塞影响。

## 通过条件

必需的结果分类、剩余风险、未解决项目和阻塞影响都已明确。

## 边界

本检查点不选择检查，不捕获最终状态指纹，不定义独立验证，不使 epoch 失效，不修复失败，不写文档，也不产生 Git 影响。

## 相关概念

- [Coding Execution Decision Gate](../layer-01-fundamental-concepts/execution-decision-gate_zh_cn.md) — 定位验收条件归属。
- [Coding Execution Control](../layer-01-fundamental-concepts/execution-control_zh_cn.md) — 定位报告范围和返回边界归属。
- [Coding Session 职责归属](../layer-01-fundamental-concepts/session-role-ownership_zh_cn.md) — 定位 Change Verification 职责。
- [Coding Delegation State Record Worker Boundary](../layer-01-fundamental-concepts/delegation-state-record-worker-boundary_zh_cn.md) — 定位证据访问边界。

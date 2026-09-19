# 验证检查点

[English](verification.md) | [简体中文](verification_zh_cn.md)

本检查点负责捕获当前最终状态证据、绑定验收条件、执行适用的整体和定向检查，并判断必需证据是否完整。不定义独立 Session、结果分类或后续 epoch 的失效规则。

## 动作

1. 记录当前最终状态的指纹或 epoch，以及验收条件。
2. 针对这个准确状态运行适用的最强整体检查和定向检查。

## 通过条件

每个必需验证项目都有当前证据，或证据缺口已明确并阻止完成。

## 边界

本检查点不定义独立验证 Session，不分类或报告结果，不使后续 epoch 失效，不修复失败，不写文档，不产生 Git 影响，也不能单独宣布整体验收完成。

## 相关概念

- [Coding Execution Decision Gate](../layer-01-fundamental-concepts/execution-decision-gate_zh_cn.md) — 定位验收条件和放行决策归属。
- [Coding Execution Control](../layer-01-fundamental-concepts/execution-control_zh_cn.md) — 定位已放行范围和返回边界归属。
- [Coding Session 职责归属](../layer-01-fundamental-concepts/session-role-ownership_zh_cn.md) — 定位 Change Verification 职责归属。
- [Coding Delegation State Record Worker Boundary](../layer-01-fundamental-concepts/delegation-worker-boundary_zh_cn.md) — 定位最终状态证据访问边界。

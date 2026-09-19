# 验证 Epoch 检查点

[English](verification-epoch.md) | [简体中文](verification-epoch_zh_cn.md)

本检查点负责最终状态 epoch 的失效：后续修改会使较早的验证结果过期，并要求重新验证。不定义检查内容、独立 Session、结果分类或修复。

## 动作

1. 将后续任何修改视为新的最终状态 epoch。
2. 不得把较早的验证结果作为新状态的证据；必须针对新 epoch 重新验证。

## 通过条件

当前最终状态 epoch 已明确，且所需的重新验证已排队或完成。

## 边界

本检查点不捕获指纹，不选择检查，不定义独立验证，不分类结果，不授权修复，不写文档，也不产生 Git 影响。

## 相关概念

- [Coding Execution Control](../layer-01-fundamental-concepts/execution-control_zh_cn.md) — 定位实质性状态边界归属。
- [Coding Delegation State Record Worker Boundary](../layer-01-fundamental-concepts/delegation-worker-boundary_zh_cn.md) — 定位最终状态证据访问。
- [Coding Child Reuse and Replacement](../layer-01-fundamental-concepts/delegation-child-reuse-replacement_zh_cn.md) — 定位修复 epoch 复用归属。
- [Coding Execution Decision Gate](../layer-01-fundamental-concepts/execution-decision-gate_zh_cn.md) — 定位依赖路线放行条件。

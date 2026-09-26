# 验证独立性检查点

[English](verification-independence.md) | [简体中文](verification-independence_zh_cn.md)

本检查点负责区分独立 Change Verification Session 和同一 Session 的逻辑验证。不定义检查内容、证据收集、结果分类或修复。

## 动作

1. 对实质性修改，在 Contract 要求时使用独立的 Change Verification Session。
2. 将同一 Session 中的检查标记为逻辑验证，不称为独立验证。

## 通过条件

独立性状态已明确分类：必需的独立 Session 已完成验证，或同 Session 检查标记为逻辑验证且独立验证不可用。后一种只是记录限制，**不**代表满足 Contract 所要求的独立验证；依赖影响继续阻塞。

## 边界

本检查点不选择整体或定向检查，不捕获指纹，不分类结果，不使 epoch 失效，不修复失败，也不产生 Git 影响。

## 相关概念

- [Coding Session 职责归属](../layer-01-fundamental-concepts/session-role-ownership_zh_cn.md) — 定位 Change Verification 职责归属。
- [Coding Session Context Firewall](../layer-01-fundamental-concepts/session-context-firewall_zh_cn.md) — 定位 Session 状态进入边界。
- [Coding Delegation State Record Worker Boundary](../layer-01-fundamental-concepts/delegation-worker-boundary_zh_cn.md) — 定位 verifier 证据访问边界。
- [Coding Execution Decision Gate](../layer-01-fundamental-concepts/execution-decision-gate_zh_cn.md) — 定位依赖 Contract 的验证条件。

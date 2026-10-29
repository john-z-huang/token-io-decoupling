# 修复处置

[English](repair-disposition.md) | [简体中文](repair-disposition_zh_cn.md)

本检查点负责失败或实质性决策变化后的路线级恢复和重新验证路由。


## 触发与输入

当前 Verification 失败或决策发生重大变化后，使用本检查点路由恢复流程。应用[Repair](../layer-02-workflow-concepts/verification-and-repair/repair_zh_cn.md)、[Repair Scope Gate](../layer-02-workflow-concepts/verification-and-repair/repair-scope-gate_zh_cn.md)、[Repair Execution](../layer-02-workflow-concepts/verification-and-repair/repair-execution_zh_cn.md)和[Repair Verification Handoff](../layer-02-workflow-concepts/verification-and-repair/repair-verification-handoff_zh_cn.md)。

## 决策与结果

1. 必须提供具体失败证据、受影响路径和最小修复候选。没有具体失败的语义变更不能算作 Repair；应作为重大决策变化路由。
2. 用当前 Contract 和 Decision 应用 Repair 范围门禁。只释放获授权的窄范围修复及其定向检查。
3. 记录修复交接、新指纹和受影响 epoch；将当前证据交给 Verification，并在依赖工作前重跑所有变更 epoch 所需检查。
4. 重大决策变化返回 S01/S06 或 M01/M07 进行路线调度。无具体失败时，返回 Repair `Not applicable` 及证据依据。

## 失败边界

诊断、授权、有界范围、handoff 证据或变更 epoch 后重新验证缺失时，阻塞依赖路线。修复意图不构成授权，也不得复用过期通过证据。

## 相关概念

- [Repair Scope Gate](../layer-02-workflow-concepts/verification-and-repair/repair-scope-gate_zh_cn.md)

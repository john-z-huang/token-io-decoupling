# 执行模式检查点

[English](mode.md) | [简体中文](mode_zh_cn.md)

## 动作

1. 加载[状态记录 reference](../layer-01-fundamental-concepts/delegation-state-record_zh_cn.md)、[模式确认 reference](../layer-01-fundamental-concepts/delegation-mode-confirmation_zh_cn.md)、[模式/数量门禁 reference](../layer-01-fundamental-concepts/delegation-mode-count-gate_zh_cn.md)和[模式重新进入 reference](../layer-01-fundamental-concepts/delegation-mode-reentry_zh_cn.md)。如果已发布模式分配了子代理，还要加载[子代理创建](../layer-01-fundamental-concepts/delegation-child-creation_zh_cn.md)、[子代理职责分配](../layer-01-fundamental-concepts/delegation-child-role-allocation_zh_cn.md)、[子代理派发](../layer-01-fundamental-concepts/delegation-child-dispatch_zh_cn.md)、[子代理复用/替换](../layer-01-fundamental-concepts/delegation-child-reuse-replacement_zh_cn.md)和[子代理生命周期](../layer-01-fundamental-concepts/delegation-child-lifecycle_zh_cn.md)。
2. 路线选择前读取父级控制的任务记录，并验证当前 `gate_status`、`mode`、`child_count`、分配、生命周期和不可用能力。如果记录尚未放行，则停留在本检查点，不得继续。
3. 新的根用户指令改变委派要求时，重新应用模式/数量门禁并替换任务记录后再继续。本检查点负责组合和验证这些 reference；不自行决定模式、数量、创建、分配、复用、例外或生命周期。

## 通过条件

任务控制记录已经包含一条已发布的有效模式结果和所需的委派状态：单代理为 `child_count: 0`，多代理为已锁定的正整数数量、有效分配和生命周期；且所选路线的能力和禁止事项得到满足。

## 边界

本检查点负责组合并验证状态记录、模式/数量和按条件加载的子代理派发/生命周期 reference，不独立决定模式、拓扑、创建、分配、复用、例外、生命周期或数量。

## 相关概念

- [Coding Delegation Mode Confirmation](../layer-01-fundamental-concepts/delegation-mode-confirmation_zh_cn.md) — 定位根模式确认归属。
- [Coding Delegation Count Gate](../layer-01-fundamental-concepts/delegation-mode-count-gate_zh_cn.md) — 定位子 Agent 数量门禁归属。
- [Coding Delegation Re-entry](../layer-01-fundamental-concepts/delegation-mode-reentry_zh_cn.md) — 定位模式/数量重新进入归属。
- [Coding Delegation State Record](../layer-01-fundamental-concepts/delegation-state-record_zh_cn.md) — 定位任务控制记录归属。
- [Coding Delegation State Record Worker Boundary](../layer-01-fundamental-concepts/delegation-worker-boundary_zh_cn.md) — 定位已放行 Worker 记录访问边界。

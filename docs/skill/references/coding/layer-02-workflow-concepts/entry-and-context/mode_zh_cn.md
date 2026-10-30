# 执行模式检查点

[English](mode.md) | [简体中文](mode_zh_cn.md)

## 动作

1. 加载[状态记录](../../layer-01-fundamental-concepts/delegation/delegation-state-record_zh_cn.md)、[模式确认](../../layer-01-fundamental-concepts/delegation/delegation-mode-confirmation_zh_cn.md)、[数量门禁](../../layer-01-fundamental-concepts/delegation/delegation-mode-count-gate_zh_cn.md)和[重新进入](../../layer-01-fundamental-concepts/delegation/delegation-mode-reentry_zh_cn.md) owner。不得在实际执行步骤前预先加载子代理创建、派发、生命周期或复用的完整策略。
2. 核对父级记录：Single-Agent 使用 `child_count: 0`、`allocations: []`；Multi-Agent 数量已锁定，具有恰好 `child_count` 个初始未绑定、未分配、待放行的预留名额。如果 `mode_source: default`，核实模式为 Multi-Agent、`child_count: 1` 且恰好有一个预留名额。如果 `mode_source: timeout-default`，仅为兼容旧记录而接受，并核实 Single-Agent、`child_count: 0` 和 `allocations: []`；新会话不再使用此来源。本门禁放行**不**等于具体 Interaction Slice 已放行，不初始化 store，也不授权创建子代理。只有路线后续已通过 Session 身份、职责和 Context Firewall 核验后，才可首次持久化 Enhanced Root 状态。
3. 后续指令沿用已锁定 mode/count，只更新任务专属证据，不重新打开模式/数量门禁。记录或必需能力证据缺失时阻塞依赖路线。职责分配和子代理操作在路线指定的执行阶段核验。

4. 核验已记录获授权的模式/数量及本门禁所需证据。建议输出不能改变已锁定模式/数量或重开本门禁；建议政策遵循[Decisions 建议](../../layer-01-fundamental-concepts/execution-planning/decisions-advisory_zh_cn.md)。

## 通过条件

父级记录具有唯一有效的已放行模式、固定数量及适用时有效的预留 allocation 结构，并满足路线入口能力；不得推断已有具体子代理或 Slice 获准。

## 边界

本检查点负责组合并验证状态记录、模式/数量和按条件加载的子代理派发/生命周期 reference，不独立决定模式、拓扑、创建、分配、复用、例外、生命周期或数量。Mode 通过从不初始化或迁移数据库；store 选择和首次写入时机由路线及[增强状态存储](../../layer-01-fundamental-concepts/enhanced-native-state/enhanced-state-store_zh_cn.md) owner 负责。

## 相关概念

- [Coding Delegation Mode Confirmation](../../layer-01-fundamental-concepts/delegation/delegation-mode-confirmation_zh_cn.md) — 定位根模式确认归属。
- [Coding Delegation Count Gate](../../layer-01-fundamental-concepts/delegation/delegation-mode-count-gate_zh_cn.md) — 定位子 Agent 数量门禁归属。
- [Coding Delegation Re-entry](../../layer-01-fundamental-concepts/delegation/delegation-mode-reentry_zh_cn.md) — 定位模式/数量重新进入归属。
- [Coding Delegation State Record](../../layer-01-fundamental-concepts/delegation/delegation-state-record_zh_cn.md) — 定位任务控制记录归属。
- [Coding Delegation State Record Worker Boundary](../../layer-01-fundamental-concepts/delegation/delegation-worker-boundary_zh_cn.md) — 定位已放行 Worker 记录访问边界。

# Coding 委派状态记录

[English](delegation-state-record.md) | [简体中文](delegation-state-record_zh_cn.md)

本文档负责 Coding 委派使用的任务控制记录，定义记录的规范位置、ownership、结构和字段约束。不决定模式，不定义 Worker 读写边界，不创建子 Agent，不分配职责，也不定义生命周期转换。

## Ownership

根父级负责当前根用户指令的记录。记录是任务状态，不通过编辑 policy 文件保存；父级控制的任务面板或等价运行时记录是规范位置。

## 记录结构

路线放行前记录：

```text
owner: <根父级身份>
gate_status: awaiting-mode | awaiting-count | released | blocked
mode: Single-Agent Coding | Multi-Agent Coding
child_count: 0 | <正整数>
allocations: [{agent, role, interaction_slice, scope, mutations, return_conditions, lifecycle}]
lifecycle: pending | running | completed | interrupted
unavailable_capabilities: [<能力名称>]
```

单代理的 `child_count` 为 0，多代理为已锁定的正整数。子 Agent 推进时，allocation 的 lifecycle 可以与顶层记录不同。

## 相关概念

- [Coding Delegation State Record Worker Boundary](delegation-worker-boundary_zh_cn.md) — 定位 Worker 快照和记录访问边界。
- [Coding Delegation Mode Confirmation](delegation-mode-confirmation_zh_cn.md) — 定位根模式确认归属。
- [Coding Delegation Count Gate](delegation-mode-count-gate_zh_cn.md) — 定位子 Agent 数量门禁归属。
- [Coding Delegation Re-entry](delegation-mode-reentry_zh_cn.md) — 定位模式/数量重新进入归属。
- [Coding Execution Control](execution-control_zh_cn.md) — 定位 Interaction Slice 字段归属。
- [Coding Child Lifecycle](delegation-child-lifecycle_zh_cn.md) — 定位子 Agent 生命周期字段归属。

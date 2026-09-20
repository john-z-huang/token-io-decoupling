# Coding 委派状态记录

[English](delegation-state-record.md) | [简体中文](delegation-state-record_zh_cn.md)

本文档负责 Coding 委派使用的任务控制记录，定义记录的规范位置、ownership、结构、字段约束和分阶段字段存在语义。不决定模式，不定义 Worker 读写边界，不创建子 Agent，不分配职责，也不定义生命周期转换。

## Ownership

根父级负责当前根用户指令的记录。记录是任务状态，不通过编辑 policy 文件保存；父级控制的任务面板或等价运行时记录是规范位置。

## 记录结构

路线放行前初始化并维护：

```text
owner: <根父级身份>
gate_status: awaiting-mode | awaiting-count | released | blocked
mode: unset | Single-Agent Coding | Multi-Agent Coding
child_count: unset | 0 | <locked positive integer>
allocations: [{agent, role, interaction_slice, scope, mutations, return_conditions, lifecycle, write_content_memo}]
lifecycle: pending | running | completed | interrupted
unavailable_capabilities: [<能力名称>]
block_reason: <仅在 gate_status 为 blocked 时必需>
```

分阶段字段约定如下：

| `gate_status` | `mode` | `child_count` | `allocations` | `lifecycle` | 额外要求 |
| --- | --- | --- | --- | --- | --- |
| `awaiting-mode` | Unset | Unset | 必须为 `[]` | 必须为 `pending` | 在提出模式确认问题前初始化此状态。 |
| `awaiting-count` | 必须为 `Multi-Agent Coding` | Unset，尚未锁定 | 必须为 `[]` | 必须为 `pending` | 仅在明确确认多代理模式后进入。 |
| `released` — Single-Agent | 必须为 `Single-Agent Coding` | 必须为 `0` | 必须为 `[]` | 必需；记录根任务状态 | 只有满足路线放行条件后才能释放路线。 |
| `released` — Multi-Agent | 必须为 `Multi-Agent Coding` | 必须为已锁定的正整数 | 必须恰好包含 `child_count` 个条目 | 顶层必需；每个 allocation 必须有自己的 lifecycle | 每个 allocation 必须显式包含 `write_content_memo: true` 或 `false`。 |
| `blocked` | 保留已确认值；否则为 unset | 保留已确认值；否则为 unset | 保留当前值 | 保留当前值 | 必须有 `unavailable_capabilities` 和 `block_reason`。此状态不是 `released`。 |

对于 `awaiting-mode`，`mode` 和 `child_count` 缺失或显式为 `unset`；其余必需字段按上表存在。对于 `awaiting-count`，`mode` 必须存在，而 `child_count` 在数量锁定前保持缺失或显式为 `unset`。每个 `released` 记录中标为必需的字段都必须存在；`write_content_memo` 是每个 Worker released slice 的显式派发字段，不得由 Worker 推断默认值。子 Agent 推进时，allocation 的 lifecycle 可以与顶层记录不同。只有明确确认多代理后，记录才能从 `awaiting-mode` 转为 `awaiting-count`；单代理确认后，先设置 `child_count: 0`，再在路线放行条件满足后释放。阻塞会保留已确认状态且不会释放路线；后续门禁重新进入遵循其所属概念。

## 相关概念

- [Coding Delegation State Record Worker Boundary](delegation-worker-boundary_zh_cn.md) — 定位 Worker 快照和记录访问边界。
- [Coding Delegation Mode Confirmation](delegation-mode-confirmation_zh_cn.md) — 定位根模式确认归属。
- [Coding Delegation Count Gate](delegation-mode-count-gate_zh_cn.md) — 定位子 Agent 数量门禁归属。
- [Coding Delegation Re-entry](delegation-mode-reentry_zh_cn.md) — 定位模式/数量重新进入归属。
- [Coding Execution Control](execution-control_zh_cn.md) — 定位 Interaction Slice 字段归属。
- [Coding Child Lifecycle](delegation-child-lifecycle_zh_cn.md) — 定位子 Agent 生命周期字段归属。

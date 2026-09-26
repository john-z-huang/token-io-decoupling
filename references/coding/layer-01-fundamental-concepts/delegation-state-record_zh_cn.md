# Coding 委派状态记录

[English](delegation-state-record.md) | [简体中文](delegation-state-record_zh_cn.md)

本文档负责 Coding 委派使用的任务控制记录，定义记录的规范位置、ownership、结构、字段约束和分阶段字段存在语义。不决定模式，不定义 Worker 读写边界，不创建子 Agent，不分配职责，也不定义生命周期转换。

## 通用规范

### Ownership

根父级负责一份会话级模式/数量选择记录，并在同一记录中更新任务专属切片和生命周期。记录是任务状态，不通过编辑 policy 文件保存。存在父级控制的任务面板时使用该面板；否则在父级会话中维护可在每次路线放行前读回的显式结构化记录。不得将短暂的子代理状态界面当作规范记录。

### 记录结构

路线放行前初始化并维护：

```text
owner: <根父级身份>
gate_status: awaiting-mode | awaiting-count | released | blocked
mode_source: unset | explicit | timeout-default
mode: unset | Single-Agent Coding | Multi-Agent Coding
child_count: unset | 0 | <locked positive integer>
allocations: [{agent: unbound | <created-agent-identity>, role, interaction_slice, scope, mutations, return_conditions, lifecycle, write_content_memo}]
lifecycle: pending | running | completed | interrupted
unavailable_capabilities: [<能力名称>]
block_reason: <仅在 gate_status 为 blocked 时必需>
```

分阶段字段约定如下：

| `gate_status` | `mode` | `child_count` | `allocations` | `lifecycle` | 额外要求 |
| --- | --- | --- | --- | --- | --- |
| `awaiting-mode` | Unset | Unset | 必须为 `[]` | 必须为 `pending` | 首轮没有明确模式时，在提问前初始化此状态。 |
| `awaiting-count` | 必须为 `Multi-Agent Coding` | Unset，尚未锁定 | 必须为 `[]` | 必须为 `pending` | 仅用于用户明确选择多代理但给出无效子代理数量的准备状态；省略数量时不得提出第二个数量问题。 |
| `released` — Single-Agent | 必须为 `Single-Agent Coding` | 必须为 `0` | 必须为 `[]` | 必需；记录根任务状态 | 只有满足路线放行条件后才能释放路线。 |
| `released` — Multi-Agent | 必须为 `Multi-Agent Coding` | 必须为已锁定的正整数 | 必须恰好包含 `child_count` 个已锁定的计划 allocation；创建前每个 allocation 可以是 `agent: unbound` 且 `lifecycle: pending` | 顶层必需；每个 allocation 必须有自己的 lifecycle | 每个 allocation 必须显式包含 `write_content_memo: true` 或 `false`。此状态放行下一步创建子 Agent；不表示子 Agent 已创建或已派发。 |
| `blocked` | 保留已确认值；否则为 unset | 保留已确认值；否则为 unset | 保留当前值 | 保留当前值 | 必须有 `unavailable_capabilities` 和 `block_reason`。此状态不是 `released`。 |

对于 `awaiting-mode`，`mode` 和 `child_count` 缺失或显式为 `unset`；其余必需字段按上表存在。对于 `awaiting-count`，`mode` 必须存在，而 `child_count` 在数量锁定前保持缺失或显式为 `unset`。每个 `released` 记录中标为必需的字段都必须存在；`write_content_memo` 是每个 Worker released slice 的显式派发字段，不得由 Worker 推断默认值。released Multi-Agent 记录必须恰好包含已锁定数量的计划 allocation；创建子 Agent 前，allocation 可以使用 `agent: unbound` 和 `lifecycle: pending`。released 状态表示路线放行门禁已通过，下一步可以创建子 Agent；不表示子 Agent 已创建或已派发。创建成功后，由 child-creation owner 回写已创建的 agent identity 和实际 lifecycle。子 Agent 推进时，allocation 的 lifecycle 可以与顶层记录不同。明确选择或 15 秒默认的多代理通常直接进入数量锁定；`awaiting-count` 仅用于明确提供的数量无效。单代理选择后先设置 `child_count: 0`，再在路线放行条件满足后释放，并保持 `allocations: []`。选择后 `mode_source` 必须记录 `explicit` 或 `timeout-default`，并在本次会话保持不变。阻塞会保留已确认状态且不会释放路线；后续门禁重新进入遵循其所属概念。

## Codex CLI / ChatGPT Desktop 特别优化指令

目前没有针对该厂商的特别优化指令；遵循上述通用规范。

## Claude Code CLI / Claude Desktop 特别优化指令

Claude Code 没有与 Codex 父级任务面板相同的持久能力。在父级会话中维护结构化模式、数量和切片记录，每次路线放行前读回。`/tasks` 只是短暂的子代理状态界面，不是规范记录。

## 相关概念

- [Coding Delegation State Record Worker Boundary](delegation-worker-boundary_zh_cn.md) — 定位 Worker 快照和记录访问边界。
- [Coding Delegation Mode Confirmation](delegation-mode-confirmation_zh_cn.md) — 定位根模式确认归属。
- [Coding Delegation Count Gate](delegation-mode-count-gate_zh_cn.md) — 定位子 Agent 数量门禁归属。
- [Coding Delegation Re-entry](delegation-mode-reentry_zh_cn.md) — 定位模式/数量重新进入归属。
- [Coding Execution Control](execution-control_zh_cn.md) — 定位 Interaction Slice 字段归属。
- [Coding Child Lifecycle](delegation-child-lifecycle_zh_cn.md) — 定位子 Agent 生命周期字段归属。

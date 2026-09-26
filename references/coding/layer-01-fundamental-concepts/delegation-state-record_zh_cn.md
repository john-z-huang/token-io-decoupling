# Coding 委派状态记录

[English](delegation-state-record.md) | [简体中文](delegation-state-record_zh_cn.md)

本文档负责 Coding 委派使用的任务控制记录，定义记录的规范位置、ownership、结构、字段约束和分阶段字段存在语义。不决定模式，不定义 Worker 读写边界，不创建子 Agent，不分配职责，也不定义生命周期转换。

## 通用规范

### Ownership

根父级负责一份会话级模式/数量选择记录，并在同一记录中更新任务专属切片和生命周期。记录是任务状态，不通过编辑 policy 文件保存。存在父级控制的任务面板时使用该面板；否则在父级会话中维护可在每次路线放行前读回的显式结构化记录。不得将短暂的子代理状态界面当作规范记录。

### 记录结构

路线放行前维护以下规范状态记录：

```text
owner: <根父级身份>
gate_status: awaiting-mode | awaiting-count | released | blocked
mode_source: unset | explicit | timeout-default
mode: unset | Single-Agent Coding | Multi-Agent Coding
child_count: unset | 0 | <已锁定正整数>
allocations: [{agent: unbound | <已创建代理身份>, role: unassigned | <职责>,
               slice_status: pending | released, interaction_slice, scope, mutations,
               return_conditions, lifecycle, write_content_memo}]
lifecycle: pending | running | completed | interrupted
unavailable_capabilities: [<能力名称>]
block_reason: <仅 blocked 时必需>
```

| `gate_status` | 模式与数量 | Allocation 和 lifecycle | 其他要求 |
| --- | --- | --- | --- |
| `awaiting-mode` | 未设置 | `[]`；顶层 `pending` | 首轮模式问题尚未答复时先初始化。 |
| `awaiting-count` | Multi-Agent；数量未设置 | `[]`；顶层 `pending` | 仅明确给出无效数量时进入；省略数量默认 1。 |
| `released` — Single-Agent | Single-Agent；数量 `0` | `[]`；顶层 lifecycle 必需 | 放行单代理路线，不授予独立 Session。 |
| `released` — Multi-Agent | Multi-Agent；已锁定正整数 | 恰好 `child_count` 个预留 allocation；初始 `agent: unbound`、`role: unassigned`、`slice_status: pending`、`lifecycle: pending` | 只放行路线与数量预算，**不**放行具体子代理或 Interaction Slice。 |
| `blocked` | 保留已确认值 | 保留现有 allocation/lifecycle | `unavailable_capabilities` 与 `block_reason` 必需；不得进入依赖路线。 |

Role Allocation 阶段分配 allocation 的职责。具体 `slice_status: released` 必须具备已分配 `role`、`interaction_slice`、`scope`、`mutations`、`return_conditions` 和显式布尔 `write_content_memo`；pending Slice 可以暂不设置这些字段。序列化每个已放行 Worker bundle 前，必须显式写入 `write_content_memo: true` 或 `false`，Worker 不得推断默认值。Child Creation 只能在相应职责和 Slice 已放行后绑定 `agent` 与 lifecycle。后续 Slice 可在**同一个**已创建子代理上准备，不创建或回收名额。

`mode_source` 记录明确选择或 15 秒默认，并在整次会话固定。各 allocation 的 lifecycle 可不同于顶层任务的 lifecycle。阻塞保留已确认值；后续指令遵循 Re-entry owner，不改变已锁定的 mode/count。

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

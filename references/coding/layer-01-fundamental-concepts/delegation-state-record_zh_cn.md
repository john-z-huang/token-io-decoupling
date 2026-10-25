# Coding 委派状态记录

[English](delegation-state-record.md) | [简体中文](delegation-state-record_zh_cn.md)

本文档负责 Coding 委派使用的任务控制记录，定义记录的规范位置、ownership、结构、字段约束和分阶段字段存在语义。不决定模式，不定义 Worker 读写边界，不创建子 Agent，不分配职责，也不定义生命周期转换。Session 审计配置由[会话审计可见性](session-audit-visibility_zh_cn.md)负责。

## 通用规范

### Ownership

根父级负责一份会话级模式/数量选择记录，并在同一记录中更新任务专属切片和生命周期。记录是任务状态，不通过编辑 policy 文件保存。Native 运行时，parent context 中的结构化记录是 canonical，并须在每次路线放行前读回；短暂子代理状态不是 canonical。Enhanced 运行时，获授权的 Root store 初始化且身份和 Schema 核验通过后，Root SQLite 记录才是 Enhanced 持久状态的 canonical。此后 parent context 只保留可读快照或引用，不能成为竞争的可写权威。从 Native 到 Enhanced 的对账遵循[Native 对账](native-reconciliation_zh_cn.md)；回切 Native 遵循[Native 权威转移](native-authority-transfer_zh_cn.md)。两种转换都不改变本记录的字段归属，也不允许覆盖有效规范记录。

### 记录结构

路线放行前维护以下规范状态记录：

```text
owner: <根父级身份>
run_id: unset | <本次 Multi-Agent 委派运行的稳定标识>
gate_status: awaiting-mode | awaiting-count | released | blocked
mode_source: unset | explicit | default | timeout-default（仅兼容旧记录）
mode: unset | Single-Agent Coding | Multi-Agent Coding
child_count: unset | 0 | <已锁定正整数>
allocations: [{allocation_id: <稳定的子代理 allocation 标识>,
               agent: unbound | <已创建代理身份>, role: unassigned | <职责>,
               slice_status: pending | released, interaction_slice, scope, mutations,
               return_conditions, lifecycle, write_content_memo}]
session_audit: {audit_mode, root_reasoning_cadence, worker_reasoning_cadence,
                source: {audit_mode: explicit | default, root_reasoning_cadence: explicit | default,
                        worker_reasoning_cadence: explicit | default},
                worker_log_visibility: available | unverified | unavailable | Not applicable,
                worker_log_evidence, audit_config_prompt: {status: unasked | pending | answered |
                timed_out | unavailable | reused, prompted_at, deadline_at, response_at,
                resolution: startup_explicit | prior_record | question_reply |
                question_reply_after_timeout | timeout_default | awaiting_input | unavailable},
                revision: session-audit/v2}
lifecycle: pending | running | completed | interrupted
unavailable_capabilities: [<能力名称>]
block_reason: <仅 blocked 时必需>
```

`audit_config_prompt` 各字段含义如下；此 schema 不定义状态转换：

| 字段 | 合法值/表示 | 含义 |
| --- | --- | --- |
| `status` | `unasked`、`pending`、`answered`、`timed_out`、`unavailable`、`reused` | 已记录的配置问题状态。 |
| `prompted_at`、`deadline_at`、`response_at` | 实际观察到的 ISO-8601 UTC 时间戳或 `null` | 实际提问时间、记录的截止时间、最近观察到的用户答复时间。 |
| `resolution` | `startup_explicit`、`prior_record`、`question_reply`、`question_reply_after_timeout`、`timeout_default`、`awaiting_input`、`unavailable` | 生效配置的已记录来源或结果。 |

所选工作流路线负责判定和状态更新；该记录作为任务状态保留。

| `gate_status` | 模式与数量 | Allocation 和 lifecycle | 其他要求 |
| --- | --- | --- | --- |
| `awaiting-mode` | 未设置 | `[]`；顶层 `pending` | 记录首次明确选择或默认值前先初始化。 |
| `awaiting-count` | Multi-Agent；数量未设置 | `[]`；顶层 `pending` | 仅明确给出无效数量时进入；省略数量时默认 1。 |
| `released` — Single-Agent | Single-Agent；数量 `0` | `[]`；顶层 lifecycle 必需 | 放行单代理路线，不授予独立 Session。`timeout-default` 仅作为旧记录来源接受并读回。 |
| `released` — Multi-Agent | Multi-Agent；已锁定正整数 | 恰好 `child_count` 个预留 allocation；`run_id` 已设置；每个 allocation 有唯一且稳定的 `allocation_id`，并初始为 `agent: unbound`、`role: unassigned`、`slice_status: pending`、`lifecycle: pending` | 只放行路线与数量预算，**不**放行具体子代理或 Interaction Slice。 |
| `blocked` | 保留已确认值 | 保留现有 allocation/lifecycle | `unavailable_capabilities` 与 `block_reason` 必需；不得进入依赖路线。 |

Role Allocation 阶段分配 allocation 的职责。具体 `slice_status: released` 必须具备已分配 `role`、`interaction_slice`、`scope`、`mutations`、`return_conditions` 和显式布尔 `write_content_memo`；pending Slice 可以暂不设置这些字段。序列化每个已放行 Worker bundle 前，必须显式写入 `write_content_memo: true` 或 `false`，Worker 不得推断默认值。Child Creation 只能在相应职责和 Slice 已放行后绑定 `agent` 与 lifecycle。后续 Slice 可在**同一个**已创建子代理上准备，不创建或回收名额。

`mode_source` 记录明确选择或默认值，并在整次会话固定。新会话不再写入 `timeout-default`；仅为读回按旧规则创建的会话而接受该来源。旧 `timeout-default` 记录必须保持 Single-Agent、`child_count: 0` 和 `allocations: []`；读回时不得重新解释或迁移。各 allocation 的 lifecycle 可不同于顶层任务的 lifecycle。阻塞保留已确认值；后续指令遵循 Re-entry owner，不改变已锁定的 mode/count。

当 `mode_source: default` 时，已放行记录必须是 Multi-Agent、`child_count: 1` 且恰好有一个预留 allocation；此预留不会初始化子代理。实际创建仍受输出类型和切片门禁约束。

`session_audit` 遵循[会话审计可见性](session-audit-visibility_zh_cn.md)定义的字段。仅根父级写入。`audit_config_prompt.status` 表示已记录的提问状态；时间戳是实际观察到的 UTC 时间或 `null`，`resolution` 标明记录的来源/结果。所选路线负责收集和更新这些字段。日志证据仅在首次需要 Worker，或出现新的实际能力/访问证据或失败时更新，不逐消息更新。此状态不得改变 `mode`、`child_count`、授权、allocation 或 Slice 放行。不得将完整 Root 审计记录复制到策略文件或 Worker 可控状态中。真实 `pending` 状态在解决前保持 pending；缺少持久化或审计更新失败不能证明用户已答复、已选默认值或已完成。

## Codex CLI / ChatGPT Desktop 特别优化指令

Codex 中，`AGENTS.md` 是指令来源，不是可写的实时 mode/count 记录；仅在已配置且受支持时，`SessionStart`、`SubagentStart` 等 Hook 才可补充获准上下文。路线放行前须读回父级规范记录、已分配身份及 epoch；运行时状态和 Hook 事件都不是规范记录。[OpenAI：Hooks](https://learn.chatgpt.com/docs/hooks)、[OpenAI：AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md)。

Codex 的 `/agent` 与 `/status` 只有暴露给当前 Agent Session 时才可提供运行时观察；`AGENTS.md`、可选本地 memories 和 `/compact` 分别用于项目指令、回忆与会话压缩，都不是实时 mode/count/allocation/epoch 权威记录。Session 恢复、compact 或通过工具转移线程后，放行新路线前必须读回父级保留的状态记录。可信且实际启用的 `SessionStart` Hook 在 `compact` 时可以提供获准上下文，但不能重新锁定数量。[OpenAI：子代理](https://learn.chatgpt.com/docs/agent-configuration/subagents)、[OpenAI：AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md)、[OpenAI：memories](https://learn.chatgpt.com/docs/customization/memories)、[OpenAI：Hooks](https://learn.chatgpt.com/docs/hooks)。

## Claude Code CLI / Claude Desktop 特别优化指令

在父级会话中维护结构化模式、数量和切片记录，每次路线放行前读回。`/tasks` 输出只是短暂的子代理状态信号，不是规范记录。

Claude Code 的 `/tasks` 显示当前／后台子代理任务状态，`/context` 查看已加载的指令／memory 文件。它们都不是规范的 mode/count/allocation 记录；`CLAUDE.md` 与 auto memory 是**指令或学习上下文**，不能作为重写实时任务记录的位置。父会话在 compaction 或重新启动后恢复时，必须先读回保留的任务记录，核验锁定门禁与当前 epoch，再放行新 Slice。已配置的 `SessionStart` Hook 可以提供获准的初始上下文，但仅凭 Hook 输出不得创建 allocation 或覆盖已锁定数量。[Anthropic：memory](https://code.claude.com/docs/en/memory)、[Anthropic：Hooks](https://code.claude.com/docs/en/hooks)、[Anthropic：子代理状态](https://code.claude.com/docs/en/sub-agents)。

## 相关概念

- [Coding Delegation State Record Worker Boundary](delegation-worker-boundary_zh_cn.md) — 定位 Worker 快照和记录访问边界。
- [Coding Delegation Mode Confirmation](delegation-mode-confirmation_zh_cn.md) — 定位根模式确认归属。
- [Coding Delegation Count Gate](delegation-mode-count-gate_zh_cn.md) — 定位子 Agent 数量门禁归属。
- [Coding Delegation Re-entry](delegation-mode-reentry_zh_cn.md) — 定位模式/数量重新进入归属。
- [Coding Execution Control](execution-control_zh_cn.md) — 定位 Interaction Slice 字段归属。
- [Coding Child Lifecycle](delegation-child-lifecycle_zh_cn.md) — 定位子 Agent 生命周期字段归属。
- [Coding Session 审计可见性](session-audit-visibility_zh_cn.md) — 定位会话审计配置归属。
- [Enhanced 状态存储](enhanced-state-store_zh_cn.md) — 定位 Native 与 Enhanced 持久记录的权威边界。
- [Native 对账](native-reconciliation_zh_cn.md) — 定位显式 Native-to-Enhanced Root 对账。
- [Native 权威转移](native-authority-transfer_zh_cn.md) — 定位显式 Enhanced-to-Native Root 权威转移。

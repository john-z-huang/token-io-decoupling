# Session 审计解决

[English](session-audit-resolution.md) | [简体中文](session-audit-resolution_zh_cn.md)

本检查点负责路线级审计配置解决、提问与答复处理、迁移、超时和规范记录回读。

## 触发与输入

已获得经过核实的规范 Root 记录后，消费该记录及当前 Session 审计事实。应用[Session Audit Visibility](../layer-01-fundamental-concepts/session-runtime/session-audit-visibility_zh_cn.md)了解审计字段值和显示语义，并应用[委派状态记录](../layer-01-fundamental-concepts/delegation/delegation-state-record_zh_cn.md)了解审计记录支持的状态和 resolution 值。

## 决策与结果

通过复用有效的显式/已完成设置、按原 deadline 恢复待处理提示、仅在未询问时提出本检查点拥有的固定原文问题，或仅澄清无效/含糊字段，解决规范 Root 审计记录。本检查点负责固定问题和解决流程；Session Audit Visibility 负责字段值、默认值和显示语义。记录实际提示时间、精确 60 秒 deadline、响应时间、状态、解决方式、变更字段、来源和 revision。有效回复只更新选定 Root 字段；保留有效 Worker 值，缺失时按规定默认 `full`。只有可靠确认无人回复且实际至少 60 秒后，才将 Root 默认设为 `balanced/milestone_only`，保留有效 Worker cadence，缺失时补为 `full/default`，然后回读规范记录。已观察到的回复不得算作超时。

## 解决流程

本检查点定义并负责对前序路线动作已核实的规范记录执行固定提问和解决流程。[Session Audit Visibility](../layer-01-fundamental-concepts/session-runtime/session-audit-visibility_zh_cn.md)仍负责字段值、默认值和显示语义。

   - **审计记录与迁移。** 读取记录。对于已知 v1，逐字段保留有效值/来源；任一 Root 字段为 `explicit` 时复用该组合，只将缺失 Root 字段补为 v2 默认 `balanced`/`milestone_only`；保留有效 Worker cadence，缺失时补 `full/default`。若 Root 两字段均为 `default` 且没有已完成提问，则询问一次，并在 pending 期间保留 v1 原值。已知映射解决后（可复用显式字段组合时立即解决；默认组合则在有效答复/真实超时后解决），应用结果并设置 `revision: session-audit/v2`。非法字段、同字段冲突或未知修订版本需定向澄清；不猜测或重置无关值。
   - **复用与恢复。** 复用有效显式启动值或已完成记录；新的显式启动记录 `status: reused` 和 resolution `startup_explicit`，复用已完成记录则记录 `status: reused` 和 resolution `prior_record`。保留提示、计时和答复证据。若为 `pending`，不得重发模板：`response_at: null` 时按原截止时间恢复等待；已观察到答复时从该答复继续定向更正，绝不自动超时。
   - **首次提问。** 仅对需要提问的 `unasked` 记录询问一次，使用以下固定模板且不改写：

     > 当前 Coding 会话的 Root 审计偏好？选择一项：**balanced/milestone_only**（推荐默认）、**economy/off**（最低可见性）或 **full/full**。也可用 `audit_mode=<economy|balanced|full>` 和/或 `root_reasoning_cadence=<off|milestone_only|full>` 自定义这些字段。Worker cadence 保留已有有效值；缺失时默认为 `full`。若 60 秒内未回复，Root 默认 **balanced/milestone_only**；Worker cadence 保留已有有效值，缺失时才默认为 **full**。这只影响显示和可选摘要，不授予任何授权。

     若有实际可用且获授权的异步输入能力则使用；否则仅在运行时允许时使用普通可见文本。记录实际观察到的 UTC 提问时间和准确的 60 秒截止时间，将状态设为 `pending`、`response_at: null`、resolution `awaiting_input`。使用可被用户输入中断、每次不超过 60 秒的间隔等待。若提问、计时或可中断有界等待不可用，记录 `unavailable`，不得猜测，并阻塞本门；独立工作可继续。
   - **答复与澄清。** 有效答复仅更新点名 Root 字段并将来源设为 `explicit`，状态设为 `answered`，resolution 设为 `question_reply`；有效迟到答复使用 `question_reply_after_timeout`，保留超时证据，只影响后续消息，不重放。预设同时设置 Root 两字段；键值自由文本仅更新点名字段，其他缺失 Root 字段默认为 `balanced`/`milestone_only`。`response_at` 记录实际观察时间。无效/歧义答复保持 `pending`；沿原问题/截止时间只澄清受影响字段，更新 `response_at`；观察到任何答复后不得自动超时。
   - **超时与读回核对。** 仅当从未观察到任何答复且可信时钟确认实际经过至少 60 秒时，将状态设为 `timed_out`、resolution 设为 `timeout_default`。此时 Root 使用 `balanced`/`milestone_only` 且来源为 `default`；保留有效 Worker cadence，缺失时补为 `full/default`。读回值、来源、提问字段和修订版本。此偏好不改变 Mode/count 或授权。

## 多代理审计证据

存在 Worker 且首次需要日志证据时，仅检查一次其完整安全会话记录是否可访问，并将实际访问证据写入 `worker_log_visibility` 和 `worker_log_evidence`。Root 返回正文或工具存在本身不能证明可访问。仅当依赖日志证据的审计无法取得/核验时才阻塞；否则报告限制并读取完整实际返回正文。无 Worker 时将 `worker_log_visibility` 设为 `Not applicable`，在 `worker_log_evidence` 记录原因，不得推断 Worker 日志结果。

## 失败边界

若无法提问、可靠计时、可中断等待、state-record guards 或审计回读，则标记 unavailable 并阻塞本门及依赖工作。保留可恢复的 pending 审计状态。若规范权威改变或 reconciliation 更新当前事实，则刷新当前 Context/Decision 后返回前序状态解决路线动作；不得重开 Mode 或重复已完成提示。

## 相关概念

- [Session Audit Visibility](../layer-01-fundamental-concepts/session-runtime/session-audit-visibility_zh_cn.md)

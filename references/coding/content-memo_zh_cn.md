# Worker Content Memo

本模块负责多 Agent Coding 中 Worker 执行内容总结文档的默认写入策略、工作语言与父级派发配置。它是 [`context-exchange_zh_cn.md`](context-exchange_zh_cn.md) 所定义 file-backed Context Exchange 中 content memo 的专项规则模块；目录 ownership、跨 Worker 传输、读写隔离与 handoff 机制仍由 Context Exchange 模块负责。

本模块只约束 `<primary-worktree>/.token-io-decoupling/context/<worker-context-id>/` 中由 Worker 维护的执行上下文总结，不改变 Semantic Contract、Progress Signal、Control Checkpoint、Change Verification、Git 交付或项目正式文档的语言与行为规则。

## 工作语言

Worker 写入其专属 Context Exchange 子目录的上下文文档，工作语言统一使用**中文**。

- `INDEX.md`、执行内容 memo、`findings.md`、`changes.md`、`verification.md`、`handoff.md` 以及其他由 Worker 新生成的 Context Exchange prose 默认使用中文。
- 路径、文件名、命令、代码符号、类型/函数/API 名称、配置键、hash、错误文本、日志片段以及其他需要保持精确性的原始技术内容保持原文，不为满足中文工作语言而强制翻译。
- 从其他 Worker 机械复制到 `imports/` 的原始文档保持源内容，不做 LLM 翻译或重写。
- 本规则不要求代码注释、Git commit message、Issue/PR、README、用户可见文档或其他产品产物改用中文；这些产物继续遵循各自项目与任务规则。

## `write_content_memo` 派发配置

父级 Input-side Reasoning Agent 在向独立 Worker 派发任务 / Interaction Slice 时使用布尔配置项：

```text
write_content_memo: true
```

语义如下：

- `true`：默认值。Worker 必须在自己的 Context Exchange 子目录中维护一份简洁的**执行内容总结 memo**，记录本 slice 已完成的工作、稳定发现、关键路径/符号、实际变更、验证状态、失败尝试中仍有复用价值的结论、剩余事项与必要证据指针。
- `false`：本 slice 不要求创建或维护执行内容总结 memo。只有父 Agent 判断该工作过于简单，且写 memo 的成本明显高于后续恢复、handoff 或复用价值时，才可以主动关闭。

如果父 Agent 的派发消息省略 `write_content_memo`，必须按 `true` 解释。为减少歧义并提高派发可见性，父 Agent **应在独立 Worker 的 Dispatch 中显式携带该字段**。

Worker 不得根据自己对任务复杂度的判断把 `true` 改为 `false`，也不得因为预计不会发生 handoff 就自行跳过。只有父 Agent拥有关闭该开关的权限；后续 slice 可以由父 Agent重新指定该值。

## 默认 memo 行为

当 `write_content_memo: true` 时：

1. 父 Agent 在派发前为 Worker 建立专属 Context Exchange 子目录，并把准确路径与该配置一起发送给 Worker。
2. Worker 在开始形成可复用执行状态后创建或更新 memo；不要求在第一条命令前创建空文件。
3. Worker 在 material milestone、阻塞式 Control Checkpoint、handoff、正常退出或被替换前刷新 memo。不得把它写成逐命令 execution journal。
4. Worker-local `INDEX.md` 应记录该 memo 的文件名、用途与最近 material update，使父 Agent或获授权的后继 Worker可以按需定位。
5. memo 保持压缩，只记录稳定、可复用、可验证的执行状态。完整日志、完整 diff、大段源文件、私有 chain-of-thought、秘密和无关会话历史继续禁止写入。

推荐默认文件名为 `content-memo.md`。如果某个既有 Worker 子目录已经有一个明确承担同等职责的文档，Worker 可以继续更新该文档而不是机械创建重复文件，但必须在 Worker-local `INDEX.md` 中明确它承担 content memo 职责。

## `write_content_memo: false` 的边界

关闭 content memo 只取消本 slice 的**文件化执行内容总结**要求，不关闭其他协议：

- Worker 仍必须遵守 `Objective`、`Authorized scope/mutations`、`Return conditions` 与 `Unreleased boundary`；
- Progress Signal 与 Control Checkpoint 仍按 execution-control 规则触发；
- Worker 仍须向父 Agent 返回完成当前 slice 所需的压缩结果与证据；
- Change Verification 的独立性与验证证据要求不受影响；
- Semantic Contract、Decision Checkpoint、Context Firewall、权限边界与用户授权不受影响；
- Worker replacement 若确实发生，而缺少 memo 会阻塞接力，父 Agent仍应使用当前可获得的最小事实完成必要 handoff，不得伪造历史。

因此，`write_content_memo: false` 是一个针对简单工作的输出/文件写入优化开关，不是关闭 Context Exchange 或父级 control loop 的总开关。

## 派发示例

```text
Objective: 修复认证中间件中的 token refresh 边界问题
Authorized scope/mutations: src/auth/**, tests/auth/**
Return conditions: 实现完成并返回聚焦检查结果
Unreleased boundary: 文档、最终 Change Verification、Git 操作
Own Context RW: <primary-worktree>/.token-io-decoupling/context/worker-auth/
write_content_memo: true
```

对于父 Agent 明确认定的极简单 slice：

```text
Objective: 修正一个已确认的配置键拼写
Authorized scope/mutations: config/example.yaml
Return conditions: 单行修正完成并返回 diff 摘要
Unreleased boundary: 其他文件与 Git 操作
Own Context RW: <primary-worktree>/.token-io-decoupling/context/worker-config/
write_content_memo: false
```

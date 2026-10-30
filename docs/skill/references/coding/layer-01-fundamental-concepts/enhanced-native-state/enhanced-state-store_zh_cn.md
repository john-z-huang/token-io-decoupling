# Enhanced 状态存储

[English](enhanced-state-store.md) | [简体中文](enhanced-state-store_zh_cn.md)

本文档负责可选 Enhanced Root 与 Worker 状态存储的持久化权威和访问边界。它不重新定义任务记录字段、Mode/Count、Slice/Control 政策、审计语义或 Worker 生命周期。

## 通用规范

### 权威记录与首次写入

Native 运行时，parent-context 记录仍按[委派状态记录](../delegation/delegation-state-record_zh_cn.md)保持 canonical。获授权的 Enhanced Root store 初始化且身份/schema 通过核验后，该 Root store 才是 Enhanced 路径的 canonical 记录；parent context 仅保留可读快照或引用，不得成为竞争的可写权威。从 Native 切换到 Enhanced 遵循[Native 对账](native-reconciliation_zh_cn.md)；反向切换遵循[Native 权威转移](native-authority-transfer_zh_cn.md)。本存储 owner 负责持久化和访问边界，不负责这两种转换流程。

首次获授权的 Root 写入须等待 Mode 门禁通过，并确认当前 Root Session 身份、职责和 Context Firewall 边界。打开 Root store 会按既有 owner 创建 pending 工作流状态和预留槽位；它本身不释放 Mode、Session、审计、Allocation 职责或 Slice 权限。若审计仍待处理，应在能力可用时保存真实的 `pending` 状态；open 成功而后续审计 transition 失败属于可恢复中间状态。不得推断用户已答复、已选择默认值、审计已完成或可推进依赖工作。

Session Audit 的值、提问文本、时序、resolution 和 Root-only 权限仍由[Session Audit Visibility](../session-runtime/session-audit-visibility_zh_cn.md)及[委派状态记录](../delegation/delegation-state-record_zh_cn.md)负责。通过获准的类型化 transition 持久化 Root 记录。不得将完整 Root 审计对象或提问历史复制到 Worker 可控状态。审计配置不授予 Mode、Allocation、Slice、生命周期或其他权限。

### Root 与 Worker 边界

Root 独占工作流控制状态和 Root-only 元数据。只有真实子 Agent 已创建、身份核验且绑定到已释放 Allocation 后，才可初始化 Worker store。Worker 只能读取自身不可变任务快照，并写入自己的进度、证据和阻塞记录。它不能选择其他 Worker/路径、写 Root 控制状态、修改任务快照或读取其他 Worker 的 store。既有记录形状及子 Agent 生命周期政策仍为权威。

只保存结构化状态、语义引用及 Hash、证据引用和有界恢复索引。完整语义正文继续归其既有文档或 Memory owner。可信能力快照是对观测绑定的证据，本身不构成授权。

### 读取、写入与恢复索引

只读状态和 Schema 诊断不得创建文件、应用迁移、刷新快照、推进 Revision 或修改收据。未绑定状态查询不得访问状态路径。已绑定 Root/Worker 只能检查自身获准 store；调用方不得提供任意数据库路径。

状态写入使用既有类型化操作、预期 Revision 和幂等键。同键、同操作、同载荷重放返回原收据且不重复生效；冲突复用必须拒绝。重放或读取不得暗中更新状态。State Revision、Schema version、规则 Hash 和各 Verification Epoch 相互独立。

恢复索引有界且顺序稳定。分页游标绑定集合及观察到的 Revision；过期游标应拒绝且不写入。分页元数据须让省略条目可通过后续游标读取。索引只含引用和 Hash，不复制语义正文。对于缺少 `output_class` 或 `write_content_memo` 的旧 Root 记录，保留 unknown 值并明确记录字段缺失原因；不得推断为当前合法值，也不得用该未知字段授权或放行操作。打开 store 不得丢弃或覆盖有效 Native 记录；依赖写入前须遵循对应的 Native 转换 owner。

## Codex CLI / ChatGPT Desktop 特别优化指令

只有当前 Session 暴露可信绑定且具备该操作所需守卫时，才能使用状态服务。生产在缺少该 Provider 时默认拒绝受保护状态操作。SDK 或 fake 绑定测试只证明受测服务/协议契约，不能证明真实宿主身份或 OS 隔离。未选择 Enhanced 或其不可用时，若 Native 前提仍满足，则沿用既有 Native 记录。

## Claude Code CLI / Claude Desktop 特别优化指令

当前没有 Claude 专属的状态存储优化。遵循通用规范，受保护访问必须有直接暴露且可信的身份和守卫。

## 相关概念

- [Enhanced Schema Migrations](enhanced-schema-migrations_zh_cn.md) — 负责 Schema 状态、迁移、备份和恢复边界。
- [Native 对账](native-reconciliation_zh_cn.md) — 负责 Native-to-Enhanced 权威转换。
- [Native 权威转移](native-authority-transfer_zh_cn.md) — 负责 Enhanced-to-Native 权威转换。
- [Coding Delegation State Record](../delegation/delegation-state-record_zh_cn.md) — 负责记录字段及 Native parent-context 权威。
- [Coding Delegation Worker Boundary](../delegation/delegation-worker-boundary_zh_cn.md) — 负责 Worker 快照与写入范围。
- [Coding Execution Control](../execution-control/execution-control_zh_cn.md) — 负责 Slice 与 Control 政策。

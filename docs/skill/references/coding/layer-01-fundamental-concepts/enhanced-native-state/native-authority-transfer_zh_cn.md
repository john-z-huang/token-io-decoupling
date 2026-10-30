# Native 权威转移

[English](native-authority-transfer.md) | [简体中文](native-authority-transfer_zh_cn.md)

本文档负责将已建立的 Enhanced Root 工作流权威安全转回 Native parent context。不定义工作流字段、Mode/Count、审计政策、Worker 生命周期或产品专属导出能力。

## 通用规范

### 适用条件

若该工作流从未初始化 Enhanced 持久化，则 Native parent context 为规范记录。记录转移为 `Not applicable` 并说明原因；不得虚构 Enhanced 历史。获授权的 Enhanced Root store 初始化且核验通过后，在本转移流程完成前始终保持权威。服务中断、守卫缺失、路线偏好或公共规则可读均不会切换权威。

这是安全协议，不代表每个宿主或服务都实现了导出、停止写入或转移操作。只有当前获授权环境实际暴露所需操作及证据时才能使用。可选建议 API 失败本身不表示健康的 Enhanced 状态服务不可用，也不会触发转移。

### 切换前冻结、结清并核验

写入 Native 规范记录前，核验同一 project、Root、Run、Mode/Count、schema 和当前规范 Root 记录。停止接受新的依赖写入，并实际冻结该权威的所有写入者。结清每个进行中操作和跨存储副作用的最终结果。超时、客户端断连、缺少响应或声称服务器已停止，都不能证明回滚或已静止。只要仍可能有写入者或操作提交，就阻塞依赖写入并保留不确定状态以供恢复。

仅转移 Native 能完整表示的规范记录。保留稳定身份、allocations、生命周期、当前状态、引用、审计状态及其 unknown 或 pending 值，以及理解记录所需的证据。审计字段及时序仍由[Session Audit Visibility](../session-runtime/session-audit-visibility_zh_cn.md)和[委派状态记录](../delegation/delegation-state-record_zh_cn.md) owner 负责；转移不代替用户答复、不重置或补默认审计值，也不把审计政策复制到 Worker 状态。不得重建缺失历史字段，也不得将 unknown 替换为当前默认值。

将核验后的记录写入 Native 规范上下文并读回。只有完整受支持的结构化记录及其身份与冻结的 Enhanced 记录一致，才可将 Native 视为新的规范权威。保留原 Enhanced 记录和转移证据作为历史；不得采用最后写入胜出、覆盖有效记录或丢弃未决对账。若 Native 无法保留必需字段、引用或生命周期事实，则阻塞依赖工作，不得声称转移完整。

若转移在读回确认前中断，结果为不确定。不得恢复任一权威的写入，也不得推断部分 Native 写入已成功或已回滚。保留两份记录及已完成的准确边界；只有获授权操作明确解决哪份记录完整且为规范记录后才能继续。冻结但未经核验的转移不授权继续写 Native。

### 权威边界

本流程只更改现有 Root 记录中哪一份为规范记录。不授权更改 Mode/Count、新建 Run 或 allocation、创建 Worker、释放 Slice、改变生命周期、通过验证或产生外部影响。保留既有 Worker 身份和状态边界；本文档不转移或合并 Worker store。方向为 Native 到 Enhanced 时，另遵循 Native Reconciliation owner。

## Codex CLI / ChatGPT Desktop 特别优化指令

仅使用当前直接暴露且获授权、能够冻结 Enhanced 写入者、结清进行中副作用、写入 Native parent 记录并核验读回的操作。不得从 CLI、SDK、fake binding、协议测试或未验证宿主推断这些能力。任何必需操作缺失或未验证时，阻塞依赖写入。不得使用 Computer Use 建立转移依据。

## Claude Code CLI / Claude Desktop 特别优化指令

当前没有 Claude 专属的权威转移优化。遵循通用规范，并要求操作和证据实际暴露且获授权。

## 相关概念

- [增强工作流可用性](enhanced-workflow-availability_zh_cn.md) — 负责路线选择及能力不可用时的处置。
- [增强状态存储](enhanced-state-store_zh_cn.md) — 负责 Enhanced 持久化权威和访问边界。
- [Coding Delegation State Record](../delegation/delegation-state-record_zh_cn.md) — 负责规范记录字段和 Native parent-context 权威。
- [Native 对账](native-reconciliation_zh_cn.md) — 负责反向的 Native-to-Enhanced 转换。

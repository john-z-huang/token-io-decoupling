# Native 对账

[English](native-reconciliation.md) | [简体中文](native-reconciliation_zh_cn.md)

本文档负责 Mode 与 Session 边界通过后，将 Native Root 记录显式对账到 Enhanced。不负责记录字段、Mode/Count、Session Audit 政策、Worker 生命周期、Schema 迁移机制或 Enhanced 可用性选择。

## 通用规范

### 依赖 Root 写入前读取并比较

当 Native parent context 为规范记录且选择 Enhanced 时，先核验当前 Root 身份、操作守卫和 Schema。没有 Native 历史的新 Enhanced 工作流将此检查记为 `Not applicable`，不得虚构既有状态。已有 Native 记录或未决比较历史时，须按有效游标读完完整有界集合，然后才能进行普通依赖 Root 写入。只读状态检查不授权写入。比较本身是会推进 Revision 的幂等 Root 修改，须先获授权并在写后读回。

将准确的当前 Native snapshot 与 Enhanced Root 记录比较。两阶段精确确认仅适用于它审阅的那条比较，不会消除其他未决记录。存在实质差异时，审阅完整当前未决集合、其摘要、最新目标 snapshot，以及所有可见的来源、引用、Revision 和 Epoch 详情。Root 决定及静止/新鲜度证据须绑定到这份准确集合。引用用于定位证据；Hash 或调用方断言本身不能证明语义真实或拥有权威。

### 支持的裁决与阻塞条件

对于受支持的实质差异，Root 明确选择 Native Contract source 与 semantic references 这一对，或同时保留 SQLite 的两项值。保留原始 Native 与 SQLite 记录、所有比较，以及带证据引用的裁决结果。不得逐字段任意合并、改写旧比较，或让较新的匹配 snapshot 隐藏较早的有效冲突。

若任一已审阅 snapshot 改变不可变的 project、Root、Run、Mode/Count、mode source、allocation 身份、生命周期或派发历史；若有已绑定或已初始化的 Worker、pending dispatch、活动 Worker Slice、必需历史未知、数据格式错误或不受支持的超大旧记录；或无法审阅完整集合，则阻塞裁决。不得重建身份、在缺少 Root 历史时导入已有进展的 Native-only 工作流、恢复终止状态或伪造历史 preimage。过期或有歧义的旧比较保持未决，直到新的受支持比较和显式审阅建立有效依据。

### 恢复 floor 与新放行

成功裁决须针对当前 Root Revision 和完整审阅集合原子提交。保留身份和当前 Root 审计记录；不得导入或重置 Native 审计状态，也不得以其替代当前[会话审计可见性](../session-runtime/session-audit-visibility_zh_cn.md) owner。结果 Revision 精确为 `max(当前 SQLite Revision，所有已审阅 Native Revision) + 1`。三个 Verification Epoch 分别精确为 `max(该维度当前 SQLite Epoch，所有已审阅 Native Epoch) + 1`。CAS 过期或发生溢出时拒绝并确保无部分裁决。

保留既有证据、评估、Control 结果、收据以及 pending/returned Evidence-on-Demand 请求作为历史。恢复 Revision floor 会使所有 floor 之前的结果失效，包括 Epoch 覆盖维度为空的事实。不得删除旧证据或将其重新解释为新鲜。尚未返回证据的 Evidence-on-Demand 请求继续保持 pending；已返回请求的状态和历史不得重写。Continue 必须有 floor 后与该请求关联的真实新返回证据。完成裁决后，后续放行前重新核对当前获准任务边界和相关事实；不得重开已锁定的 Mode，也不重复已完成的 Session Audit 提问或裁决；离开 Session 边界前仍须读回并确认当前规范审计记录。

释放下一 Slice 前，必须取得明确记录在恢复 floor 之后、且对当前 Control 规则和相关 Epoch 仍有效的新 Control `Continue`。Slice 和 Control 的归属遵循[Coding Execution Control](../execution-control/execution-control_zh_cn.md)。先前的 Continue、API 建议或比较成功都不够。状态或适用 Epoch/规则发生变化时，重新取得当前 Control 结果。`Amend` 返回既有 Contract 与 Decision 检查，重新通过 Control 后才能放行；`Stop` 不放行。实现后的普通 Control 仍按原路线进入当前状态 Verification。

### Root-only 权威与副作用

只有可信 Root 能比较、确认或裁决。任何比较或确认仍未解决时，须在副作用发生前拒绝依赖 Root 写入，包括完成派发或初始化 Worker。仅允许只读检查、获授权的比较/裁决及真正无副作用的收据重放。所有状态改变仍须绑定 CAS 和幂等键。本流程不授予 Mode、Count、Allocation、Worker、Slice、验证或外部影响权限。

## Codex CLI / ChatGPT Desktop 特别优化指令

仅使用当前 Session 实际暴露的获授权 Root 状态操作和有界分页。裁决前审阅所有未决页及实际引用来源；不得使用原始数据库访问、伪造 snapshot 或 GUI 操作。fake binding 或 SDK 协议测试只证明其测试边界，不能证明真实宿主身份或语义真实性。

## Claude Code CLI / Claude Desktop 特别优化指令

当前没有 Claude 专属的对账优化。遵循通用规范，仅使用实际暴露且获授权的 Root 操作。

## 相关概念

- [增强状态存储](enhanced-state-store_zh_cn.md) — 负责 Root 持久化、类型化操作及有界恢复索引。
- [增强工作流可用性](enhanced-workflow-availability_zh_cn.md) — 负责路线选择和能力不可用时的处置。
- [Coding Delegation State Record](../delegation/delegation-state-record_zh_cn.md) — 负责规范记录字段及 Native 权威。
- [Coding Execution Control](../execution-control/execution-control_zh_cn.md) — 负责 Slice 与 Control 政策。
- [Native 权威转移](native-authority-transfer_zh_cn.md) — 负责反向的 Enhanced-to-Native 转换。

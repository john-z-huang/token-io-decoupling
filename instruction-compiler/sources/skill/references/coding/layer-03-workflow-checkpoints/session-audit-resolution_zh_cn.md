# Session 审计解决

[English](session-audit-resolution.md) | [简体中文](session-audit-resolution_zh_cn.md)

本检查点负责将当前 Session 审计偏好应用于父级控制记录，并核对最终值；不将审计可见性设为权限或执行门禁。

## 触发与输入

取得规范 parent-context 记录后，使用该记录和当前 Session 审计事实。应用[Session Audit Visibility](../layer-01-fundamental-concepts/session-runtime/session-audit-visibility_zh_cn.md)了解字段值与显示语义，并应用[委派状态记录](../layer-01-fundamental-concepts/delegation/delegation-state-record_zh_cn.md)了解记录归属和结构。

## 决策与结果

使用用户已提供或当前父级控制记录中保留的有效显式偏好。否则立即应用缺省值：Root 为 `balanced/milestone_only`；Worker 为 `full`。用户可明确更改任一偏好，父级记录最终值及其显式或缺省来源。不得强制首次提问。不得启动计时器、等待回复或迁移旧提示状态值。

若现有记录含过时提示/计时或迁移字段，则忽略这些字段并保留有效偏好值。不得根据过时提示状态推断偏好。若当前显式值冲突或无效，适当时只针对受影响偏好请求澄清；若无法解决，则使用策略缺省值并报告限制，不阻塞无关工作。

Worker 日志可见性仍只是证据描述。若任务依赖访问完整安全 Worker 会话记录，只能依据实际访问证据报告 `available`、`unverified` 或 `unavailable`；不存在 Worker 时，记录带理由的 `Not applicable`。若该证据是必需的且不可用或未验证，则仅阻塞依赖它的审计判断。仅返回最终正文或发现工具均不能证明可访问完整日志。

## 失败边界

偏好收集是可选项，绝不授予授权。未提供偏好时，继续使用有效缺省值。保留必需进度报告和保密规则。仅当某项判断依赖缺失的必需审计证据时才阻塞；报告偏好或 Worker 日志证据不可用，但不得把它视为完成证明。

## 相关概念

- [Session Audit Visibility](../layer-01-fundamental-concepts/session-runtime/session-audit-visibility_zh_cn.md)
- [Coding Delegation State Record](../layer-01-fundamental-concepts/delegation/delegation-state-record_zh_cn.md)

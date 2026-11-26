# 2026-11-18 · Pi Skill 文档与运行时校准

## 审查范围与原则

扫描 `docs/skill` 下 138 份 Markdown，对照 Pi 扩展的启动、快照、检查点、工具入口，以及 MCP 工具清单和可信调用边界。修订 30 份文档。规则由 `references/coding` 的 owner 定义，Hooks 负责说明当前动作所需条件和证据；导航索引和来源对照表供定位。

## 主要改动

- **启动和会话。** 区分扩展的三项模式菜单与手动回退的四项菜单。缺失答案须经用户确认。按扩展的实际状态回读模式、预算、已占用 allocation 和审计偏好，空闲预算以数量表示。审计偏好在同一 Session 内沿用，日志访问仍需实际证据。[Session 合同](../docs/skill/hooks/session.md)
- **执行和恢复。** 对齐 `DE02` 的 Root 分支、`DE04` 放行、`DE06` 派发条件，以及 `executor_changed`、决策补证返回、归档保全和验证 epoch。当前适配器通过任务正文携带显式 `write_content_memo`，Root 仍需核验实际 Worker 能力和授权。[委派合同](../docs/skill/hooks/delegation.md) · [恢复合同](../docs/skill/hooks/recovery.md)
- **MCP 和授权。** 区分只读规则摘录、候选文件预检、Memory 尾部读取及文本存在性检查、以及受保护的输出物化。同步已移除的工作流专用接口说明。默认 stdio 缺少物化所需的可信 Worker 绑定，候选预检的磁盘证据取决于启动配置的可信读取器。[工作流架构](../docs/project/WORKFLOW_ARCHITECTURE.md)
- **依赖方向。** 解除 `planning` 与 `context` Hook 的互引。共享计划规则回到任务计划 Memory 生命周期 owner。核对 113 份 Coding 参考文档和 16 份 Hook 执行合同，规则来源表没有 Hook 间引用，参考文档没有指向 Hooks 的反向链接，Hook 执行合同之间无循环。[来源与链接规则](../docs/skill/hooks/README.md#来源整合与链接基准)

## 验证

- **PASS** · 文档链接、层级结构及工作流地图检查，61 项文档测试，144 项 Pi 扩展测试，336 种 Hook 注入场景，Pi 1.5.2 入口加载检查及 4 个离线 wheel 构建。
- **SKIPPED** · 真实 Pi 会话、真实子代理、Memory 后端及 API 端到端验证。

本次提交范围为 Skill 文档及这份变更记录。规则摘要随文档变化，旧扩展会话恢复时须按现有 Hash 校验重新核验。

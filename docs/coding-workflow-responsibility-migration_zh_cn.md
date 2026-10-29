# Coding 工作流职责迁移记录

[English](coding-workflow-responsibility-migration.md) | [简体中文](coding-workflow-responsibility-migration_zh_cn.md)

本开发记录将旧 Layer-03 路线判断和 Layer-02 工作流选择文本映射到四层 owner。下列历史路径仅用于标识来源位置；当前 owner 使用有效路径链接。

| 原职责来源 | 新 owner | 路线消费位置 | 保留边界 |
| --- | --- | --- | --- |
| `workflows/coding.md` Entry/Routes：预检组合和唯一路线选择 | [路线入口](../references/coding/layer-03-workflow-checkpoints/route-entry_zh_cn.md) | 入口调用，在 S03/M03 核对 | Mode 菜单/默认/无效输入政策仍由 Mode owners 负责；入口链接所选路线。 |
| Layer-02 Environment/Capability Inventory：可选 Enhanced 资格选择 | [Enhanced 路径选择](../references/coding/layer-03-workflow-checkpoints/enhanced-path-selection_zh_cn.md) | S02/M02 | 通用能力证据和 Enhanced 可用性/state 政策仍由原 owner 负责。 |
| Layer-04 Session 步骤：规范 store authority、对账/转移、有守卫的打开/恢复、迁移资格和回读路由 | [Session 状态解决](../references/coding/layer-03-workflow-checkpoints/session-state-resolution_zh_cn.md) | S04/M04，在审计解决前 | authority、身份、角色、firewall、schema、迁移机制和类型化 state 政策仍由其 L1 owner 负责；故障不等于 authority 转移。 |
| Layer-04 Session 步骤：审计记录复用、固定提问、答复/澄清、超时和审计字段回读 | [Session 审计解决](../references/coding/layer-03-workflow-checkpoints/session-audit-resolution_zh_cn.md) | S04/M04，在状态解决后 | 审计字段/默认/显示语义仍归 Session Audit Visibility；state authority/schema 流程由 Session 状态解决及其 L1 引用负责。 |
| Layer-04 Context 步骤：决策背景生成触发、审阅、Hash/当前性及直接判断证据充足性 | [决策上下文选择](../references/coding/layer-03-workflow-checkpoints/decision-context-selection_zh_cn.md) | S05/M06，在下游建议/决策使用前 | 上下文生成机制和建议政策仍由其 L1 owner 负责；不替代建议选择。 |
| Layer-02 Context：有界规则查询和项目记忆检索流程选择 | [上下文来源选择](../references/coding/layer-03-workflow-checkpoints/context-source-selection_zh_cn.md) | S05/M06 | 范围、新鲜度、必需 Memory 能力和 memo 授权仍由原 owner 负责；始终检查活动计划，并明确来源检索的回退/阻塞结果。 |
| Layer-01 Execution Planning 通用分支：计划记忆生命周期调用 | [规划输出选择](../references/coding/layer-03-workflow-checkpoints/planning-output-selection_zh_cn.md) | S06/M07 | 计划记忆 owner 保留触发语义、持久化、回读、归档、不可变及失败政策。 |
| Layer-04 Multi-Agent M07 Bootstrap/Refresh 适用性 | [Bootstrap 选择](../references/coding/layer-03-workflow-checkpoints/bootstrap-selection_zh_cn.md) | 仅 M07 | 既有 Child Role Allocation 阈值、跳过条件、角色和名额授权仍具权威。 |
| Layer-04 Decision 步骤：Root/子代理执行者和现有候选选择分支 | [执行者选择](../references/coding/layer-03-workflow-checkpoints/executor-selection_zh_cn.md) | S06/M07 | Task Assignment 仍是执行者/候选政策 owner；Single-Agent Root 确定路线、明确冲突、当前 Session 资格、候选比较及派发前检查仍有效。 |
| Layer-04 Decision 步骤：独立评估 Root 直接大型输出及 yes/no 路由 | [输出路线选择](../references/coding/layer-03-workflow-checkpoints/output-route-selection_zh_cn.md) | S06/M07 | Output Token Routing 仍负责独立体量决策；明确指令、按模式挂起/路由及不授权创建仍有效。 |
| Layer-04 Multi-Agent M07/M08 边界：新子代理角色选择、唯一 Session 预留、容量及精确扩额 | [角色预留](../references/coding/layer-03-workflow-checkpoints/role-reservation_zh_cn.md) | M07 在 M08 Slice 前；M09 消费结果 | Child Role Selection、Count Gate、State Record 和 Child Role Allocation 保留角色、容量、状态和预留政策；不得提前放行 Slice 或创建。 |
| Layer-02 Contract、Mode、Decision、Control、Verification Epoch 的建议编排 | [建议选择](../references/coding/layer-03-workflow-checkpoints/advisory-selection_zh_cn.md) | S06/M07、S09/M11、S10/M12 | 建议 opt-in、获授权 Root、新鲜度、无权威效力和回退仍由 Decisions Advisory 负责。 |
| Layer-02 Repair 及路线修复/决策返回逻辑 | [修复处置](../references/coding/layer-03-workflow-checkpoints/repair-disposition_zh_cn.md) | S11/M13；重大决策返回 S01/S06 或 M01/M07 | 诊断、授权、修复范围、handoff 和变更 epoch 验证仍归 Layer-02 repair owners。 |
| Layer-02 Documentation 及路线影响返回逻辑 | [文档影响](../references/coding/layer-03-workflow-checkpoints/documentation-impact_zh_cn.md) | S12/M14 | 文档 epoch、必需检查、受影响内容重新验证和证据复用仍归 Documentation 与 Verification Epoch。 |

完整路线模板现位于 `references/coding/layer-04-workflows/`；Layer-04 保留有序调度、owner 调用、结果门禁、阻塞和返回。Layer-03 负责可执行的任务特定决策流程，但不重新定义 Layer-01/02 政策。以上职责行列明了从路线正文迁出的流程；路线摘要消费这些证据，不重复完整流程。

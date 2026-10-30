# Session 状态解决

[English](session-state-resolution.md) | [简体中文](session-state-resolution_zh_cn.md)

本检查点负责在解决审计配置前，按路线建立并读取当前规范 Root 状态；不负责审计提问、审计字段或迁移机制。

## 触发与输入

消费已选择的 Native 或 Enhanced 路径、已放行的 Mode/count，以及当前 Session 身份、角色和 Context Firewall 事实。应用[Session 模型](../layer-01-fundamental-concepts/session-runtime/session-model_zh_cn.md)、[Session 角色归属](../layer-01-fundamental-concepts/session-runtime/session-role-ownership_zh_cn.md)、[Session 上下文防火墙](../layer-01-fundamental-concepts/session-runtime/session-context-firewall_zh_cn.md)和[委派状态记录](../layer-01-fundamental-concepts/delegation/delegation-state-record_zh_cn.md)。仅在各自触发条件成立时，Enhanced state 还应用[增强状态存储](../layer-01-fundamental-concepts/enhanced-native-state/enhanced-state-store_zh_cn.md)、[增强 Schema 迁移](../layer-01-fundamental-concepts/enhanced-native-state/enhanced-schema-migrations_zh_cn.md)、[Native 对账](../layer-01-fundamental-concepts/enhanced-native-state/native-reconciliation_zh_cn.md)和[Native 权威转移](../layer-01-fundamental-concepts/enhanced-native-state/native-authority-transfer_zh_cn.md)。

## 决策与结果

1. 确认已选后端和已释放的 Session 事实。若 Mode、身份、角色、Context Firewall 或必需 Schema 证据缺失或冲突，则在打开或写入 Root state 前停止。
2. 确立哪个记录具备规范权威。若选择 Enhanced 但 Native 仍可能持有当前规范记录，必须在普通 Enhanced 打开或依赖写入前完成 Native 对账。若要将已建立的 Enhanced 记录转回 Native，仅在 Native 权威转移 owner 的条件成立时才使用该流程。单纯故障绝不改变权威。若选择 Native 且不存在既有 Enhanced 权威，则将 Enhanced store/schema 和转移检查记录为 `Not applicable` 并注明观察到的原因。
3. 对 Enhanced state，在首次打开前核验绑定 host 身份、仅 Root 访问、路径、只读身份/状态守卫及兼容的 schema/history。需要迁移时遵循迁移 owner 的备份、版本、事务和完整性流程；本检查点只核对其证据。新建且没有 Native 历史的 Enhanced Root 将 reconciliation 记录为 `Not applicable`。不得把重建缺失或不可访问记录当作恢复捷径。
4. 仅在适用的 authority、身份、角色、firewall 和 schema 检查通过后打开或恢复 Root 记录。选择 Native 时使用 Native 规范 parent-context 记录；选择 Enhanced 时使用绑定的 Enhanced Root 记录。保留现有记录和待处理状态。
5. 回读当前规范记录、身份、revision 及适用的 allocation/state 证据。将已核实结果返回路线，供其后续审计解决动作消费；本检查点不负责审计记录配置和提问/恢复流程。

| 观察到的结果 | 必需路线动作 |
| --- | --- |
| 规范权威和记录已核实；有守卫的打开/恢复及回读成功 | 将记录和回读证据返回路线，供下一动作使用。 |
| Native 路线不涉及既有 Enhanced 权威，或无 Native 历史的新 Enhanced Root 不触发 reconciliation | 记录 `Not applicable` 及原因；仅在识别适用的规范记录后继续。 |
| 权威、身份、角色、防火墙、schema、迁移结果、必需守卫、打开/恢复或回读未知/失败 | 将依赖操作标记为不可用并阻塞依赖 state 的工作。保留可恢复状态；不得推断权威或创建替代记录。 |
| 对账实质改变当前事实或授权决策 | 返回当前 Context 和 Decision，之后重新建立并回读规范 state。不得重开 Mode 或重复已完成审计提问。 |

## 失败边界

适用 owner 的守卫通过前不得打开或写入 state。Enhanced 操作失败不构成转移权威或重置 state 的许可。回读失败会阻塞审计解决及依赖工作。

## 相关概念

- [Session 模型](../layer-01-fundamental-concepts/session-runtime/session-model_zh_cn.md)
- [增强状态存储](../layer-01-fundamental-concepts/enhanced-native-state/enhanced-state-store_zh_cn.md)

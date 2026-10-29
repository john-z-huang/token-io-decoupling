# 建议选择

[English](advisory-selection.md) | [简体中文](advisory-selection_zh_cn.md)

本检查点负责可选建议在各阶段的适用性路由。


## 触发与输入

Mode 和 Session 通过且存在获授权 Root 上下文前，建议记为 `Not applicable`；任务意图/输出分类使用直接权威来源。建议不能选择或改变路线选择结果，不能重开 Mode gate 或改变已锁定 mode/count。Root 上下文存在后，仅由 S06/M07 消费相关 Decision 建议，由 S09/M11 消费相关 Control 建议，由 S10/M12 消费相关 Verification/Epoch 建议。应用[Decisions Advisory](../layer-01-fundamental-concepts/execution-planning/decisions-advisory_zh_cn.md)和当前直接检查点 owner；将每条建议返回指定阶段进行基于证据的审阅。

## 决策与结果

1. Mode、Session 和已授权 Root 上下文通过前，记录 `Not applicable`；任务意图和输出分类使用直接权威来源。
2. 在 Decision、Control 和 Verification/Epoch 阶段，仅当建议已启用、符合条件、相关，且当前阶段绑定和 Root 授权已核实时，才评估可选建议。
3. 记录类型化建议、当前政策/输入/上下文 Hash、新鲜度结果及与直接 owner 的比较。将建议返回该阶段，并依据权威 owner 和当前证据决策。
4. Task Assignment、Output Token Routing 和角色预留建议不属于这五节点 opt-in 门禁；其 owner 独立控制这些决策。
5. 向路线调度返回已审阅建议或附理由的 `Not applicable`；建议不授权工作，也不替代通过条件。

## 失败边界

建议过期、不可用、格式错误或调用失败时，仅当必需事实仍充分时才回退到直接 owner 审查，否则阻塞。不得把外部建议调用变成强制要求，也不得绕过 opt-in/授权限制重试。

## 相关概念

- [Decisions 建议](../layer-01-fundamental-concepts/execution-planning/decisions-advisory_zh_cn.md)

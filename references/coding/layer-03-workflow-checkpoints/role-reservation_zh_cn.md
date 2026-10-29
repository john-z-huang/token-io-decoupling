# 角色预留

[English](role-reservation.md) | [简体中文](role-reservation_zh_cn.md)

本检查点负责 Multi-Agent 路线 M07 的预留决策。[Child Role Selection](../layer-01-fundamental-concepts/delegation/child-role-selection_zh_cn.md)、[Count Gate](../layer-01-fundamental-concepts/delegation/delegation-mode-count-gate_zh_cn.md)、[State Record](../layer-01-fundamental-concepts/delegation/delegation-state-record_zh_cn.md)和[Child Role Allocation](../layer-01-fundamental-concepts/delegation/delegation-child-role-allocation_zh_cn.md)分别是角色选择、容量、身份/状态及预留政策的权威 owner。

## 触发与输入

仅当 Executor Selection 针对获授权拟议任务返回 `new-executor-needed`，且 Output Route Selection 已独立处置 Root 直接输出后运行。读取四个已链接的 L1 owner 及当前 Session 角色/allocation/容量事实。

## 决策与结果

1. 应用 Child Role Selection，将实际获授权拟议任务匹配到一种受维护角色。遵循用户明确的角色指令；仅当 owner 触发条件满足时使用其有条件的 Primary 回退。建议或 Primary 偏好不授权创建。
2. 从 State Record 和 Role Allocation owner 读取完整的当前 Session 角色台账。任一 Session 成员已预留或创建的角色均视为占用。不得将其他 Session 的继承子代理计入。
3. 若存在匹配的其他未占用角色，在锁定容量内将其唯一预留记录到当前 allocation。若仅容量不足，且该角色仍未占用，则经 Count Gate 请求明确批准恰好 `+1`。不得自动扩额。
4. 若四种角色都已占用，阻塞且不申请更多容量。向 M07 返回预留、有证据/理由的 `Not applicable` 或阻塞。M08 Slice 和 M09 创建仍是后续独立门禁。

## 失败边界

缺少获授权任务、Session 状态过期或不确定、角色冲突、角色不可用、容量不足且无精确批准，或角色适配未决时，阻塞 Slice 释放。本检查点不释放 Slice、不创建或派发。

## 相关概念

- [Child Role Selection](../layer-01-fundamental-concepts/delegation/child-role-selection_zh_cn.md)
- [Delegation Count Gate](../layer-01-fundamental-concepts/delegation/delegation-mode-count-gate_zh_cn.md)
- [Delegation State Record](../layer-01-fundamental-concepts/delegation/delegation-state-record_zh_cn.md)
- [Child Role Allocation](../layer-01-fundamental-concepts/delegation/delegation-child-role-allocation_zh_cn.md)

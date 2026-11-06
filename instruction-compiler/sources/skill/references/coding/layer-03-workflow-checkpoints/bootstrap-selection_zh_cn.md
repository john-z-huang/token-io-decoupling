# Bootstrap 选择

[English](bootstrap-selection.md) | [简体中文](bootstrap-selection_zh_cn.md)

本检查点负责当前多代理任务是否消费 Bootstrap/Refresh。


## 触发与输入

当前事实已建立且 Root 已授权当前任务范围后，判断该任务是否触发 Bootstrap/Refresh，并以此范围作为评估输入。若 Bootstrap/Refresh 提出具体辅助任务，Root 必须在执行者选择或角色预留前另行审查并授权该任务。读取[Child Role Allocation](../layer-01-fundamental-concepts/delegation/delegation-child-role-allocation_zh_cn.md)，了解其既有触发、阈值、跳过条件及角色/slot 授权。

## 决策与结果

1. 列明 Root 已授权的当前任务范围、拟议角色、角色占用/slot 及相关 Memory 事实，并标注来源。
2. 逐项应用 Child Role Allocation 原有的触发条件、阈值和跳过条件；记录命中的条件，或明确缺失事实及 `Not applicable` 理由。
3. 若触发，向后续 Executor Selection 和 Role Reservation 返回拟议 Bootstrap/Refresh 任务及依据；否则返回 `Not applicable`。
4. 向调用方返回决策证据，供后续任务和职责决策使用。本步骤不预留角色/容量、不创建 child、不释放 Interaction Slice。

## 失败边界

触发事实或授权不清时阻塞此分支。不得复制/重定义 owner 阈值、推断新角色、提前预留容量或绕过后续 Slice 与创建门禁。

## 相关概念

- [子代理职责分配](../layer-01-fundamental-concepts/delegation/delegation-child-role-allocation_zh_cn.md)

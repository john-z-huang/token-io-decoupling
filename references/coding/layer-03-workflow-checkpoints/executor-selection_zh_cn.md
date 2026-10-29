# 执行者选择

[English](executor-selection.md) | [简体中文](executor-selection_zh_cn.md)

本检查点负责 S06/M07 的执行者路由。[Task Assignment](../layer-01-fundamental-concepts/execution-planning/task-assignment_zh_cn.md)仍是执行者及候选选择政策的权威 owner。

## 触发与输入

在建立当前事实、用户明确指令、已锁定模式及获授权拟议任务后运行。读取 Task Assignment owner，并核验当前 Session allocation、身份、能力、权限和可用性事实。执行者选择不决定输出体量，也不释放子代理 Slice。

## 决策与结果

1. 首先检查明确指令。在模式、权限、当前身份、能力、范围和可用性均允许时遵循明确执行者/候选，并仅跳过对应建议。锁定 Single-Agent 模式下，明确 `sub_agent` 与模式冲突，应返回 Root 复核；明确 `root` 有效。没有执行者指令时，Single-Agent 路线确定由 Root 执行，且不请求执行者建议。
2. Multi-Agent 模式下，根据当前任务事实和获授权范围判断。若权限与能力支持 Root，返回 `root`；若需要子代理，仅检查身份已核实且符合条件的当前 Session 子代理。Fork 后先为新 Session 完成新的 mode/count 重新进入；继承的子代理不会因重新进入而成为新 Session 的候选。
3. 应用 owner 的候选筛选。只有一个合格候选时直接选择。存在多个候选时优先考虑合格且空闲的候选；筛选后恰好一个空闲候选时选择该候选。若有两个或更多合格空闲候选，按 Task Assignment 中当前的任务上下文程序比较，包括适用的空闲 Primary 分支。不得按 transcript 体量或虚构阈值选择。若已核实 `sub_agent` 执行者方向且没有合格候选，依据授权、任务事实和候选筛选证据记录路线处置 `new-executor-needed`。它既不是新增的注册决策或工具返回枚举，也不授权创建。若合适子代理均忙碌，将忙碌状态交路线，在等待前独立评估输出路由。
4. 对忙碌候选，在等待前依据 Output Token Routing 路由每项 Root 直接输出。`no` 返回 Root 的其余门禁；`yes` 要求合适的空闲子代理或挂起/等待；证据不足/失败时保持未决，除非已核实的直接事实足够。派发前立即复核身份、权限、角色、能力、范围及最新可用性。
5. 返回 `root`、所选候选、`new-executor-needed`、`hold` 或 `insufficient_evidence`，附当前证据、建议调用时使用的政策/输入/上下文 Hash 及理由。建议失败绝不默认 Root。本检查点不预留新角色、释放 Slice、创建或派发。

## 失败边界

事实缺失或过期、指令冲突、模式/权限/能力未知、候选身份不可用、选择未决，或建议/Hash 失败且直接证据不足时，返回未决并阻塞后续释放。不得假设 Root 或候选可用。

## 相关概念

- [Task Assignment](../layer-01-fundamental-concepts/execution-planning/task-assignment_zh_cn.md)
- [Output Token Routing](../layer-01-fundamental-concepts/execution-planning/output-token-routing_zh_cn.md)
- [Session Model](../layer-01-fundamental-concepts/session-runtime/session-model_zh_cn.md)
- [Delegation State Record](../layer-01-fundamental-concepts/delegation/delegation-state-record_zh_cn.md)

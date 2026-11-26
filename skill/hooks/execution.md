# 主代理执行 Hook

## 触发条件

单代理执行阶段，或多代理路线中主代理推进自己承担的工作时。

## 输入与证据

当前计划、可执行任务、允许影响的路径和相关前置结果。

## 执行要求

1. 按[执行边界](../references/execution/execution-control.md#划定可执行范围)核实依赖、当前授权和结束条件。
2. 按[阶段反馈规则](../references/execution/execution-stage-feedback.md)记录实际结果、失败和新证据。需要调整或恢复时，先按[继续、调整或暂停条件](../references/execution/execution-control.md#继续调整或暂停)判断。
3. 依赖就绪后推进下一项工作。多代理路线中的命令执行按[主代理职责](../references/roles/main-agent.md#执行要求)约束。

## 输出与落点

可供后续任务或验证使用的当前产物、实际操作证据和障碍。

## 退出与阻断

本项交付可验证时继续。授权缺失或实质前置条件未满足时暂停本项工作。

## 重新核验

任务输入、资源、授权或上游结果变化时重新核对其影响。

## 规则来源

并行和串行条件见[任务边界与依赖](../references/planning/task-planning.md#划分任务与依赖)。

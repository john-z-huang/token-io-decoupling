# 工作流导航选择

[English](workflow-navigation-selection.md) | [简体中文](workflow-navigation-selection_zh_cn.md)

本检查点选择当前编译指令交付入口及有用的可选结构输入检查；交付和结构结果与独立判断任务事实及完成状态保持分离。

## 触发与输入

使用当前[环境](../layer-02-workflow-concepts/entry-and-context/environment_zh_cn.md)及[能力清单](../layer-02-workflow-concepts/entry-and-context/environment-capability-inventory_zh_cn.md)结果。可选导航可能有帮助时，参考[工作流导航可用性](../layer-01-fundamental-concepts/workflow-navigation/navigation-availability_zh_cn.md)和[工作流规则上下文](../layer-01-fundamental-concepts/workflow-navigation/rule-context_zh_cn.md)。若对所供检查点事实执行结构检查可能有帮助，则应用[检查点结构检查](../layer-01-fundamental-concepts/workflow-navigation/checkpoint-structure-checks_zh_cn.md)。除非任务本身要求相关结果，否则两种辅助能力均为可选。

## 决策与结果

1. 标识当前指令单元及动作所需的明确继续入口，保留准确暂停位置与已完成副作用。
2. 可选导航有用且可用时，消费其当前完整指令正文，核验语言、资源或构建标识及完整性；这些均不建立身份、权限、语义真实性、检查点完成、跨调用顺序或验收。
3. 结构检查有用时，对照所供输入和当前编译指令审阅结构结果，再独立判断证据含义；结构结果不建立授权或语义真实性。
4. 可选辅助能力不需要时，记录附理由的 `Not applicable`，直接消费对应已交付指令，不查找作者文档。
5. 可选导航不可用时，可由实际可用且获授权的同构建生成纯文档指令入口提供明确当前单元。必需资源缺失、不完整或不兼容时阻塞依赖判断；资源错误不授权作者源回退。
6. 返回所选来源和任何所需的结构检查结果供审阅。本决策不会更改工作流状态、授权操作或建立检查点结果。

## 失败边界

| 结果 | 必需操作 |
| --- | --- |
| 不需要可选导航 | 记录 `Not applicable`；直接消费必要已交付指令。 |
| 有界导航可用 | 审阅当前完整正文及准确继续入口，独立判断事实。 |
| 不需要或无法进行可选结构检查 | 附理由记录 `Not applicable`；除非任务独立要求该结果，否则依据当前编译指令继续。 |
| 结构检查可用且已选择 | 对照当前指令和所供输入审阅结果，独立判断证据。 |
| 导航不可用但同构建生成指令可访问 | 消费准确交付单元并记录限制。 |
| 必需指令资源不可用、不完整或不兼容 | 阻塞依赖判断，不推断政策、跳过守卫或读取作者源。 |

## 相关概念

- [工作流导航可用性](../layer-01-fundamental-concepts/workflow-navigation/navigation-availability_zh_cn.md)
- [工作流规则上下文](../layer-01-fundamental-concepts/workflow-navigation/rule-context_zh_cn.md)
- [运行环境能力清单](../layer-02-workflow-concepts/entry-and-context/environment-capability-inventory_zh_cn.md)

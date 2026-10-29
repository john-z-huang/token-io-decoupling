# Enhanced 路径选择

[English](enhanced-path-selection.md) | [简体中文](enhanced-path-selection_zh_cn.md)

本检查点负责针对当前任务选择是否使用可选 Enhanced 路径。

## 触发与输入

在 S02/M02，使用当前[环境](../layer-02-workflow-concepts/entry-and-context/environment_zh_cn.md)和[能力清单](../layer-02-workflow-concepts/entry-and-context/environment-capability-inventory_zh_cn.md)结果判断当前任务是否需要可选 Enhanced 操作。Enhanced 分支需要时，应用[Enhanced 工作流可用性](../layer-01-fundamental-concepts/enhanced-native-state/enhanced-workflow-availability_zh_cn.md)和[Enhanced Host 绑定](../layer-01-fundamental-concepts/enhanced-native-state/enhanced-host-binding_zh_cn.md)。

## 决策与结果

1. 将任务所需操作与当前环境及能力清单支持的可选 Enhanced 操作进行比较。
2. 若所需操作不需要 Enhanced state，记录 Native 和带理由的 `Not applicable`；继续时不得打开或初始化 Enhanced state。
3. 若需要 Enhanced 操作，核验当前 Session 符合可用性 owner 的资格条件、当前 host 身份可信且已绑定，并且每项必需 guard/能力均可用。保留各项核验的证据来源。
4. 若已核验所需操作、身份和守卫，则返回 `Enhanced eligible` 及这些证据；若存在缺失/未知要求则返回 `blocked`。路线后续的状态解决动作消费该结果；本选择本身不打开或初始化状态。

## 失败边界

| 结果 | 必需路线动作 |
| --- | --- |
| 无需 Enhanced 操作 | 继续 Native，并记录带理由的 `Not applicable`。 |
| 已核验 Enhanced 操作及资格、身份、守卫事实 | 返回证据供路线的状态解决动作使用；此处不得打开 state。 |
| 所需操作不明确，或身份、能力、资格、守卫未知/不可用 | 阻塞依赖 Enhanced 分支。保留 Native 候选；不得推断资格或初始化 state。 |

若既有 Enhanced 权威可能存在，Native 候选本身不能决定哪个后端为规范权威；路线的状态解决动作应按 reconciliation 和 authority-transfer owners 核验。

## 相关概念

- [Enhanced 工作流可用性](../layer-01-fundamental-concepts/enhanced-native-state/enhanced-workflow-availability_zh_cn.md)

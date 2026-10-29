# 工作流模块入口解析

[English](module-entry-resolution.md) | [简体中文](module-entry-resolution_zh_cn.md)

本检查点负责解析调用一个有界工作流模块时的就绪状态。它只处理调用方声明的要求；不选择或枚举模块、不定义 Layer-04 模块契约，也不调度路线。

## Trigger 和输入

调用方请求开始或恢复模块工作时使用。调用方提供任务和授权范围、适用且已释放的路线/模式证据、模块声明的前置 owners 与证据要求、当前 Session 状态、相关证据和 epoch、恢复时的暂停位置，以及先前效果的状态。首次直接调用可以没有 continuation 历史或顶层路线；当前调用方可在其可用上下文中建立 continuation。应用[工作流模块契约](../layer-01-fundamental-concepts/execution-planning/workflow-module-contract_zh_cn.md)，并应用相关的[Contract](../layer-02-workflow-concepts/entry-and-context/contract_zh_cn.md)、[Environment](../layer-02-workflow-concepts/entry-and-context/environment_zh_cn.md)、[能力清单](../layer-02-workflow-concepts/entry-and-context/environment-capability-inventory_zh_cn.md)、[Mode](../layer-02-workflow-concepts/entry-and-context/mode_zh_cn.md)及直接前置 owner。

## 决策与结果

1. 确认请求范围及适用模式当前有效且已获授权。已释放的 Mode 是待消费的证据，不是再次提问或更改路线的理由。不得重复已完成的提问或效果。
2. 只检查已声明的前置条件和调用方的暂停位置。根据直接 owner 核验来源、新鲜度、相关 epoch、必需能力及效果状态。若已授权的只读来源能够确认缺失证据，则只获取该有界证据并记录其来源。
3. 模块可以安全开始或恢复时，返回带有已核验证据、当前 epoch 和允许效果边界的 `ready`。`ready` 只是入口预检结果；模块仍须返回自身的 `complete`、带原因的 `not_applicable`、`needs_prerequisite` 或 `blocked`。尚未解决的 pending owner 结果不代表其依赖工作已就绪，也不能视为完成。就绪不超出调用方已有范围，也不表示模块或路线完成。
4. 必需证据缺失但尚不构成阻塞时，返回 `needs_prerequisite`，注明语义 owner、缺少的证据及暂停的模块/子步骤。调用方（包括没有顶层路线的直接调用方）决定从哪里恢复；本检查点不路由到模块或重启无关门禁。
5. 授权或模式冲突、必需能力/证据来源不可用、必需的 continuation 位置无法保留或找回、调用方状态矛盾、前置解析反复进行但没有新证据/相关 epoch 进展/有效 owner 状态变化，或通过已授权读回仍无法确认先前效果状态时，返回 `blocked`。首次进入时没有历史记录本身不构成阻塞。有证据或 epoch 推进时，可以继续 owner 要求的修复和重新验证。保留当前状态，不重试、重放或推断安全的后续操作。

## 失败边界

本检查点可以核验或取得已授权的只读证据。首次直接进入时，当前调用方可以建立 continuation 记录；本检查点不要求存在路线或外部持久化机制。不得创建或修改前置条件、扩展范围、重新选择 Mode、发起提问、创建 Agent、派发工作、执行 Git 操作或选择后续模块。建立前置条件所需的写操作仍必须具备已有授权，并通过调用方正常门禁返回。证据缺失或过期只阻塞依赖该证据的模块工作；不得因此跳过其声明的 owner。

## 相关概念

- [工作流模块契约](../layer-01-fundamental-concepts/execution-planning/workflow-module-contract_zh_cn.md)
- [Contract](../layer-02-workflow-concepts/entry-and-context/contract_zh_cn.md)
- [Environment 能力清单](../layer-02-workflow-concepts/entry-and-context/environment-capability-inventory_zh_cn.md)
- [Mode](../layer-02-workflow-concepts/entry-and-context/mode_zh_cn.md)

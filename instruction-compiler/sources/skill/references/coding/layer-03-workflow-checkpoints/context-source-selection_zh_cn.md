# 上下文来源选择

[English](context-source-selection.md) | [简体中文](context-source-selection_zh_cn.md)

本检查点负责路线级 active plan、有界规则查询、可复用项目记忆和持久交换上下文的选择与核验流程。

## 触发与输入

Session 已解决后，根据已验证事实和任务范围执行上下文来源选择。应用[Context](../layer-02-workflow-concepts/entry-and-context/context_zh_cn.md)、[Session Context Firewall](../layer-01-fundamental-concepts/session-runtime/session-context-firewall_zh_cn.md)、[项目 Memory 与代码结构能力](../layer-01-fundamental-concepts/session-runtime/LSP-MCP-Tools_zh_cn.md)、[工作流规则上下文](../layer-01-fundamental-concepts/workflow-navigation/rule-context_zh_cn.md)，并在触发条件成立时应用 context-exchange owners。

## 决策与结果

1. 定义当前最小 Context 问题、任务范围及可回答它的来源类别。应用 Context owner；不读取无关项目状态。
2. 始终列出 `plans/` 中本任务的活动计划 Memory，并读取每个匹配项。依据当前指令、任务匹配、来源指针和新鲜度核对每项；当前指令优先，计划不授予授权。无匹配活动计划时记录 `Not applicable` 和原因。若无法列出或读取相关活动计划，阻塞依赖工作；不得用文件替代该计划。
3. 若问题需要此前工作的可复用项目知识，列出项目 Memory 并读取相关项；对照权威项目文件核验来源指针和新鲜度。无相关项或无需跨会话知识时，记录 `Not applicable` 和原因。Memory 不可用时返回已批准的权威项目文件；仅当必需事实无法另行确认时阻塞。此回退适用于普通可复用项目知识，不适用于第 2 步必需的活动计划查询/读取。
4. 当前问题需要工作流指令时，按工作流规则上下文消费同一构建、语言的明确当前编译节点或单元，核验标识、完整性及未解决事实；在依赖动作前取得每个明确指令继续入口，保留准确返回位置。可选有界导航不需要时，记录 `Not applicable` 并消费对应已交付指令；可选导航不可用时，可由实际可用且获授权的同构建生成纯文档入口提供单元。必需资源缺失、损坏、不完整或不兼容时阻塞依赖判断，绝不查找作者 owner 或推断遗漏政策。
5. 应用 Session Context Firewall 限制来源范围和入口。需要 Worker memo 或 memo 派发时，应用[内容 Memo 派发](../layer-01-fundamental-concepts/context-exchange/content-memo-dispatch_zh_cn.md)及其[内容 Memo 生命周期](../layer-01-fundamental-concepts/context-exchange/content-memo-lifecycle_zh_cn.md)，核验必需的 Memory 能力与证据，作为之后获授权 Worker memo 派发的证据；未触发时记录 `Not applicable` 及原因。Worker 需要跨 Worker 交换/bootstrap 时，应用[工作流 Context Exchange](../layer-01-fundamental-concepts/context-exchange/context-exchange_zh_cn.md)及[工作区边界](../layer-01-fundamental-concepts/context-exchange/context-exchange-workspace-boundary_zh_cn.md)。仅在具体交接或恢复时应用[Context Exchange Handoff](../layer-01-fundamental-concepts/context-exchange/context-exchange-handoff_zh_cn.md)。按各自 owner 分别判断独立触发条件，并核验必需的持久 Memory 能力和证据。不得仅因收集 Context 而创建交换记录。必需的交换能力不可用时，阻塞依赖工作；owner 要求的持久记录不得回退为文件。
6. 返回带来源指针、来源溯源、新鲜度/epoch 及限制说明的最小当前事实。关键上下文过期、不完整或冲突时阻塞依赖决策。memo 适用性、同意和持久化仍由各自 owner 负责。

## 失败边界

关键上下文过期、不可访问或冲突时，阻塞依赖它的决策。不得扩大来源范围、从记忆推断授权或绕过必需 Memory 能力。

## 相关概念

- [Context](../layer-02-workflow-concepts/entry-and-context/context_zh_cn.md)

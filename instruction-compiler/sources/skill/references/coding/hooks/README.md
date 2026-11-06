# Coding Hook 契约


Agent 根据当前目标、上下文和证据选择执行。这些逻辑事件提供判断问题与反馈，不构成 Python 阶段机。读取共享契约、所选简短 workflow，以及当下适用的事件。

## 事件目录

| 事件 | 契约 | 问题 |
| --- | --- | --- |
| task_received | [任务接收](task-received.md) | 任务、限制、模式和能力是否充分明确？ |
| boundary_requested | [边界请求](boundary-requested.md) | 拟执行效果是否符合当前获准边界？ |
| action_observed | [动作观察](action-observed.md) | 实际发生什么，哪些证据失效？ |
| progress_reported | [进展反馈](progress-reported.md) | 继续、修订、补证据、等待或停止？ |
| completion_requested | [完成请求](completion-requested.md) | 当前结果是否支持 Agent 的验收声明？ |
| session_resumed | [会话恢复](session-resumed.md) | 哪些当前上下文和效果支持安全继续？ |

应用[共享约束](shared.md)，按已确认模式选择[单代理](../layer-04-workflows/coding-single-agent.md)或[多代理](../layer-04-workflows/coding-multi-agent.md)。各契约 JSON 围栏只声明机器输入/结果形状，判断语义以其正文为准。

## 交付与原生覆盖

实际暴露且获准时使用 workflow_check_event，或等价的批准生成文档。静态规则交付不需要模型/API/Memory/计划服务。可选语义建议须有自身明确配置和外发授权，其结果与输入结构及指令完整性分开。

逻辑事件不是原生 Hook 名称。原生适配器可提供受支持的 PreToolUse/PostToolUse/UserPromptSubmit/SessionStart 上下文或提示。已核对协议中 Stop/SubagentStop 没有 additionalContext：其缺省 systemMessage 提示不是模型注入契约，也不能证明已执行本逻辑检查或验收。Agent 最终声明前主动检查 completion_requested，重要返回时检查 progress_reported。明确的有界阻塞模式须另外验证真实宿主支持；不据此声称全局完成强制或持久重试计数。

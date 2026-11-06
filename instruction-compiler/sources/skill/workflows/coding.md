# Coding


本可选 workflow 用于获准代码、配置、指令或文档工作。通过 [task_received](../references/coding/hooks/task-received.md)确认当前目标、约束和验收，并应用[共享约束](../references/coding/hooks/shared.md)。

使用已确认[单代理](../references/coding/layer-04-workflows/coding-single-agent.md)或[多代理](../references/coding/layer-04-workflows/coding-multi-agent.md)指令。必要状态由 Agent 上下文维护，新任务不重置同 Session mode/count。动态选择当前动作，在实际边界使用[事件目录](../references/coding/hooks/README.md)。最终完成需要当前证据，而非走到编号序列末尾。

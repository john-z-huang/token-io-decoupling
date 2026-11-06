# 单代理 Coding


使用已确认 Single-Agent 模式：当前一个 Agent、零子级。Agent 在自身对话上下文维护决定、执行与证据；同上下文检查不是独立验证。

1. 读取[共享约束](../hooks/shared.md)，新/变更任务使用 [task_received](../hooks/task-received.md)，保留目标、范围、验收与当前事实。
2. 自主选择下一有界动作。跨越重要范围/效果边界前使用 [boundary_requested](../hooks/boundary-requested.md)，通过独立工具执行获准工作。
3. 真实结果/受影响 epoch 使用 [action_observed](../hooks/action-observed.md)，重要返回使用 [progress_reported](../hooks/progress-reported.md)。只修复已放行问题，重新验证变化覆盖；普通机械步骤留在当前 Slice。
4. 声明完成前主动使用 [completion_requested](../hooks/completion-requested.md)，执行当前必需检查，将每项适用标准映射到证据。请求的 Git/资源工作保留自身授权，不适用分支有证据理由。
5. 中断或上下文恢复时使用 [session_resumed](../hooks/session-resumed.md)，解决不明效果后继续待办，不重放；在宿主限制内如实报告完成、等待或阻塞。

这些必要依赖是给 Agent 的指令，不是编号运行阶段。Agent 根据当前事实选择路径，不使用 Python 阶段执行器、下一节点服务或 workflow 状态存储。

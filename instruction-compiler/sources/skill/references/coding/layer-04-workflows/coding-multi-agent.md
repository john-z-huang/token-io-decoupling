# 多代理 Coding


Root 规划、放行有界工作并最终验收。真实当前 Session 子级按已确认 mode/count、能力及用户分工执行任务。Root 与子级各自保留获准上下文，不要求 workflow 数据库或共享状态后端。

1. 对当前目标、范围、验收、能力及已有 allocation 事实应用[共享约束](../hooks/shared.md)和 [task_received](../hooks/task-received.md)。容量预留本身不创建子级。
2. Root 选择有界任务/执行者。放行、新建子级、改变范围或产生外部效果前使用 [boundary_requested](../hooks/boundary-requested.md)。核验身份、容量、职责、权限、可用性和返回条件；复用适任现有子级，忙时等待。
3. 只派发已放行快照。子级在范围内执行，仅向 Root 返回真实结果；独立不冲突工作可并行。Root 读取完整返回，用 [action_observed](../hooks/action-observed.md)核对效果/epoch。
4. 重要边界使用 [progress_reported](../hooks/progress-reported.md)。Root 继续有依据 Slice、先修改 Contract 再改变工作、补证据、等待或停止。窄修复返回当前状态执行所需验证；Bootstrap 或子级结果不是整体完成。
5. 最终声明前，Root 主动使用 [completion_requested](../hooks/completion-requested.md)，验证真实最终状态和必需独立性，映射当前标准/证据，只执行单独获准交付。
6. 上下文恢复时使用 [session_resumed](../hooks/session-resumed.md)。保留真实同 Session 身份/mode/count 和效果状态，不重建子级、回收容量或重放已完成效果，如实报告当前限制。

Agent 解释这些依赖并选择执行路径；Hook 判断和独立 MCP 方法辅助选择，Python 不遍历业务 DAG，也不保存运行游标。

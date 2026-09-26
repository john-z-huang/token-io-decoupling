# Coding 子 Agent 生命周期

[English](delegation-child-lifecycle.md) | [简体中文](delegation-child-lifecycle_zh_cn.md)

本文档负责已创建多代理子 Agent 的持久性和生命周期状态。它消费已由各自 owner 概念处理创建、分配和派发的子 Agent；不定义创建、职责分配、Dispatch Preview、Worker 边界、复用/替换或上下文传输。

## 通用规范

### 生命周期状态

在父级记录中持久保存每个已创建子 Agent 的身份和生命周期。运行环境存在持久任务面板时，不得仅为清理而关闭、shutdown、归档、删除或移除子 Agent。运行时状态界面是短暂的情形下，其条目消失后仍在父级记录保留子 Agent ID 和状态。pending 或 running 时只能等待或发送已授权输入。只有返回最终结果和证据后才能进入 completed。

### 错误与中断

发生错误或中断时，保留原子代理的身份、明确的生命周期状态与现有证据；未经授权不得以清理为由关闭它。同一子代理是否能够进行获准 follow-up，以及无法继续时如何处理，均由复用/替换 owner 决定；生命周期 owner 只记录结果状态和阻塞原因。不得从生命周期变化推断创建 successor 或回收 allocation 名额的权限。

## Codex CLI / ChatGPT Desktop 特别优化指令

Codex 也可通过已配置的 `SubagentStart`／`SubagentStop` Hooks 观察子代理 ID 与生命周期；在 `SubagentStart` 中返回 `continue: false` **不会**阻止创建。即使任务界面或 Hook 报告消失，仍要把实际子代理 ID 与完成证据保留在父级记录中。这些事件只用于观察，不授权替换，也不能证明验证通过。[OpenAI：生命周期 Hooks](https://learn.chatgpt.com/docs/hooks)。

### Codex 线程观察

当前 Agent Session 暴露 `/agent` 或直接的子代理状态／结果工具时，才通过该工具获取执行中工作和返回摘要，避免把完整 transcript 输入父级上下文。Desktop Codex 线程／活动面板属于面向用户的 GUI；不得通过 Computer Use 读取，也不能在没有会话工具时声称 Agent 可访问。非当前 CLI Child 的审批请求可能出现在现有线程上方，并标明来源线程；核对其身份与操作授权后才能处理。非交互宿主不能提供新的审批时，操作会失败，父级必须记录 Slice 阻塞。`SubagentStop` Hook 只提供观察；Done 标记或空白活动面板都不能取代最终证据，也不授权清理／替换。[OpenAI：子代理线程与审批](https://learn.chatgpt.com/docs/agent-configuration/subagents)、[OpenAI：Hooks](https://learn.chatgpt.com/docs/hooks)。

## Claude Code CLI / Claude Desktop 特别优化指令

可用时通过 `Agent` 结果和 `/tasks` 观察运行中的子代理；以有界运行时等待取得结果。`/tasks` 是短暂状态界面，其条目消失后仍在父级记录保留返回的 Agent ID 和完成或错误状态。

### 事件辅助观察

实际暴露 Hooks 的 Claude Code Session 中，可选 `SubagentStart` Hook 用于记录事件提供的 `agent_id`/`agent_type`；可选 `SubagentStop` Hook 可读取 `agent_id`、`agent_transcript_path` 和 `last_assistant_message`，无需把完整 transcript 塞入父级上下文。必须与实际 `Agent` 结果和父级状态记录交叉核对；单个 Hook 事件既不证明成功完成，也不授予关闭、替换或创建子代理的权限。失败和部分输出应单独记录。`/tasks` 只是便捷视图而非持久事实源，条目消失后仍要保留 ID 和证据。只有实际 Claude Code Runtime 才能依赖这些 Hooks，不假定 Desktop Chat 或 Cowork 具有相同功能。

官方依据：[SubagentStart/SubagentStop 事件字段](https://code.claude.com/docs/en/hooks)、[子代理生命周期与恢复](https://code.claude.com/docs/en/sub-agents)。

达到 `maxTurns`、`Agent` 调用失败或返回未完成／后台部分结果时，父级核实实际输出与返回条件前均按部分完成或中断处理；`/tasks` 条目消失不构成完成证据。[Anthropic：子代理执行限制](https://code.claude.com/docs/en/sub-agents)。

## 相关概念

- [Coding Child Creation](delegation-child-creation_zh_cn.md) — 定位子 Agent 创建能力。
- [Coding Child Role Allocation](delegation-child-role-allocation_zh_cn.md) — 定位名额和职责分配。
- [Coding Child Dispatch](delegation-child-dispatch_zh_cn.md) — 定位 Dispatch Preview 和 Worker 边界。
- [Coding Child Reuse and Replacement](delegation-child-reuse-replacement_zh_cn.md) — 定位获准修复和替换关系。
- [Coding Context Exchange](context-exchange_zh_cn.md) — 定位上下文传输归属。

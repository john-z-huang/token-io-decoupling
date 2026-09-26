# Coding 子 Agent 派发

[English](delegation-child-dispatch.md) | [简体中文](delegation-child-dispatch_zh_cn.md)

本文档负责实际派发前的 Dispatch Preview 和 Worker 边界。它消费已获授权的子 Agent 和 slice；不定义子 Agent 创建、职责分配、复用或替换、生命周期或 Interaction Slice 字段。

## 通用规范

### Dispatch Preview 和返回边界

分配或实质派发前，检查输入侧推理职责已完成指令、环境和定义任务所需代码事实的前置确认，具有 source pointer，且具体 Interaction Slice 已放行。父级展示获准目标、修改和返回条件的简洁 Dispatch Preview；前置条件缺失时仍由父级持有 Slice。Worker 只向直接父级返回，不得创建、fork、handoff、向其他 Agent 或 Session 发消息、替换或协调其他 Agent 或 Session，也不得联系任意线程。与已确认前提冲突的发现返回父级重新决策，不得改变模式或数量。

### Named path 和 slice 放行

通过[上下文工作区边界](context-exchange-workspace-boundary_zh_cn.md)核验各 Worker 的目录与具名权限；通过[执行控制](execution-control_zh_cn.md)消费获准的 Interaction Slice，一次只派发一个 Slice，除非明确允许相互独立且不冲突的并行工作。本模块不重新定义目录布局或 Slice 字段。

## Codex CLI / ChatGPT Desktop 特别优化指令

目前没有针对该厂商的特别优化指令；遵循上述通用规范。

## Claude Code CLI / Claude Desktop 特别优化指令

目前没有针对该厂商的特别优化指令；遵循上述通用规范。

### 派发前工具门禁

本地已配置 Claude Code 的宿主中，获准的 `PreToolUse` Hook 可匹配 `Agent`，在调用执行**之前**检查父级记录是否具备预留名额、已放行 Slice 和获准返回路径；缺少时通过显式 deny 阻止创建。不得依赖创建之后才触发且不能 veto 的 `SubagentStart`。必须在 `Agent` 工具调用**之前**在父级会话展示人类可读的 Dispatch Preview；Hook 本身不能证明父级已审核或展示该预览。守卫脚本必须读取真实状态记录，授权缺失时拒绝执行，不记录密钥或完整提示词。未安装经过审查的 Hook 时，派发前语义检查仍然是强制要求。

官方依据：[PreToolUse 与 SubagentStart 语义](https://code.claude.com/docs/en/hooks)。

## 相关概念

- [Coding Child Creation](delegation-child-creation_zh_cn.md) — 定位子 Agent 创建能力。
- [Coding Child Role Allocation](delegation-child-role-allocation_zh_cn.md) — 定位名额和职责分配。
- [Coding Child Lifecycle](delegation-child-lifecycle_zh_cn.md) — 定位子 Agent 状态和恢复归属。
- [Coding Child Reuse and Replacement](delegation-child-reuse-replacement_zh_cn.md) — 定位获准的复用和替换。
- [Coding Context Exchange](context-exchange_zh_cn.md) — 定位 named-path 上下文传输归属。
- [Coding Execution Control](execution-control_zh_cn.md) — 定位 Interaction Slice 边界控制。

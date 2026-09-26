# Coding 子 Agent 复用与替换

[English](delegation-child-reuse-replacement.md) | [简体中文](delegation-child-reuse-replacement_zh_cn.md)

本文档负责已创建子 Agent 的获准 follow-up、修复 epoch 以及复用或替换关系。不定义子 Agent 创建、职责分配、Dispatch Preview、Worker 边界、生命周期状态或上下文传输。

## 通用规范

### 获准复用

对已授权 follow-up、修复 epoch 和中断，在安全时复用同一个已创建子代理。优先通过该子代理尝试获准修复；无法安全继续时报告阻塞，并将依赖的 Multi-Agent 工作置为 `blocked`。复用不得创建递归层级或 peer 协调。已创建子代理的身份和证据遵循生命周期 owner 保留。

### 替换关系

数量锁定后、名额中的子代理创建前，允许父级授权修改 `agent: unbound` 的预留 allocation 计划；只能在锁定预算内调整未绑定职责或待放行 Slice。数量尚未锁定时，awaiting-count 记录不存在可替换的 allocation。已创建子代理的名额不得回收；数量锁定后不得再创建额外或替代子代理。不得重复询问数量、fork 或 handoff 给新子代理。上下文交接由[上下文交换交接](context-exchange-handoff_zh_cn.md)拥有，不授予创建 Agent 的能力。

## Codex CLI / ChatGPT Desktop 特别优化指令

### 复用已分配的 Codex 线程

宿主提供父级可控的 steering 或能够向已记录 Codex 子线程 follow-up 时，必须对**同一身份**发起获准的修复或后续 epoch。当前 Session 暴露的 `/agent` 或直接子线程工具可定位已记录身份。通过暴露工具返回的不同 Session 或 worktree 不足以证明与已分配 Child 身份连续。请求新的 subagent 会产生不同身份，在数量锁定后不得伪装为复用。原线程无法通过暴露工具继续或 steering 失败时，保留证据并阻塞依赖 Multi-Agent Slice。[OpenAI：子代理编排与线程控制](https://learn.chatgpt.com/docs/agent-configuration/subagents)、[OpenAI：worktree 行为](https://learn.chatgpt.com/docs/environments/git-worktrees)。

## Claude Code CLI / Claude Desktop 特别优化指令

获准跟进或修复同一子代理时，使用返回的 Agent ID 调用 `SendMessage`。再次调用 `Agent` 会创建另一个子代理并消耗另一个名额；数量锁定后不得将其用于复用。

### 恢复同一身份，不重新创建

获准的持久 `general-purpose` 或自定义子代理，应通过 `SendMessage` 指定返回的 `agent_id`（或运行时支持的 Agent 名称），发送范围明确的修复/follow-up 指令。新的 `Agent` 调用即使类型与提示词相同，也会产生不同实例；数量锁定后不得暗中用它替换原子代理。内置 `Explore` 和 `Plan` 是一次性 Agent，不返回可恢复 ID，不得用于需要后续 follow-up 的名额。恢复失败时保留错误并阻塞依赖工作，不再尝试创建另一子代理。除非 Claude Desktop 连接器工具结果明确返回父级控制的该身份关系，否则连接器调用不能代替向已记录 Agent 身份发送 `SendMessage`。

官方依据：[恢复子代理](https://code.claude.com/docs/en/sub-agents)。

Agent team 消息或 `/branch` 都不能替代恢复已记录的 Agent 身份。原子代理 ID 不可继续时，保留其证据并阻塞依赖 Slice，不得消耗未经批准的替代名额。[Anthropic：子代理恢复](https://code.claude.com/docs/en/sub-agents)。

## 相关概念

- [Coding Child Creation](delegation-child-creation_zh_cn.md) — 定位子 Agent 创建能力。
- [Coding Child Role Allocation](delegation-child-role-allocation_zh_cn.md) — 定位名额和职责分配。
- [Coding Child Dispatch](delegation-child-dispatch_zh_cn.md) — 定位实际派发边界。
- [Coding Child Lifecycle](delegation-child-lifecycle_zh_cn.md) — 定位子 Agent 状态和恢复归属。
- [Coding Context Exchange](context-exchange_zh_cn.md) — 定位 handoff 和上下文传输归属。

# Coding 子 Agent 职责分配

[English](delegation-child-role-allocation.md) | [简体中文](delegation-child-role-allocation_zh_cn.md)

本文档负责在 Multi-Agent count 已 locked 时进行名额和辅助职责分配。不定义子 Agent 创建、Dispatch Preview、Worker 边界、复用或替换、生命周期、上下文传输、验证或 Git 策略。

## 通用规范

### 职责分配

父级完成有界事实确认后，只能在已锁定和预留的数量预算内分配职责。预留名额在用途未确定前可以保持 `role: unassigned`；创建子代理前必须分配并放行其职责。只有一个子代理时，将其分配给 Primary Output。Primary Output、Change Verification、Documentation/Comments & Git Operations、Context Bootstrap/Refresh 及其他独立职责各自消耗一个名额。获准修改未绑定名额的计划不属于创建替代子代理，不得突破预算；创建后子代理身份保持绑定。未分配独立 verifier 或辅助职责时，安全情况下可使用当前或已分配 Agent，否则报告不可用；不得通过改名将同一 Session 的工作冒充独立验证。

### Context Bootstrap/Refresh 分配

仅当复用可能比设置成本更有利时分配 Context Bootstrap/Refresh：至少两个独立下游 Worker、广泛侦察加三个或更多路由策略模块，或来源集合大致超过 20k 字符 / 5k token-equivalents。单个小 Worker 或仅文档快速路径应跳过。这里的数值是路由启发式，不是运行时或质量测量结论。

## Codex CLI / ChatGPT Desktop 特别优化指令

Codex 的 `.codex/agents/*.toml` profile 可以命名计划职责，但注册 profile 不能创建 Agent 或改变预留名额中的子代理身份。必须在已锁定预算内选择角色及实际生效的 `model`／`model_reasoning_effort`／`sandbox_mode`；可配置的全局并发 Agent 上限与本 Skill 的总数量门禁不同。[OpenAI：自定义子代理](https://learn.chatgpt.com/docs/agent-configuration/subagents)。

## Claude Code CLI / Claude Desktop 特别优化指令

Claude Code 可以利用 `.claude/agents/` 或 `~/.claude/agents/` 中自定义 subagent 的 `description`、`tools`、`model`、`effort` 细化**计划中的**职责；定义或发现文件不会创建 Agent 实例，也不会额外消耗锁定名额。先将可复用职责分配至已有名额，之后才由创建 owner 调用 `Agent`。内置 Explore／Plan 为一次性 Agent，不应被分配为需要持久身份的 Primary Output、verifier 或 follow-up 职责。即使宿主暴露额外内置 Agent，也不能改变已锁定数量。[Anthropic：subagent 作用域与一次性 Agent](https://code.claude.com/docs/en/sub-agents)。

## 相关概念

- [Coding Child Creation](delegation-child-creation_zh_cn.md) — 定位子 Agent 创建归属。
- [Coding Child Dispatch](delegation-child-dispatch_zh_cn.md) — 定位实际派发边界。
- [Coding Child Lifecycle](delegation-child-lifecycle_zh_cn.md) — 定位子 Agent 状态归属。
- [Coding Child Reuse and Replacement](delegation-child-reuse-replacement_zh_cn.md) — 定位获准的复用和替换。
- [Coding Context Exchange](context-exchange_zh_cn.md) — 定位上下文传输归属。

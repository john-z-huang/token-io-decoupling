# Coding 子 Agent 创建

[English](delegation-child-creation.md) | [简体中文](delegation-child-creation_zh_cn.md)

本文档负责创建 Multi-Agent 子 Agent 的唯一能力入口。入口要求是：已 release 的 Multi-Agent 状态、已锁定的正整数 `child_count`，以及恰好等于 `child_count` 个已锁定的计划 allocation；每个计划 allocation 在创建前都可以是 `agent: unbound`。它不重新打开 mode 或 count 确认。数量锁定前的计划级 replacement 不属于创建能力，不能创建子 Agent 或消耗子 Agent 名额。创建成功后，由本 owner 将每个已创建的 agent identity 和实际 lifecycle 回写到计划 allocation；不改变 mode 或 count，也不创建额外名额。它不定义职责分配、Dispatch Preview、Worker 边界、复用或替换，或生命周期。

## 通用规范

### 创建能力

使用运行环境真实且由父级控制的子代理机制。不得把 peer chat 或无法跟踪的通用任务当作持久子代理。必须具备子代理身份、父级控制的返回/继续路径、有界等待和可观察生命周期。创建后将实际身份和生命周期绑定到计划 allocation。能力缺失或无法核实时阻塞创建，不更改模式或数量。

## Codex CLI / ChatGPT Desktop 特别优化指令

本地 Codex 使用当前暴露的 MultiAgentV1/V2 spawn 操作；模型与能力绑定遵循[运行环境与模型厂商支持](runtime-provider-support_zh_cn.md)。

## Claude Code CLI / Claude Desktop 特别优化指令

本地 Claude Code 在数量和 allocation 放行后使用内建 `Agent` 工具，显式指定 `subagent_type`（`general-purpose` 或已命名自定义子代理）、合规模型、有界任务提示和返回条件。模型与 effort 绑定遵循[运行环境与模型厂商支持](runtime-provider-support_zh_cn.md)；可用时在 `/tasks` 核验实际模型，因为被禁模型可能回退到继承模型。内建 Explore/Plan Agent 不返回可复用 Agent ID，不得作为持久子代理。

通用 `Agent` 调用没有逐次 effort 参数。需要 Sonnet 职责专属 effort 时，使用获准的 `.claude/agents/<name>.md` 或 `~/.claude/agents/<name>.md` 定义，填写 `name`、`description`、`model: sonnet`、必需的 `effort` 和适当的工具白名单。否则在启动前显式设置并核验子代理继承的会话 `/effort`；Haiku 省略 effort。优先使用工具白名单中排除 `Agent` 和 peer 消息的具名可复用子代理，防止递归委派。自定义定义不在获准修改范围内时，只有在能核验实际 effort 和工具边界时才使用 `general-purpose`。必需的绑定或边界无法核实时阻塞该子代理职责。

## 相关概念

- [Coding Child Lifecycle](delegation-child-lifecycle_zh_cn.md) — 定位子 Agent 状态归属。
- [Coding Child Role Allocation](delegation-child-role-allocation_zh_cn.md) — 定位名额和职责分配。
- [Coding Child Dispatch](delegation-child-dispatch_zh_cn.md) — 定位实际派发边界。
- [Coding Child Reuse and Replacement](delegation-child-reuse-replacement_zh_cn.md) — 定位获准的复用和替换。
- [Coding Session Model](session-model_zh_cn.md) — 定位 role 和 Session 归属。
- [Coding Context Exchange](context-exchange_zh_cn.md) — 定位必要的上下文传输归属。

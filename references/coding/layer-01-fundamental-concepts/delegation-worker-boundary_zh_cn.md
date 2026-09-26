# Coding 委派 Worker 边界

[English](delegation-worker-boundary.md) | [简体中文](delegation-worker-boundary_zh_cn.md)

本文档负责已放行的 Worker 快照、Worker 读写边界、父级控制的 Dispatch 进入路径，以及任务控制记录无法持久化或返回时的阻断。它消费[委派状态记录](delegation-state-record_zh_cn.md)定义的记录；不定义记录结构、模式/数量策略、子 Agent 生命周期或 Dispatch Preview 策略。

## 通用规范

### Worker 快照和访问边界

Worker 只能通过父级控制的 Dispatch 接收相关的已放行快照。不得推断、修改或替换根记录。Worker 只能在已放行范围内使用快照，并通过父级控制的路径返回所需事实。

### Dispatch 进入和持久化阻断

放行后，Worker 通过父级提供的 Dispatch Preview 进入，不重新打开根用户模式或数量门禁。运行时无法持久化或返回任务控制记录时，依赖该记录的路线被阻塞。

## Codex CLI / ChatGPT Desktop 特别优化指令

目前没有针对该厂商的特别优化指令；遵循上述通用规范。

## Claude Code CLI / Claude Desktop 特别优化指令

目前没有针对该厂商的特别优化指令；遵循上述通用规范。

### Worker 工具范围

对获准的 Claude Code 自定义 Worker，用 frontmatter `tools` 白名单和/或 `disallowedTools` 排除 `Agent` 及 peer messaging 工具。当前 Claude Code 中，Worker 具有 `Agent` 工具时可能继续创建嵌套子代理；纯文字禁止并不等于工具层边界。需要 MCP 时，只授予必需 Server/Tool，使用受支持的 `mcp__<server>` 模式禁止无关 MCP 工具；这限制的是工具可用性，不改变父级状态记录的所有权。项目/个人 Agent 定义可使用 `mcpServers` 限定范围，但插件自带 Agent 的该 frontmatter 字段会被忽略。不得假定 Desktop Chat 已安装同样的限制。

官方依据：[子代理工具、disallowedTools 与 MCP 范围](https://code.claude.com/docs/en/sub-agents)。

## 相关概念

- [Coding Delegation State Record](delegation-state-record_zh_cn.md) — 定位记录 ownership 和字段约束。
- [Coding Child Dispatch](delegation-child-dispatch_zh_cn.md) — 定位 Worker 派发边界。
- [Coding Execution Control](execution-control_zh_cn.md) — 定位已放行 Interaction Slice 边界。
- [Coding Context Exchange](context-exchange_zh_cn.md) — 定位命名上下文传输归属。

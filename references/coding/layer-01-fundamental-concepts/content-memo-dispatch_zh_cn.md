# Worker Content Memo Dispatch

[English](content-memo-dispatch.md) | [简体中文](content-memo-dispatch_zh_cn.md)

本文档只定义父 Agent 控制的 Worker 文件化执行 memo `write_content_memo` dispatch 开关。不定义 memo 内容、memo 生命周期、上下文传输或子 Agent 生命周期。

## 通用规范

### Dispatch 开关

父 Agent 使用：

```text
write_content_memo: true
```

省略该字段时也按 `true` 处理。它为当前 dispatch 启用文件化 memo。`false` 只关闭文件化 memo，且仅适用于 memo 成本明显高于预期复用、恢复或 handoff 价值的情况。

内部派发配置可以省略字段并使用上述 `true` 默认值。但在父级序列化 released task bundle 前，必须显式写出 `write_content_memo: true` 或 `write_content_memo: false`。Worker 只消费其 released bundle 中的显式值；如果 released bundle 省略该字段，则派发不完整，Worker 不得自行推断默认值。

### 父级授权

Worker 不得修改或重新解释该开关；只有父 Agent 可以为后续 slice 选择取值。该授权只控制 memo 文件是否物化，不授予其他范围或 capability。

## Codex CLI / ChatGPT Desktop 特别优化指令

Codex 自定义 Agent TOML、`AGENTS.md`、可选 memories 和 `/compact` 都不会实现本 Skill 的派发开关。spawn 前必须在**实际放行的子任务提示**中显式写明 `write_content_memo: true` 或 `false`，并指定获准的 memo 路径。启用时核验父 Agent 已在指定的获准绝对路径创建 memo 目录，且接收任务的 Worker Session 在批准的 RW 边界内确实具有该路径的写入能力。若 Worker 使用独立 checkout，还须单独核验 Primary Worktree 下的 `CONTEXT_ROOT` 是否可达；不得将 memo 擅自迁入 Worker checkout，也不得根据 checkout 归属推断访问权限。权威目录布局与路径权限由[Context Exchange Workspace Boundary](context-exchange-workspace-boundary_zh_cn.md)负责。`SubagentStart` 或 `PreCompact` Hook 是可选上下文，不能代替显式 bundle 或 Worker 真正写入的文件。[OpenAI：子代理提示](https://learn.chatgpt.com/docs/agent-configuration/subagents)、[OpenAI：本地 memories](https://learn.chatgpt.com/docs/customization/memories)、[OpenAI：Hooks](https://learn.chatgpt.com/docs/hooks)。

## Claude Code CLI / Claude Desktop 特别优化指令

Claude Code 的 `Agent` 提示与自定义 subagent 配置不会自动实现本 Skill 的 `write_content_memo` 开关。调用已获准的 Worker 前，必须在其已放行任务 bundle 中显式序列化 `write_content_memo: true` 或 `false`；开启时核验可写 memo 目录已准备好。不得依赖 `Agent` 的隐式默认值、`SubagentStop` Hook 或父级 auto memory 自动产生文件化 memo。关闭时只跳过 memo 写入，仍需返回独立要求的执行证据。[Anthropic：子代理配置](https://code.claude.com/docs/en/sub-agents)、[Anthropic：memory](https://code.claude.com/docs/en/memory)。

## 相关概念

- [Worker Content Memo](content-memo_zh_cn.md) — 定位 memo 内容契约。
- [Worker Content Memo Lifecycle](content-memo-lifecycle_zh_cn.md) — 定位 memo 生命周期规则。

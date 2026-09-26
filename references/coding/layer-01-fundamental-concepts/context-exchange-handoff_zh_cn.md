# Coding Context Exchange Handoff

[English](context-exchange-handoff.md) | [简体中文](context-exchange-handoff_zh_cn.md)

本文档负责 Worker-local context index、上下文实质更新、handoff 和 replacement-state 记录以及 successor 暴露。它只记录已获准 handoff 的上下文传输；不授权子 Agent 复用或替换，不定义 capsule 内容或工作区 capability。

## 通用规范

### Worker-local 上下文记录

每个 Worker-local `INDEX.md` 只记录 task、scope、status、最近一次实质更新、各文档用途以及 blocker 或 handoff 目标。只有能提供不同复用价值时才增加专项文档。上下文文件只在状态、证据或 handoff 实质变化时更新，不要每条命令都写记录。

### Handoff 和 successor 暴露

只有已获授权的上下文交接才能为接收方分配新的 Context ID 和目录；Context ID 本身不授予创建或替换 Agent 的权限。接收方仅能读取父级明确暴露的前任文档，永远不得写入前任目录。交接优先引用已有[执行 memo](content-memo_zh_cn.md) 中准确的稳定事实，而不另造重复状态副本；若 memo 已关闭或缺失，则直接记录交接必需的最小事实：已完成状态、失败方案与证据、当前修改和验证状态、阻塞以及下一步动作。父级更新根索引，明确来源路径并只暴露点名文档；前任不可用时不得重建完整 transcript。

## Codex CLI / ChatGPT Desktop 特别优化指令

Desktop Codex 的 `Handoff` 在 Local 与 Codex 管理的 Worktree 间转移的是**同一个 chat**；它不是本 Skill 的跨 Worker context handoff，不会自动把具名 capsule 送给其他已分配 Agent。真正的 Worker 交接必须使用父级获准的来源／import 路径并记录接收 Child 身份。归档的 chat 或已清理的管理型 worktree 可能需要恢复保存的 snapshot，因此依赖旧导出文件前先核验来源新鲜度。[OpenAI：worktree Handoff 与清理](https://learn.chatgpt.com/docs/environments/git-worktrees)。

## Claude Code CLI / Claude Desktop 特别优化指令

Claude Code 原子代理仍有可恢复 Agent ID 时，优先通过获准的 `SendMessage` follow-up 与具名只读来源指针继续，不新建子代理，也不复制 transcript。原子代理无法继续时，只能把经父级批准的交接文档与当前来源证据交给**已经获授权**的接收方；恢复父 Session 的 `/resume`、`/branch` 或新的 Desktop Code 面板本身都不授权替换子代理。本地 MCP Desktop Extension 可以向 Desktop Chat 暴露获准文档，但不会因此创建共享的 Worker 生命周期。[Anthropic：子代理恢复](https://code.claude.com/docs/en/sub-agents)、[Anthropic：Desktop Session](https://code.claude.com/docs/en/desktop)。

## 相关概念

- [Coding Context Exchange](context-exchange_zh_cn.md) — 定位 capsule 和 freshness 归属。
- [Coding Context Exchange Workspace Boundary](context-exchange-workspace-boundary_zh_cn.md) — 定位目录和 capability 边界。
- [Coding Session Context Firewall](session-context-firewall_zh_cn.md) — 定位原始状态进入归属。
- [Coding Child Reuse and Replacement](delegation-child-reuse-replacement_zh_cn.md) — 定位复用和替换授权归属。
- [Coding Child Lifecycle](delegation-child-lifecycle_zh_cn.md) — 定位子 Agent 状态和恢复归属。

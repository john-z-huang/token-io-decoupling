# Worker Content Memo Dispatch

[English](content-memo-dispatch.md) | [简体中文](content-memo-dispatch_zh_cn.md)

本文档定义父 Agent 控制的 Serena Memory Worker memo 开关 `write_content_memo`，不定义 memo 内容或生命周期。

## 通用规范

### Dispatch 开关

每个已放行 bundle 都必须显式包含 `write_content_memo: true` 或 `false`；Worker 不得自行推断默认值。`true` 启用对 `context-exchange/workers/<worker-context-id>/content-memo` 的写入；`false` 只关闭该 memo。已放行 bundle 中须包含准确 Memory 名称。父级控制开关和名称，但这只是逻辑归属：Serena 不强制 Worker 级访问或只读 ACL。

Memory 工具未暴露或未获授权时，报告限制并阻塞依赖 memo 的切片；不得把 memo 物化为文件。其他独立工作可以继续。

## Codex CLI / ChatGPT Desktop 特别优化指令

在实际放行的子任务提示中序列化开关和准确 Memory 名称。只使用实际暴露且获准的 Serena Memory 工具，并确认写入结果。Codex 配置、Hooks、本地 Memory 或 compaction 本身均不实现此开关。

## Claude Code CLI / Claude Desktop 特别优化指令

当前 Agent Session 暴露且授权 Serena MCP Memory 工具时，在已放行 bundle 中包含开关和名称，并确认写入结果。Claude auto memory、Hooks 或 compaction 不能代替具名项目 Memory。工具不可用时按通用阻塞/报告规则处理。

## 相关概念

- [Worker Content Memo](content-memo_zh_cn.md) — 定位 memo 内容契约。
- [Worker Content Memo Lifecycle](content-memo-lifecycle_zh_cn.md) — 定位更新规则。
- [Coding Context Exchange Workspace Boundary](context-exchange-workspace-boundary_zh_cn.md) — 定位 Memory 逻辑归属规则。

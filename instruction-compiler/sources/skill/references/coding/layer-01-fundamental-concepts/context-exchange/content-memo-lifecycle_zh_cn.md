# Worker Content Memo Lifecycle

[English](content-memo-lifecycle.md) | [简体中文](content-memo-lifecycle_zh_cn.md)

本文档定义 Serena Memory Worker memo 的创建、更新、清理和可发现性，不定义 memo 内容、dispatch、handoff 授权或验收。

## 通用规范

### 创建、更新与发现

`write_content_memo` 为 true 时，使用 `list_memories` 检查具名条目，并在首次出现可复用状态以及实质里程碑、阻塞、handoff、replacement 或正常退出时，使用 `write_memory` 创建或更新 `context-exchange/workers/<worker-context-id>/content-memo`。只在状态/证据实质变化时更新，不要逐命令记录。父级或后继者只有在已放行指令具名或授权该记录时才能读取；Serena 本身不强制该归属规则。这些记录不另建本地文件索引；名称可通过 Serena Memory 列表发现。

Memory 能力失败时必须报告，并阻塞依赖该记录的工作；不得回退为文件写入。遵守 memo 内容契约，不得写成命令日志。

## Codex CLI / ChatGPT Desktop 特别优化指令

Hooks 可以提示 compaction 或退出边界，但不会写入或验证具名 Memory。使用实际暴露且获准的 Serena 工具并确认写入结果；除非父级明确授权该记录，否则不得写入其他 Worker 的 Memory 名称。

## Claude Code CLI / Claude Desktop 特别优化指令

仅在 Serena MCP Memory 工具暴露且获准时使用具名 Memory，并核验写入结果。Hooks 或 auto memory 不能替代该记录。工具不可用时，报告限制并阻塞依赖工作。

## 相关概念

- [Worker Content Memo](content-memo_zh_cn.md) — 定位 memo 内容契约。
- [Worker Content Memo Dispatch](content-memo-dispatch_zh_cn.md) — 定位 memo 开关。

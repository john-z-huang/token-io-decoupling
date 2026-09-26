# Worker Content Memo Lifecycle

[English](content-memo-lifecycle.md) | [简体中文](content-memo-lifecycle_zh_cn.md)

本文档只定义 Worker 文件化执行 memo 的创建、更新、清理和本地索引可发现性。不定义 memo 内容、dispatch 开关、handoff 或 replacement 策略，也不定义任务验收。

## 通用规范

### 创建与更新

在首次出现可复用执行状态，以及实质里程碑、阻塞边界、handoff、replacement 或正常退出时，创建或更新 `content-memo.md`，或一个已被明确标识为 memo 的等价既有文档。

### 清理与可发现性

清理和压缩必须遵守 `content-memo.md` 内容契约，不得把 memo 写成命令日志。Memo 必须能从 Worker 的本地索引定位。

## Codex CLI / ChatGPT Desktop 特别优化指令

目前没有针对该厂商的特别优化指令；遵循上述通用规范。

## Claude Code CLI / Claude Desktop 特别优化指令

目前没有针对该厂商的特别优化指令；遵循上述通用规范。

### 压缩与退出时的 Memo 检查点

本地 Claude Code 已配置 Hooks 且 `write_content_memo: true` 时，可选 `PreCompact` Hook 可在压缩**之前**识别压缩事件并检查现有、获准的 Memo/索引是否最新；不可假定该 Hook 能提醒 Agent 生成新状态；`SubagentStop` 可以把末条回复提供给父级以核对 Memo/索引。这些事件信号本身不会自动写出正确 Memo，把整个 transcript 复制进去也违反 Memo 内容契约。无论是否装有 Hook，均须在普通实质性里程碑维护 Memo，并在 Worker Index 保留准确具名路径；Memo 明确关闭时不得执行该 Hook 工作流。Hooks 的脚本必须在实际 Claude Code Session 中可用且获信任；不得推断 Desktop Chat/Cowork 会运行它们。

官方依据：[PreCompact 与 SubagentStop Hooks](https://code.claude.com/docs/en/hooks)。

## 相关概念

- [Worker Content Memo](content-memo_zh_cn.md) — 定位 memo 内容契约。
- [Worker Content Memo Dispatch](content-memo-dispatch_zh_cn.md) — 定位 memo dispatch 开关。

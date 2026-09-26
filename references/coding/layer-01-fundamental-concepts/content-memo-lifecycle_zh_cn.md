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

## 相关概念

- [Worker Content Memo](content-memo_zh_cn.md) — 定位 memo 内容契约。
- [Worker Content Memo Dispatch](content-memo-dispatch_zh_cn.md) — 定位 memo dispatch 开关。

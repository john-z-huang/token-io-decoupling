# Worker Content Memo

[English](content-memo.md) | [简体中文](content-memo_zh_cn.md)

本文档只定义 Worker 文件化执行 memo 的可复用内容契约：用途、语言与格式规则、可记录状态和禁止材料。不定义 dispatch 开关或 memo 生命周期。

## 通用规范

### 用途与语言

Memo 是用于保存稳定、可复用事实的精简执行状态文档。Worker 编写的上下文 prose 使用**中文**。路径、文件名、命令、symbol、key、hash、准确错误文本和日志片段保持原文。机械复制的源文档保留来源语言和内容。本规则不改变代码注释、commit、Issue/PR、README、产品文档或用户消息的语言。

### 可记录状态

使用 `content-memo.md`，或使用一个已被明确标识为 memo 的等价既有文档。只记录稳定、可复用的状态：

- 已完成结果和相关发现；
- 变更路径或 symbol；
- 验证状态和准确证据指针；
- 可避免重复的失败方案；
- 剩余工作、阻塞或 handoff 需求。

### 禁止材料

不要写成逐命令日志，也不要记录完整日志、完整 diff、大段源码副本、秘密、私有推理或无关历史。

## Codex CLI / ChatGPT Desktop 特别优化指令

目前没有针对该厂商的特别优化指令；遵循上述通用规范。

## Claude Code CLI / Claude Desktop 特别优化指令

目前没有针对该厂商的特别优化指令；遵循上述通用规范。

## 相关概念

- [Worker Content Memo Dispatch](content-memo-dispatch_zh_cn.md) — 定位 memo dispatch 开关。
- [Worker Content Memo Lifecycle](content-memo-lifecycle_zh_cn.md) — 定位 memo 生命周期规则。

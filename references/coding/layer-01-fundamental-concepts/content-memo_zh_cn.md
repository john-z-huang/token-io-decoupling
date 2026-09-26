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

Codex 本地 memories（启用时）总结跨会话可复用经验，`/compact` 则压缩单个 chat 的上下文。两者都不能保证当前获准 Slice 的 Worker 自有 memo 已更新，也不会自行满足来源 hash、修改路径或下一步契约的要求。稳定执行状态应写入明确的 `content-memo.md`，只携带有界证据指针；不复制本地 memory 文件或完整 CLI transcript。[OpenAI：本地 memories](https://learn.chatgpt.com/docs/customization/memories)、[OpenAI：compact 命令](https://learn.chatgpt.com/docs/developer-commands)。

## Claude Code CLI / Claude Desktop 特别优化指令

Claude Code auto memory 存储在 `~/.claude/projects/<project>/memory/`；`MEMORY.md` 是索引，只有开头 200 行或 25 KB（取较小值）会在 Session 启动时载入。主题文件按需加载。同一 Git 仓库内的所有 worktree 和子目录共用这一本机 memory 目录；主对话的 auto memory 不会载入其 subagent。当前 Session 暴露这些命令时，用 `/memory` 浏览 memory 文件，用 `/context` 核对已加载的 `CLAUDE.md` 和 rules 文件。`CLAUDE.md` 保存长期指令，auto memory 记录学习到的偏好；`/compact` 压缩的是**会话历史**，`PreCompact`／`PostCompact` 只观察该过程。它们都不能代替本 Worker 拥有、受路径限制、可追溯来源的 `content-memo.md` 或实时 parent state record。启用 memo 时，只将稳定决策、来源引用、变更路径、阻塞与下一步写入获授权文件；不应倾倒整个 transcript，也不应把 auto memory 复制一份进去。[Anthropic：memory 存储位置、载入限制和命令](https://code.claude.com/docs/en/memory)、[Anthropic：compaction Hooks](https://code.claude.com/docs/en/hooks)。

## 相关概念

- [Worker Content Memo Dispatch](content-memo-dispatch_zh_cn.md) — 定位 memo dispatch 开关。
- [Worker Content Memo Lifecycle](content-memo-lifecycle_zh_cn.md) — 定位 memo 生命周期规则。

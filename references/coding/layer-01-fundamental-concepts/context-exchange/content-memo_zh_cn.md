# Worker Content Memo

[English](content-memo.md) | [简体中文](content-memo_zh_cn.md)

本文档定义以 Serena 项目 Memory 持久化的 Worker 执行 memo 内容契约，不定义 dispatch 开关或生命周期。

## 通用规范

### 用途与内容

使用 Memory 名称 `context-exchange/workers/<worker-context-id>/content-memo`；Serena 在默认项目数据目录下将其映射为 `.serena/memories/context-exchange/workers/<worker-context-id>/content-memo.md`。Serena 配置可以更改该目录。名称只表示逻辑归属：Serena 不强制 Worker 级可见性、只读访问或文件系统隔离；拥有相关工具的 Session 可能看到或修改该 Memory。遵守已放行任务中的归属指令，不得声称存在技术隔离。

Worker 编写的 prose 使用中文。路径、文件名、命令、symbol、key、hash、准确错误和日志片段保留原文。只记录稳定且可复用的执行状态：完成结果、发现、变更路径/symbol、验证证据、失败方案、剩余工作、阻塞和 handoff 需求。保留指向权威来源的准确指针，不把来源全文作为权威副本存入 Memory。

### 禁止材料和能力不可用

不得写逐命令日志、完整日志/diff、大段源码副本、秘密、私有推理、完整 transcript、无关历史或父级实时 mode/count/allocation/epoch 状态。Serena Memory 读写不可用时，报告限制并阻塞依赖该记录的工作；不得回退到文件写入该记录。独立工作可以继续。

## Codex CLI / ChatGPT Desktop 特别优化指令

只使用当前 Session 实际暴露且获准的 Serena Memory 工具。Codex 本地 memories 和 `/compact` 不能代替具名 Serena Memory。确认写入成功；当前工作流要求时，使用 `read_memory` 核验存储条目。

## Claude Code CLI / Claude Desktop 特别优化指令

仅当当前 Session 暴露且授权相关 Serena MCP 工具时，才使用 Serena Memory。Claude auto memory 和 compaction 不能代替该具名项目 Memory。核实实际工具可用性和写入结果；不得假设 Serena Memory 已共享或隔离。

## 相关概念

- [Worker Content Memo Dispatch](content-memo-dispatch_zh_cn.md) — 定位 Memory 写入开关。
- [Worker Content Memo Lifecycle](content-memo-lifecycle_zh_cn.md) — 定位更新与发现规则。

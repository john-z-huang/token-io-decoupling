# Coding Context Exchange Handoff

[English](context-exchange-handoff.md) | [简体中文](context-exchange-handoff_zh_cn.md)

本文档负责 Worker-local context index、上下文实质更新、handoff 和 replacement-state 记录以及 successor 暴露。它只记录已获准 handoff 的上下文传输；不授权子 Agent 复用或替换，不定义 capsule 内容或工作区 capability。

## 通用规范

### Worker-local 上下文记录

每个 Worker-local `INDEX.md` 只记录 task、scope、status、最近一次实质更新、各文档用途以及 blocker 或 handoff 目标。只有能提供不同复用价值时才增加专项文档。上下文文件只在状态、证据或 handoff 实质变化时更新，不要每条命令都写记录。

### Handoff 和 successor 暴露

获准的 successor 使用新的 Context ID 和目录。它只能读取父 Agent 明确暴露的前任文档，永远不得写入前任目录。获准的 replacement handoff 应记录已完成状态、失败方案与证据、当前修改和验证状态、blocker 以及下一步最有价值的动作。父 Agent 更新根索引，只暴露点名的前任文档。前任不可用时，只记录事实支持的最小恢复说明，不能重建完整 transcript。

## Codex CLI / ChatGPT Desktop 特别优化指令

目前没有针对该厂商的特别优化指令；遵循上述通用规范。

## Claude Code CLI / Claude Desktop 特别优化指令

目前没有针对该厂商的特别优化指令；遵循上述通用规范。

## 相关概念

- [Coding Context Exchange](context-exchange_zh_cn.md) — 定位 capsule 和 freshness 归属。
- [Coding Context Exchange Workspace Boundary](context-exchange-workspace-boundary_zh_cn.md) — 定位目录和 capability 边界。
- [Coding Session Context Firewall](session-context-firewall_zh_cn.md) — 定位原始状态进入归属。
- [Coding Child Reuse and Replacement](delegation-child-reuse-replacement_zh_cn.md) — 定位复用和替换授权归属。
- [Coding Child Lifecycle](delegation-child-lifecycle_zh_cn.md) — 定位子 Agent 状态和恢复归属。

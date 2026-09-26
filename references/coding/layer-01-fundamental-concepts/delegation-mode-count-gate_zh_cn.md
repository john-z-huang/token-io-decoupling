# Coding 委派数量门禁

[English](delegation-mode-count-gate.md) | [简体中文](delegation-mode-count-gate_zh_cn.md)

本文档负责多代理子 Agent 数量的选择、锁定和数量预算边界。它消费已选择的模式和状态记录；不定义模式选择、重新进入、子 Agent 创建或生命周期。

## 通用规范

### 数量选择和锁定

选择多代理后，优先采用用户在模式选择时给出的明确正整数数量；否则使用 1，包括 15 秒超时的情形。不得再提出第二个阻断式数量问题。明确给出的数量无效时，保持路线未放行，直到用户给出有效正整数；不得解释为同意其他数量。数量是整次会话的子代理总预算，而非每任务、每阶段或每职责的数量。

路线放行前锁定数量，在父级状态记录中预留恰好该数量的计划 allocation 名额。每个初始名额均使用 `agent: unbound`、`role: unassigned`、`slice_status: pending` 和 `lifecycle: pending`；预留名额不表示 Context、Decision 或具体 Slice 已经放行。父级完成有界事实确认后，由职责分配 owner 在这些名额内分配职责。只有角色和本次 Slice 均获放行，才可以创建对应子代理。每项独立职责消耗一个预留名额；复用不增加名额。数量锁定固定的是总预算，不是尚未绑定子代理名额的具体内容。

数量锁定后不得通过 replacement、fork、handoff successor、额外 verifier 或其他子代理突破预算。已经创建过子代理的名额不得回收后创建另一个子代理。必需名额或能力不可用时阻塞依赖工作，不得默默更改数量。

## Codex CLI / ChatGPT Desktop 特别优化指令

目前没有针对该厂商的特别优化指令；遵循上述通用规范。

## Claude Code CLI / Claude Desktop 特别优化指令

目前没有针对该厂商的特别优化指令；遵循上述通用规范。

## 相关概念

- [Coding Delegation Mode Confirmation](delegation-mode-confirmation_zh_cn.md) — 定位根模式确认归属。
- [Coding Delegation Count Gate](delegation-mode-count-gate_zh_cn.md) — 定位数量锁定归属。
- [Coding Delegation Re-entry](delegation-mode-reentry_zh_cn.md) — 定位门禁重新进入归属。
- [Coding Delegation State Record](delegation-state-record_zh_cn.md) — 定位状态记录归属。
- [Coding Child Creation](delegation-child-creation_zh_cn.md) — 定位子 Agent 创建归属。
- [Coding Child Lifecycle](delegation-child-lifecycle_zh_cn.md) — 定位子 Agent 生命周期归属。

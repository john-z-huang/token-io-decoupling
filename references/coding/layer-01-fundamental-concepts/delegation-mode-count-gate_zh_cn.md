# Coding 委派数量门禁

[English](delegation-mode-count-gate.md) | [简体中文](delegation-mode-count-gate_zh_cn.md)

本文档负责多代理子 Agent 数量的选择、锁定和数量预算边界。它消费已选择的模式和状态记录；不定义模式选择、重新进入、子 Agent 创建或生命周期。

## 通用规范

### 数量选择和锁定

选择多代理后，采用用户明确给出的正整数子代理数量；否则锁定 1 个子代理的预算。首次 Coding 指令默认选择 Multi-Agent 时也应用此默认值。用户选择了自定义数量选项、但遗漏或给出无效数量时，只提出一个聚焦的补充问题并保持 Mode gate 未放行；不得替换为 1。数量有效时不再提出额外数量问题。其他明确数量无效时，保持路线未放行，直到用户给出有效正整数；不得解释为同意其他数量。数量是整次会话的子代理总预算，而非每任务、每阶段或每职责的数量。

路线放行前锁定数量，在父级状态记录中预留恰好该数量的计划 allocation 名额。每个初始名额均使用 `agent: unbound`、`role: unassigned`、`slice_status: pending` 和 `lifecycle: pending`；预留名额不表示 Context、Decision 或具体 Slice 已经放行，也不会初始化子代理。父级完成有界事实确认后，由职责分配 owner 在这些名额内分配职责。只有角色和本次 Slice 均获放行，且输出属于代码/配置实现或本 Skill 指令/参考文档编写编辑，才可以创建对应子代理。普通非 Skill 文档不会触发或消耗预留名额；由根父级编写，包括同时存在代码修改的任务。每项独立职责消耗一个预留名额；复用不增加名额。数量锁定固定的是总预算，不是尚未绑定子代理名额的具体内容。

数量锁定后不得通过 replacement、fork、handoff successor、额外 verifier 或其他子代理突破预算。已经创建过子代理的名额不得回收后创建另一个子代理。必需名额或能力不可用时阻塞依赖工作，不得默默更改数量。

## Codex CLI / ChatGPT Desktop 特别优化指令

目前没有针对该厂商的特别优化指令；遵循上述通用规范。

## Claude Code CLI / Claude Desktop 特别优化指令

目前没有针对该厂商的特别优化指令；遵循上述通用规范。

## 相关概念

- [Coding Delegation Mode Confirmation](delegation-mode-confirmation_zh_cn.md) — 定位根模式确认归属。
- [Coding Delegation Re-entry](delegation-mode-reentry_zh_cn.md) — 定位门禁重新进入归属。
- [Coding Delegation State Record](delegation-state-record_zh_cn.md) — 定位状态记录归属。
- [Coding Child Creation](delegation-child-creation_zh_cn.md) — 定位子 Agent 创建归属。
- [Coding Child Lifecycle](delegation-child-lifecycle_zh_cn.md) — 定位子 Agent 生命周期归属。

# Coding 委派数量门禁

[English](delegation-mode-count-gate.md) | [简体中文](delegation-mode-count-gate_zh_cn.md)

本文档负责多代理子 Agent 数量的选择、锁定和数量预算边界。它消费已选择的模式和状态记录；不定义模式选择、重新进入、子 Agent 创建或生命周期。

## 数量选择和锁定

本次会话选择多代理后，如用户在模式选择时提供了明确的正整数子代理数量，则采用该数量；否则使用 1 个子代理，包括 15 秒超时的情形。不得再提出第二个阻断式数量问题。明确给出的数量无效时，保持路线未放行，直到用户给出有效正整数；不得将其解释为同意其他数量。数量是本次会话的子代理总预算，不是每任务、每阶段或每职责的数量。

首次 Dispatch 前锁定数量，路线放行前形成恰好该数量的计划 allocation；创建前可以使用 `agent: unbound`。只有 1 个子代理时将其分配给 Primary Output；独立 Change Verification 和文档/Git 子代理职责未分配，因此同 Session 检查须标记为逻辑检查和独立性不可用。每项独立职责消耗一个名额；复用不增加名额。锁定后不得创建替代子代理、fork、handoff 后继、额外 verifier 或其他超过预算的子代理。必需名额或能力不可用时阻塞依赖工作，不得默默更改数量。

## 相关概念

- [Coding Delegation Mode Confirmation](delegation-mode-confirmation_zh_cn.md) — 定位根模式确认归属。
- [Coding Delegation Count Gate](delegation-mode-count-gate_zh_cn.md) — 定位数量锁定归属。
- [Coding Delegation Re-entry](delegation-mode-reentry_zh_cn.md) — 定位门禁重新进入归属。
- [Coding Delegation State Record](delegation-state-record_zh_cn.md) — 定位状态记录归属。
- [Coding Child Creation](delegation-child-creation_zh_cn.md) — 定位子 Agent 创建归属。
- [Coding Child Lifecycle](delegation-child-lifecycle_zh_cn.md) — 定位子 Agent 生命周期归属。

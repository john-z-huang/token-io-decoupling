# Coding 委派数量门禁

[English](delegation-mode-count-gate.md) | [简体中文](delegation-mode-count-gate_zh_cn.md)

本文档负责多代理子 Agent 数量的建议、确认、锁定和数量预算边界。它消费已确认的模式和状态记录；不定义根模式确认、重新进入、子 Agent 创建或生命周期。

## 数量建议和确认

确认多代理后，根父级建议准确的正整数子 Agent 数量，询问确认并等待。该数量是根指令的总预算，不是阶段或职责数量。

## 数量锁定

数量确认后，在第一次 Dispatch 前锁定。运行时能够安全创建时必须创建恰好该数量，否则阻塞而不能默默改变数量。每个独立职责消耗一个名额；复用不创建新名额。替换、fork、handoff 到新子 Agent 或增加 verifier 都属于新建，当前指令锁定后禁止。

能力不可用时阻塞数量路线，不能据此默默改变已确认的数量。

## 相关概念

- [Coding Delegation Mode Confirmation](delegation-mode-confirmation_zh_cn.md) — 定位根模式确认归属。
- [Coding Delegation Count Gate](delegation-mode-count-gate_zh_cn.md) — 定位数量锁定归属。
- [Coding Delegation Re-entry](delegation-mode-reentry_zh_cn.md) — 定位门禁重新进入归属。
- [Coding Delegation State Record](delegation-state-record_zh_cn.md) — 定位状态记录归属。
- [Coding Child Creation](delegation-child-creation_zh_cn.md) — 定位子 Agent 创建归属。
- [Coding Child Lifecycle](delegation-child-lifecycle_zh_cn.md) — 定位子 Agent 生命周期归属。

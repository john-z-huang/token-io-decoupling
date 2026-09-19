# Coding 委派重新进入

[English](delegation-mode-reentry.md) | [简体中文](delegation-mode-reentry_zh_cn.md)

本文档负责重新进入模式和数量门禁，以及更高优先级限制或能力不可用时的阻断边界。它消费模式确认和数量门禁的结果；不重复其确认或数量锁定策略，也不定义子 Agent 创建或生命周期。

## 门禁重新进入

每个新的根指令都会重新打开模式和数量门禁，即使工作继续在同一项目中。后续指令实质性改变委派时，必须在改变拓扑或继续改变后的路线前重新应用这些门禁。

## 更高优先级限制和能力阻断

用户、权限、安全、产品、运行环境、能力、仓库和安全限制始终有效。能力不可用时阻塞路线，不能据此默默改变模式或数量。

## 相关概念

- [Coding Delegation Mode Confirmation](delegation-mode-confirmation_zh_cn.md) — 定位模式确认归属。
- [Coding Delegation Count Gate](delegation-mode-count-gate_zh_cn.md) — 定位数量锁定归属。
- [Coding Delegation Re-entry](delegation-mode-reentry_zh_cn.md) — 定位门禁重新进入归属。
- [Coding Delegation State Record](delegation-state-record_zh_cn.md) — 定位状态记录归属。
- [Coding Child Creation](delegation-child-creation_zh_cn.md) — 定位子 Agent 创建归属。
- [Coding Child Lifecycle](delegation-child-lifecycle_zh_cn.md) — 定位子 Agent 生命周期归属。

# Coding 委派重新进入

[English](delegation-mode-reentry.md) | [简体中文](delegation-mode-reentry_zh_cn.md)

本文档负责重新进入模式和数量门禁，以及更高优先级限制或能力不可用时的阻断边界。它消费模式确认和数量门禁的结果；不重复其确认或数量锁定策略，也不定义子 Agent 创建或生命周期。

## 通用规范

### 门禁重新进入

同一宿主 Session 生命周期内的后续根指令沿用已锁定的模式和当前子代理数量预算；不重新打开模式选择，也不替换会话选择。后续轮次、compact 或同一 Session 的恢复均不会重置这些门禁。唯一允许的同 Session 数量变化，是按[委派数量门禁](delegation-mode-count-gate_zh_cn.md)，在用户实际明确批准为不同且未占用职责增加一个名额后，恰好增加一个名额。该事务只改变数量；不重新选择模式、不放行 Slice，也不创建子代理。其他数量或拓扑变更请求都会阻塞依赖工作，直到开启新 Session。按需更新任务专属 Contract、切片、allocation 的当前生命周期和能力证据。

Fork 会以新的 Session 身份开启新会话。在任何依赖工作前，必须重新确认模式、选择数量并初始化状态记录，即使来源会话曾使用 Single-Agent 模式也一样。继承的子代理身份属于其他会话：不得将其采纳为已创建、已预留、可恢复或当前会话的合格候选。新记录只能依据本会话当前用户指令和状态构建；不得把来源会话已锁定的模式/数量选择冒充为本会话的新选择。

### 更高优先级限制和能力阻断

用户、权限、安全、产品、运行环境、能力、仓库和安全限制始终有效。能力不可用时阻塞路线，不能据此默默改变模式或数量。

## Codex CLI / ChatGPT Desktop 特别优化指令

目前没有针对该厂商的特别优化指令；遵循上述通用规范。

## Claude Code CLI / Claude Desktop 特别优化指令

目前没有针对该厂商的特别优化指令；遵循上述通用规范。

## 相关概念

- [Coding Delegation Mode Confirmation](delegation-mode-confirmation_zh_cn.md) — 定位模式确认归属。
- [Coding Delegation Count Gate](delegation-mode-count-gate_zh_cn.md) — 定位数量锁定归属。
- [Coding Delegation State Record](delegation-state-record_zh_cn.md) — 定位状态记录归属。
- [Coding Session Model](../session-runtime/session-model_zh_cn.md) — 定位 Session 身份和 Fork 边界。
- [Coding Child Creation](delegation-child-creation_zh_cn.md) — 定位子 Agent 创建归属。
- [Coding Child Lifecycle](delegation-child-lifecycle_zh_cn.md) — 定位子 Agent 生命周期归属。

# Coding 子 Agent 创建

[English](delegation-child-creation.md) | [简体中文](delegation-child-creation_zh_cn.md)

本文档负责创建 Multi-Agent 子 Agent 的唯一能力入口。入口要求是：已 release 的 Multi-Agent 状态、已锁定的正整数 `child_count`，以及恰好等于 `child_count` 个已锁定的计划 allocation；每个计划 allocation 在创建前都可以是 `agent: unbound`。它不重新打开 mode 或 count 确认。数量锁定前的计划级 replacement 不属于创建能力，不能创建子 Agent 或消耗子 Agent 名额。创建成功后，由本 owner 将每个已创建的 agent identity 和实际 lifecycle 回写到计划 allocation；不改变 mode 或 count，也不创建额外名额。它不定义职责分配、Dispatch Preview、Worker 边界、复用或替换，或生命周期。

## 创建能力

创建子 Agent 意味着使用真实的 MultiAgentV1 或 MultiAgentV2 spawn 操作，而不是 peer chat 或通用 task。运行时必须暴露子 Agent identity、由父级控制的发送/返回路径、有界等待和生命周期状态。子 Agent 接收一个 role、一个 Interaction Slice、authorized scope/mutations、return conditions 和必要 context。若任何能力缺失或无法验证，则停止并报告阻塞，不改变 mode、count，也不创建额外名额。

## 相关概念

- [Coding Child Lifecycle](delegation-child-lifecycle_zh_cn.md) — 定位子 Agent 状态归属。
- [Coding Child Role Allocation](delegation-child-role-allocation_zh_cn.md) — 定位名额和职责分配。
- [Coding Child Dispatch](delegation-child-dispatch_zh_cn.md) — 定位实际派发边界。
- [Coding Child Reuse and Replacement](delegation-child-reuse-replacement_zh_cn.md) — 定位获准的复用和替换。
- [Coding Session Model](session-model_zh_cn.md) — 定位 role 和 Session 归属。
- [Coding Context Exchange](context-exchange_zh_cn.md) — 定位必要的上下文传输归属。

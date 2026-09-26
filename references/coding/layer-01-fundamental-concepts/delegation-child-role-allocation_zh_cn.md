# Coding 子 Agent 职责分配

[English](delegation-child-role-allocation.md) | [简体中文](delegation-child-role-allocation_zh_cn.md)

本文档负责在 Multi-Agent count 已 locked 时进行名额和辅助职责分配。不定义子 Agent 创建、Dispatch Preview、Worker 边界、复用或替换、生命周期、上下文传输、验证或 Git 策略。

## 通用规范

### 职责分配

父级完成有界事实确认后，只能在已锁定和预留的数量预算内分配职责。预留名额在用途未确定前可以保持 `role: unassigned`；创建子代理前必须分配并放行其职责。只有一个子代理时，将其分配给 Primary Output。Primary Output、Change Verification、Documentation/Comments & Git Operations、Context Bootstrap/Refresh 及其他独立职责各自消耗一个名额。获准修改未绑定名额的计划不属于创建替代子代理，不得突破预算；创建后子代理身份保持绑定。未分配独立 verifier 或辅助职责时，安全情况下可使用当前或已分配 Agent，否则报告不可用；不得通过改名将同一 Session 的工作冒充独立验证。

### Context Bootstrap/Refresh 分配

仅当复用可能比设置成本更有利时分配 Context Bootstrap/Refresh：至少两个独立下游 Worker、广泛侦察加三个或更多路由策略模块，或来源集合大致超过 20k 字符 / 5k token-equivalents。单个小 Worker 或仅文档快速路径应跳过。这里的数值是路由启发式，不是运行时或质量测量结论。

## Codex CLI / ChatGPT Desktop 特别优化指令

目前没有针对该厂商的特别优化指令；遵循上述通用规范。

## Claude Code CLI / Claude Desktop 特别优化指令

目前没有针对该厂商的特别优化指令；遵循上述通用规范。

## 相关概念

- [Coding Child Creation](delegation-child-creation_zh_cn.md) — 定位子 Agent 创建归属。
- [Coding Child Dispatch](delegation-child-dispatch_zh_cn.md) — 定位实际派发边界。
- [Coding Child Lifecycle](delegation-child-lifecycle_zh_cn.md) — 定位子 Agent 状态归属。
- [Coding Child Reuse and Replacement](delegation-child-reuse-replacement_zh_cn.md) — 定位获准的复用和替换。
- [Coding Context Exchange](context-exchange_zh_cn.md) — 定位上下文传输归属。

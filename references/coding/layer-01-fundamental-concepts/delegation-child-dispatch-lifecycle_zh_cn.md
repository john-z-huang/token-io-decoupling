# Coding 子 Agent 生命周期

[English](delegation-child-dispatch-lifecycle.md) | [简体中文](delegation-child-dispatch-lifecycle_zh_cn.md)

本文档负责已创建多代理子 Agent 的持久性和生命周期状态。它消费已由各自 owner 概念处理创建、分配和派发的子 Agent；不定义创建、职责分配、Dispatch Preview、Worker 边界、复用/替换或上下文传输。

## 生命周期状态

已创建的子 Agent 必须保持可见和持久。不得关闭、shutdown、归档、删除或从任务面板移除。pending 或 running 时只能等待或发送已授权输入。只有返回最终结果和证据后才能进入 completed。

## 错误与中断

发生错误或中断时，保持子 Agent 状态明确，报告阻塞和现有证据；未经授权不得以清理为由关闭它。获准的修复、复用或替换遵循对应 owner 概念。

## 相关概念

- [Coding Child Creation](delegation-child-creation_zh_cn.md) — 定位子 Agent 创建能力。
- [Coding Child Role Allocation](delegation-child-role-allocation_zh_cn.md) — 定位名额和职责分配。
- [Coding Child Dispatch](delegation-child-dispatch_zh_cn.md) — 定位 Dispatch Preview 和 Worker 边界。
- [Coding Child Reuse and Replacement](delegation-child-reuse-replacement_zh_cn.md) — 定位获准修复和替换关系。
- [Coding Context Exchange](context-exchange_zh_cn.md) — 定位上下文传输归属。

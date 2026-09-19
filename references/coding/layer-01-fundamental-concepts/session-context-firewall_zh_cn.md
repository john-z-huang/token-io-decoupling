# Coding Session Context Firewall

[English](session-context-firewall.md) | [简体中文](session-context-firewall_zh_cn.md)

本文档负责 Context Firewall：原始状态进入限制、有界检查、事实返回边界和临时项目定位。不定义职责责任、Session 语义、文件化上下文传输或工作流验收。

## 原始状态进入

在多 Session Coding 中，输入侧 Session 不执行开放式项目检查。Primary Output 消费源代码/配置状态；Change Verification 消费最终状态证据；Documentation/Comments & Git Operations 消费 Git 状态和获准的文档范围。各自只返回下一步决策所需的事实。

只有严格有界的只读元数据可由输入侧直接检查。边界由潜在输出体积和仓库状态影响决定，而不是由命令名称决定。单 Session 没有跨 Session Firewall，但仍须渐进读取并压缩原始状态。

## 语义 ownership 和临时定位

Firewall 限制原始状态进入输入侧上下文，不限制语义推理。输入侧仍拥有含义、权衡、放行决定和验收；临时的 UI/项目定位状态留在观察它的 Session 中，不提升为长期 Contract 状态。

## 相关概念

- [Coding Session Model](session-model_zh_cn.md) — 定位 Session 语义和 Affinity。
- [Coding Session Role Ownership](session-role-ownership_zh_cn.md) — 定位职责责任归属。
- [Coding Context Exchange](context-exchange_zh_cn.md) — 定位文件化上下文传输。
- [Coding Delegation State Record](delegation-state-record_zh_cn.md) — 定位任务控制状态归属。
- [Coding Execution Control](execution-control_zh_cn.md) — 定位有界阶段和 slice 归属。

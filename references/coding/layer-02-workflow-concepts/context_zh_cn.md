# 上下文检查点

[English](context.md) | [简体中文](context_zh_cn.md)

## 动作

1. 明确下一切片必须回答的最小问题。
2. 只读取回答该问题所需的文件、元数据、历史或生成证据。
3. 复用缓存或文件上下文前，检查其范围、所有者、来源路径、新鲜度和最终状态 epoch。
4. 将过期、不完整或互相冲突的上下文视为不可用。只刷新受影响的上下文，并记录发生了什么变化。
5. 保持上下文以事实和路由信息为主；不能用它替代 Contract、源文档或验证。

## 通过条件

下一切片拥有有界且当前有效的上下文，或已记录具体缺失的上下文并暂停该切片。

## 边界

本检查点只收集和判断上下文，不作实质性决策，不授权实现，也不宣布验证完成。

## 相关概念

- [Coding Context Exchange](../layer-01-fundamental-concepts/context-exchange_zh_cn.md) — 定位文件化 capsule 和 freshness 归属。
- [Coding Session Context Firewall](../layer-01-fundamental-concepts/session-context-firewall_zh_cn.md) — 定位原始状态进入和事实返回归属。

# 修复执行检查点

[English](repair-execution.md) | [简体中文](repair-execution_zh_cn.md)

本检查点负责执行获准的窄范围修复及其聚焦检查。它消费范围门禁的授权；不诊断失败，不定义授权条件，也不创建验证 epoch。

## 动作

1. 只在已放行的路径和修改范围内执行获准修复。
2. 运行直接检查该修复或为其提供信息的聚焦检查。
3. 向父级边界返回已修改路径、相关检查输出和剩余问题。

## 通过条件

获准的窄范围修复已经执行，且聚焦检查已通过或产生了可交给下一 owner 的具体问题。

## 边界

本检查点不诊断失败，不授权范围变化，不定义最终状态指纹或 epoch，不执行最终验证，不写文档，也不产生 Git 影响。

## 相关概念

- [Coding Execution Control](../layer-01-fundamental-concepts/execution-control_zh_cn.md) — 定位已放行路径和修改边界。
- [Coding Execution Planning](../layer-01-fundamental-concepts/execution-planning_zh_cn.md) — 定位有界实现 slice 归属。
- [Coding Delegation State Record Worker Boundary](../layer-01-fundamental-concepts/delegation-state-record-worker-boundary_zh_cn.md) — 定位命名路径的 Worker 访问边界。

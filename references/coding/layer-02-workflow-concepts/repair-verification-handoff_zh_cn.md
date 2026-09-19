# 修复验证交接检查点

[English](repair-verification-handoff.md) | [简体中文](repair-verification-handoff_zh_cn.md)

本检查点负责将改变状态的修复以新的最终状态指纹或 epoch 交回验证。它不授权修复、不定义修复内容，也不定义验证检查或结果报告。

## 动作

1. 对改变状态的修复，捕获产生的最终状态指纹或 epoch。
2. 在依赖工作继续前，将新状态交回验证检查点。

## 通过条件

已改变状态拥有新的最终状态指纹或 epoch，并已明确排队等待验证；或者交接已暂停并明确缺少的证据。

## 边界

本检查点不诊断失败，不授权或执行修复，不定义检查内容，不分类结果，不写文档，也不产生 Git 影响。

## 相关概念

- [Coding Execution Control](../layer-01-fundamental-concepts/execution-control_zh_cn.md) — 定位实质性边界和返回条件归属。
- [Coding Execution Decision Gate](../layer-01-fundamental-concepts/execution-decision-gate_zh_cn.md) — 定位依赖路线放行归属。
- [Coding Delegation State Record Worker Boundary](../layer-01-fundamental-concepts/delegation-state-record-worker-boundary_zh_cn.md) — 定位最终状态证据访问边界。
- [Coding Child Reuse and Replacement](../layer-01-fundamental-concepts/delegation-child-reuse-replacement_zh_cn.md) — 定位修复 epoch 复用归属。

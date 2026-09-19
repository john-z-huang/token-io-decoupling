# 实现检查点

[English](implementation.md) | [简体中文](implementation_zh_cn.md)

## 动作

1. 重新读取切片目标、授权路径、允许的修改和返回条件。
2. 只检查该切片所需的文件，然后以最小修改满足已批准的方向。
3. 不要把无关清理、重构、生成产物或外部影响带入切片。
4. 运行可以指导修复的聚焦临时检查，但不要把它们当作最终验收。
5. 返回已修改路径、相关输出、剩余问题和尚未发布的边界。

## 通过条件

获批准的切片已在范围内实现，且聚焦检查要么通过，要么提供了可交给修复检查点的具体问题。

## 边界

本检查点不扩大范围，不改变实质性决策，不执行最终验证，不写入验证后的文档，也不产生未授权的 Git 影响。

## 相关概念

- [Coding Execution Control](../layer-01-fundamental-concepts/execution-control_zh_cn.md) — 定位授权路径、修改和返回边界归属。
- [Coding Execution Planning](../layer-01-fundamental-concepts/execution-planning_zh_cn.md) — 定位有界规划和已放行 slice 归属。
- [Coding Execution Decision Gate](../layer-01-fundamental-concepts/execution-decision-gate_zh_cn.md) — 定位方向和实现放行归属。
- [Coding Delegation State Record Worker Boundary](../layer-01-fundamental-concepts/delegation-state-record-worker-boundary_zh_cn.md) — 定位命名路径的 Worker 访问边界。

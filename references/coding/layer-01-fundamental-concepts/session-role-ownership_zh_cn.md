# Coding Session 职责归属

[English](session-role-ownership.md) | [简体中文](session-role-ownership_zh_cn.md)

本文档负责 Coding 架构角色的责任：输入侧推理、Primary Output、Context Bootstrap/Refresh、Change Verification 以及 Documentation/Comments & Git Operations。不定义 Session 语义、职责分配、Context Firewall 策略或工作流最终验收。

## 输入侧推理 Agent

负责用户意图与业务语义分析、Semantic Contract、架构和风险决策、未解决的权衡、阶段与 slice 边界、放行决定、checkpoint 结果、用户交互和最终语义验收。它可以请求证据和候选项，但必须解释其含义，不得摄入高体量项目原始状态，也不得把已批准的决定展开成长篇输出。

## Primary 输出角色

负责高体量项目探索、证据压缩、在已批准方向内执行、代码/配置物化、已放行 slice 内的修复和临时实现检查。它采用渐进式读取，不能改变未解决的目标、约束、架构或验收标准，也不负责最终验收或非简单 Git 工作。

## Context Bootstrap/Refresh 职责

被分配时，构建或刷新包含中性项目事实、准确 source pointer、policy-routing pointer 和 freshness 数据的有界 fingerprint capsule。它不定义任务、不修改 Contract、不实现、不验证、不物化文档，也不得递归委派。Capsule 只能补充强制指令，不能替代直接读取权威文件。

## Change Verification Agent

被分配时，独立依据 Contract 和验收标准验证实质性改动的最终状态。它消费范围证据，执行适当的整体和定向检查，针对每个最终状态 fingerprint/epoch 重新评估，并报告证据、缺口、失败和风险。除明确点名的验证资产外，它对产品代码/配置、文档和 Git 保持只读；不修复、不作语义决策、不委派。

## Documentation/Comments & Git Operations Agent

被分配时，只物化获准的文档/注释，或只执行明确放行的非简单 Git slice。它不得修改产品行为、测试或语义决策；如果冲突需要新的内容或含义，必须返回父级。文档与 Git 工作保持为彼此独立的执行范围。

## 相关概念

- [Coding Session Model](session-model_zh_cn.md) — 定位 Session 语义和 Affinity。
- [Coding Session Context Firewall](session-context-firewall_zh_cn.md) — 定位原始状态进入归属。
- [Coding Child Role Allocation](delegation-child-role-allocation_zh_cn.md) — 定位职责分配归属。
- [Coding Delegation State Record](delegation-state-record_zh_cn.md) — 定位任务控制状态归属。
- [Coding Execution Control](execution-control_zh_cn.md) — 定位阶段和 slice 边界归属。

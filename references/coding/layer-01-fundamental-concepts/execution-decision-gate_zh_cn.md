# Coding Execution Decision Gate

[English](execution-decision-gate.md) | [简体中文](execution-decision-gate_zh_cn.md)

本文档定义 Decision Brief、阻塞式 Decision Checkpoint、方案选择、Contract 更新和实现放行的决策条件。不定义规划提纲、Interaction Slice 字段、阶段反馈、角色/Session 语义、上下文传输或委派生命周期。

## Decision Brief

对于不是简单、局部、低风险、明显、可逆且可机械验证的工作，第一次实质性执行 slice 前应准备简洁的 **Decision Brief**。它记录分析结果而不是 private chain-of-thought，至少应包含：

- `Problem`
- `Known facts`
- `Assumptions and unknowns`
- `Decision questions`
- `Solution envelope`
- `Risks`
- `Acceptance`
- `Stages and checkpoints`

`Acceptance` 作为 Decision Brief 字段记录验收信息；本文档不定义 Acceptance 工作流。

## Decision Checkpoint 与实现放行

当下一阶段依赖高价值判断时，使用阻塞式 Decision Checkpoint，例如存在竞争的架构/API 选择、跨越公共接口/schema/兼容性/安全边界、调试出现实质分叉、范围将大幅扩大，或验证失败需要改变 Contract。

如果仍有实质性决策未解决，只能放行 reconnaissance。返回后确认或否定假设，选择批准方向，更新 Contract 并放行实现。如果新证据改变实质性决策，应暂停当前方向并重新执行决策门禁。不得放行让一个执行者同时分析、选择、实现和验证未定方案的未解决组合指令。

## 相关概念

- [Coding Execution Control](execution-control_zh_cn.md) — 定位 Interaction Slice 边界。
- [Coding Execution Planning](execution-planning_zh_cn.md) — 定位有界规划关系。
- [Coding Execution Stage Feedback](execution-stage-feedback_zh_cn.md) — 定位阶段内反馈信号。
- [Coding Session Model](session-model_zh_cn.md) — 定位角色和 Session 归属。
- [Coding 子 Agent Dispatch 与生命周期](delegation-child-lifecycle_zh_cn.md) — 定位委派放行生命周期归属。

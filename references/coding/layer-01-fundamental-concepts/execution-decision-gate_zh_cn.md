# Coding Execution Decision Gate

[English](execution-decision-gate.md) | [简体中文](execution-decision-gate_zh_cn.md)

本文档定义 Decision Brief、阻塞式 Decision Checkpoint、方案选择、Contract 更新和实现放行的决策条件。不定义规划提纲、Interaction Slice 字段、阶段反馈、角色/Session 语义、上下文传输或委派生命周期。

## 通用规范

### Decision Brief

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

### Decision Checkpoint 与实现放行

当下一阶段依赖高价值判断时，使用阻塞式 Decision Checkpoint，例如存在竞争的架构/API 选择、跨越公共接口/schema/兼容性/安全边界、调试出现实质分叉、范围将大幅扩大，或验证失败需要改变 Contract。

如果仍有实质性决策未解决，只能放行 reconnaissance。返回后确认或否定假设，选择批准方向，更新 Contract 并放行实现。如果新证据改变实质性决策，应暂停当前方向并重新执行决策门禁。不得放行让一个执行者同时分析、选择、实现和验证未定方案的未解决组合指令。

## Codex CLI / ChatGPT Desktop 特别优化指令

目前没有针对该厂商的特别优化指令；遵循上述通用规范。

## Claude Code CLI / Claude Desktop 特别优化指令

Claude Code 的实质性决策阶段，如果运行环境暴露 Plan mode（通过 `/plan` 或 Desktop Code 标签页的模式选择器），可以用它在调查和拟定方案期间保持只读。这是**工具权限模式**，并非 Semantic Contract、获准修改、用户确认或父级 Slice Release 已通过的证据。不能因为生成了 Plan 就退出 Plan mode 并直接写文件；必须先经过通用 Decision Brief 与当前路线的放行边界。普通 Desktop Chat 不继承 Code 标签页的执行控制。[Anthropic：常见工作流](https://code.claude.com/docs/en/common-workflows)、[Anthropic：权限](https://code.claude.com/docs/en/permissions)、[Anthropic：Desktop Code](https://code.claude.com/docs/en/desktop)。

## 相关概念

- [Coding Execution Control](execution-control_zh_cn.md) — 定位 Interaction Slice 边界。
- [Coding Execution Planning](execution-planning_zh_cn.md) — 定位有界规划关系。
- [Coding Execution Stage Feedback](execution-stage-feedback_zh_cn.md) — 定位阶段内反馈信号。
- [Coding Session Model](session-model_zh_cn.md) — 定位角色和 Session 归属。
- [Coding 子 Agent 生命周期](delegation-child-lifecycle_zh_cn.md) — 定位委派放行生命周期归属。

# 开发任务编排参考

## 角色与通用规则

[主代理职责](roles/main-agent.md)确定决策、执行和验收归属。[任务规划与选路](planning/task-planning.md)负责路线与依赖。[子代理职责与委派策略](delegation/delegation-policy.md)负责角色匹配、复用、替换和模型选择。

## 按阶段查阅

| 主题 | 参考规则 |
| --- | --- |
| 规划 | [任务约定](planning/contract.md)、[执行者与依赖](planning/task-assignment.md)、[决策与执行条件](planning/execution-decision-gate.md) |
| 委派 | [派发与回执](delegation/delegation-child-dispatch.md)、[上下文交接](delegation/context-exchange-handoff.md) |
| 执行与恢复 | [执行边界](execution/execution-control.md)、[阶段反馈](execution/execution-stage-feedback.md)、[修复范围](execution/repair-scope-gate.md) |
| 验证与交付 | [验证独立性](verification/verification-independence.md)、[证据时效](verification/verification-epoch.md)、[修复后的复验](verification/repair-verification-handoff.md)、[结果报告](verification/verification-reporting.md) |

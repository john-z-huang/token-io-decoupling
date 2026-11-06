# 实现检查点

[English](implementation.md) | [简体中文](implementation_zh_cn.md)

## 动作

1. 重新读取切片目标、授权路径、允许的修改和返回条件。
2. 只检查该切片所需的文件，然后以最小修改满足已批准的方向。
3. 授权实施路径使用受控候选输出时，在各自 owner 规定的门禁处遵循[输出物料化](../../layer-01-fundamental-concepts/execution-planning/output-materialization_zh_cn.md)和[候选合规预检](../../layer-01-fundamental-concepts/execution-planning/candidate-compliance_zh_cn.md)。审阅准确的有界候选及其当前基线；应用前解决每项已选预检返回的失败、未知、遗漏或过期结果。未选择可选候选路径时，记录有原因的 `Not applicable`，且仅在独立授权的实施路径下继续。准备、预检和应用收据都是临时证据，不能替代本检查点的聚焦检查或后续最终 Verification。
4. 不要把无关清理、重构、生成产物或外部影响带入切片。
5. 运行可以指导修复的聚焦临时检查，但不要把它们当作最终验收。
6. 返回已修改路径、相关输出、剩余问题和尚未发布的边界。

实施前应用[任务计划 Memory 生命周期](../../layer-01-fundamental-concepts/execution-planning/task-plan-memory-lifecycle_zh_cn.md)：要求当前计划证据和持久化确认，以及该 owner 要求的内容核验，或其有记录的限制例外。按 owner 规定的边界记录更新；影响授权、范围、验收、方向或依赖实施的事实，须在该工作前记录并分析。仅父级可释放受影响工作。

## 通过条件

获批准的切片已在范围内实现，且聚焦检查要么通过，要么提供了可交给修复检查点的具体问题。

## 边界

本检查点不扩大范围，不改变实质性决策，不执行最终验证，不写入验证后的文档，也不产生未授权的 Git 影响。

## 相关概念

- [Coding Execution Control](../../layer-01-fundamental-concepts/execution-control/execution-control_zh_cn.md) — 定位授权路径、修改和返回边界归属。
- [Coding Execution Planning](../../layer-01-fundamental-concepts/execution-planning/execution-planning_zh_cn.md) — 定位有界规划和已放行 slice 归属。
- [Coding Execution Decision Gate](../../layer-01-fundamental-concepts/execution-planning/execution-decision-gate_zh_cn.md) — 定位方向和实现放行归属。
- [输出物料化](../../layer-01-fundamental-concepts/execution-planning/output-materialization_zh_cn.md) — 定位受控候选准备和应用。
- [候选合规预检](../../layer-01-fundamental-concepts/execution-planning/candidate-compliance_zh_cn.md) — 定位只读候选检查。
- [Coding Delegation State Record Worker Boundary](../../layer-01-fundamental-concepts/delegation/delegation-worker-boundary_zh_cn.md) — 定位命名路径的 Worker 访问边界。

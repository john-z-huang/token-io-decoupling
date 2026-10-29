# 输出路线选择

[English](output-route-selection.md) | [简体中文](output-route-selection_zh_cn.md)

本检查点依据 [Output Token Routing](../layer-01-fundamental-concepts/execution-planning/output-token-routing_zh_cn.md)，独立评估每项 Root 直接输出是否应改由 Root 之外的路线提供。它不选择执行者。

## 触发与输入

当前任务范围和模式建立后，根据请求形式、预期输出量、用户明确指令、锁定模式和当前已核实事实，逐项评估 Root 直接输出。建议前先检查明确指令。不得使用无关输入/transcript 体量或任意数值阈值。

## 决策与结果

1. 若用户明确指定输出由谁提供或是否提供，记录该指令并仅跳过其对应建议；其他门禁仍有效。
2. 否则逐项返回 `yes`、`no`、`insufficient_evidence` 或 `failed`，并附证据及当前输入/上下文/政策 Hash。输入过期或政策 Hash 不匹配表示未决，绝不等于 `no`。
3. `yes` 表示大型输出应避免由 Root 直接物化。在 Single-Agent 模式下挂起并报告拓扑边界。在 Multi-Agent 模式下，使用合适且空闲的当前 Session 子代理，或等待/挂起直至其空闲。`no` 允许 Root 在其他所有门禁约束下继续。
4. 保持此结果与执行者选择相互独立。仅有 `yes` 不授权创建子代理。只有另行确定需要新执行者后，才可依序进入角色/容量、Slice 和创建门禁。
5. 将逐项结果及证据返回路线调度；此处不释放 Slice 或派发。

## 失败边界

事实不足、Hash 过期或不匹配、建议失败或输出证据冲突时，返回未决。仅当核实事实足够时直接审阅 owner，否则阻塞。不得默认 `no`、仅因输出体量创建子代理或绕过锁定模式边界。

## 相关概念

- [Output Token Routing](../layer-01-fundamental-concepts/execution-planning/output-token-routing_zh_cn.md)
- [Delegation State Record](../layer-01-fundamental-concepts/delegation/delegation-state-record_zh_cn.md)
- [Delegation Count Gate](../layer-01-fundamental-concepts/delegation/delegation-mode-count-gate_zh_cn.md)

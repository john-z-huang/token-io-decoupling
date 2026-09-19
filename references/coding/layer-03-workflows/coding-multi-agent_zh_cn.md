# Coding 工作流——多代理模式

[English](coding-multi-agent.md) | [简体中文](coding-multi-agent_zh_cn.md)

本路线由 Coding 工作流选择；只有模式检查点放行多代理 Coding 后才有效。该检查点在执行前组合三个委派 reference。

## 模式 Contract

- Worker 接收一个已发布的 Interaction Slice，只能通过父级控制的通道返回；不得递归创建层级，也不得把其他 Worker 的进度当作授权。
- 模式/数量与子代理派发/生命周期 reference 负责模式、数量、分配、创建、复用、替换和生命周期；职责名称不能独立授权 Session。
- 如果用户禁止子代理、子任务、独立 Session 或并行委派，应停止本路线并返回路线选择，不得模拟多代理行为。

## 组合输入

本路线组合[共享协议](../../share/shared-protocols_zh_cn.md)、[委派状态记录](../layer-01-fundamental-concepts/delegation-state-record_zh_cn.md)、[模式确认 reference](../layer-01-fundamental-concepts/delegation-mode-confirmation_zh_cn.md)、[模式/数量门禁](../layer-01-fundamental-concepts/delegation-mode-count-gate_zh_cn.md)、[模式重新进入 reference](../layer-01-fundamental-concepts/delegation-mode-reentry_zh_cn.md)、[子代理创建](../layer-01-fundamental-concepts/delegation-child-creation_zh_cn.md)、[子代理职责分配](../layer-01-fundamental-concepts/delegation-child-role-allocation_zh_cn.md)、[子代理派发](../layer-01-fundamental-concepts/delegation-child-dispatch_zh_cn.md)、[子代理复用/替换](../layer-01-fundamental-concepts/delegation-child-reuse-replacement_zh_cn.md)、[子代理生命周期](../layer-01-fundamental-concepts/delegation-child-dispatch-lifecycle_zh_cn.md)、[Session 模型](../layer-01-fundamental-concepts/session-model_zh_cn.md)、[Session 职责归属](../layer-01-fundamental-concepts/session-role-ownership_zh_cn.md)、[Session Context Firewall](../layer-01-fundamental-concepts/session-context-firewall_zh_cn.md)和[执行控制](../layer-01-fundamental-concepts/execution-control_zh_cn.md)；只有已发布切片需要时才加载[上下文交换](../layer-01-fundamental-concepts/context-exchange_zh_cn.md)、[上下文工作区边界](../layer-01-fundamental-concepts/context-exchange-workspace-boundary_zh_cn.md)、[上下文 handoff](../layer-01-fundamental-concepts/context-exchange-handoff_zh_cn.md)或[内容 memo](../layer-01-fundamental-concepts/content-memo_zh_cn.md)。模式检查点已经验证任务记录；下方检查点列表是完整的路线组合。

## 职责边界

职责 ownership 见[Session 职责归属](../layer-01-fundamental-concepts/session-role-ownership_zh_cn.md)；本路线只增加下方的多代理条件。

## 本路线的运行环境要求

使用运行环境检查点提供的能力清单和共用运行规则。只有任务记录和已发布切片所需能力均暴露时才能继续。Worker 只能向直接父级返回，不能创建/管理其他 Agent 或联系任意线程。在本地 Codex 中使用 Skill 绑定：Primary Output 为 `gpt-5.6-luna`/`xhigh`；Change Verification 为 `gpt-5.6-luna`/`xhigh`；Documentation/Git 为 `gpt-5.6-luna`/`high`；Context Bootstrap 为 `gpt-5.6-luna`/`high`，确定性刷新可用 `medium`。重复失败或阻塞时才窄范围升级到 `max`，随后恢复正常档位。

## 已组合的检查点顺序

Coding 选择器已经将 Environment 和 Mode 检查点作为路线前门禁执行；本路线不得重复执行。遵循 Coding 工作流，并组合[Contract](../layer-02-workflow-concepts/contract_zh_cn.md)、[Context](../layer-02-workflow-concepts/context_zh_cn.md)、[Decision](../layer-02-workflow-concepts/decision_zh_cn.md)、[Implementation](../layer-02-workflow-concepts/implementation_zh_cn.md)、[Control](../layer-02-workflow-concepts/control_zh_cn.md)、[Verification](../layer-02-workflow-concepts/verification_zh_cn.md)、[Repair](../layer-02-workflow-concepts/repair_zh_cn.md)、[Documentation](../layer-02-workflow-concepts/documentation_zh_cn.md)、[Git](../layer-02-workflow-concepts/git_zh_cn.md)和[Acceptance](../layer-02-workflow-concepts/acceptance_zh_cn.md)。多代理差异：Worker 需要可复用状态时加载上下文；实质性派发前执行决策；每个已发布实现切片配套控制边界；分配了 verifier 时使用新的独立验证 Session；失败经过修复和新的验证 epoch 后，再进入文档、Git 和验收。

## 上下文与派发

公共工作流已经建立共享协议、Session 规则、运行环境检查和执行控制规则。此外：

1. Worker 需要可复用状态时，读取[上下文交换](../layer-01-fundamental-concepts/context-exchange_zh_cn.md)；需要强制工作区或 capability 边界时，另外读取[上下文工作区边界](../layer-01-fundamental-concepts/context-exchange-workspace-boundary_zh_cn.md)；需要有界交接或替换恢复时，读取[上下文 handoff](../layer-01-fundamental-concepts/context-exchange-handoff_zh_cn.md)。
2. 派发启用 Worker 编写内容 memo 时，读取[内容 memo](../layer-01-fundamental-concepts/content-memo_zh_cn.md)。
3. 只有当前委派状态已经分配时才使用 Context Bootstrap 或 Refresh。保持 capsule 只包含事实和路由信息；它不能替代 Contract、必需的源文档或独立验证。
4. 每个 Worker 使用独立的 context-exchange 子目录，并且只授予它所需的命名代码路径和上下文路径。Worker 分配和边界遵循子代理职责分配与派发 reference。

第一次实质性派发前，除非任务简单、局部、低风险、明显、可逆且可机械验证，否则先形成简洁的 Decision Brief。实质性事实不足时只发布有界侦察，随后在输入侧综合结果，再发布实现。

每个已发布任务包都说明：

```text
Owner: Primary Output | Documentation/Comments & Git Operations | Change Verification
Objective: ...
Authorized scope/mutations: ...
Return conditions: ...
Unreleased boundary: ...
```

不适用的段落写明 `Not applicable` 及原因，不要创建无操作 Worker。除非子代理派发/生命周期 reference 允许独立且不冲突的并行工作，否则一次只发布一个 Interaction Slice。在切片内使用 Progress Signals，在实质性边界使用控制边界检查点。

## 验证与修复

- 实质性修改达到实现检查点后，只有任务控制记录包含已分配 verifier 时，才能执行独立 Change Verification。否则由当前或已分配的 Agent 执行允许的最终检查，并报告独立验证不可用；不得改变委派状态。
- 后续 Evidence-on-Demand 和修复后的 epoch 复用该验证者。每次最终状态指纹改变都必须重新独立评估；早期结论不能作为新状态的证据。
- 失败时只发布窄范围修复，并将新 epoch 发送给同一验证者。实质性问题未解决前，不开始验证后的文档或依赖验证的远程 Git 工作。
- 验证通过后，将文档/注释工作和 Git 工作作为独立的有界切片发布，并明确授权。

## 完成

执行根 Coding 完成门禁，处理文档、Git 和最终验收。最终报告必须区分真实独立 Session 与同一 Session 的逻辑阶段，并把每个验收条件映射到当前证据。

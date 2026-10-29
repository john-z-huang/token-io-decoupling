# Coding 任务执行主体分配

[English](task-assignment.md) | [简体中文](task-assignment_zh_cn.md)

本文档负责决定由 Root 还是子代理执行已放行任务，以及从当前会话合格的现有子代理中进行选择。不负责为新子代理选择职责、创建或派发子代理，也不改变 Output Token 路由。

## 通用规范

### 分配边界

在本文 owner 中，已放行任务是指 Root 在 Context 和 Decision 之后已授权并界定其目标与范围。这不要求面向特定子代理的 Interaction Slice 已放行。执行主体选择本身不能放行后续 Slice：实现或派发前，Root 仍须通过适用的 Slice 门禁并提供具体授权边界。

遵循用户明确的执行主体或 Agent 指令，并跳过相应的建议请求。仍须核验模式、范围、权限、可用性和当前会话身份。显式 `sub_agent` 指令与已锁定的 Single-Agent 模式冲突时，必须交 Root 复核；不得静默改成 `root`。Single-Agent 模式下显式指定 `root` 仍然有效。没有显式执行主体时，Single-Agent 模式没有子代理执行主体，可按本地确定性路径由 Root 处理，但仍须通过其他门禁。Fork 是新 Session，必须按[委派模式重入](../delegation/delegation-mode-reentry_zh_cn.md)重新通过模式/数量门禁；依据[Session 模型](../session-runtime/session-model_zh_cn.md)和[委派状态记录](../delegation/delegation-state-record_zh_cn.md)，继承代理不属于当前会话候选。

执行主体未明确时，Root 审阅当前任务事实和决策上下文，再考虑执行主体建议。若上下文生成失败，或缺少直接影响判断的事实，不得伪造描述/哈希，也不得带着不可用上下文发送下游建议请求。若当前 Skill 和已核实事实足以直接判断，Root 仍可直接决定；否则保留未决状态供审阅。若存在正数未用批准名额且没有合适的现有子代理，`sub_agent` 建议可通过[子代理职责选择](../delegation/child-role-selection_zh_cn.md)继续，无需另行申请预算。Root 须在 Context 与 Decision 之后、该子代理专属 Interaction Slice 放行之前，为已授权的拟派任务选择并预留职责；之后 Slice 门禁仍须核验具体目标/范围与该职责相符。执行主体建议本身不预选职责。没有剩余名额但仍有未占用的不同职责时，Root 必须按[委派数量门禁](../delegation/delegation-mode-count-gate_zh_cn.md)中的用户明确批准流程预留该职责。若四种职责均已占用，扩额不能使另一职责合法可用，必须阻止创建而不得申请扩额。建议能力失败或证据不足时，Root 按本文审阅，绝不默认选择 Root。

### 执行主体 Decisions 指令

为已放行任务选择 `root`、`sub_agent` 或 `insufficient_evidence`。比较语义职责、任务上下文、所需能力和已核实权限。只使用当前审阅任务和已提供的当前会话状态。不得臆造当前子代理、权限、能力、预算或用户指令。任务未放行、事实冲突、必需能力或权限未知，或无法确认任一主体安全执行时，选择 `insufficient_evidence`。若选择 `sub_agent` 且有未用批准名额，可继续职责选择和创建；此工具不授予任何权限。不得仅因 Decisions API 失败就选择 `root`。

### 执行主体选项说明

#### root

当 Root 在已放行范围、当前权限、上下文访问和 Output Token 路由下适合执行时选择。Root 保留语义判断、合同解释、编排和最终验收。

#### sub_agent

当子代理应执行具体的已放行实现或其他合格切片，且当前会话职责、能力、权限和预算门禁均可满足时选择。若有合适现有子代理，继续选择具体子代理。若没有现有子代理但有批准未用名额，继续职责选择和创建。否则请求用户批准一个不同职责，或返回 Root 审阅。

#### insufficient_evidence

当任务或当前证据不足以确定安全执行者、必需能力或权限缺失/未知、事实过期或冲突，或请求超出范围时选择。Root 必须复核；不能把 API 没有成功答复视为 Root 判断。

### 子代理选择 Decisions 指令

从候选中按不透明 `candidate_ref` 选择一个合格子代理，或选择 `insufficient_evidence`。合格要求已核实当前会话身份、职责匹配、所需能力和执行此任务的权限。排除其他会话继承代理和不可用候选。唯一合格候选可直接使用，无需 Decisions。存在多个合格候选时，先考虑适任的空闲子代理，再考虑忙碌者；若都不空闲，等待直到有合适子代理空闲。经过筛选后若只剩一个空闲候选（因为其他合格候选均忙碌），可直接选择该唯一空闲候选。此例外不适用于仍有多个空闲候选的情况。至少有两个空闲候选时，即使 `Primary Output` 具有优先级，也必须调用具体子代理选择 Decisions。若存在合适的空闲 Primary，只向 Decisions 提供该候选和 `insufficient_evidence`；否则提供所有合格空闲候选和 `insufficient_evidence`。若不存在合适 Primary，则比较候选所提供上下文对当前任务的直接支持程度，并优先选择拥有更多相关当前上下文者。不得使用原始 transcript 大小、无关上下文量或数值置信阈值。若上下文相关性相同或无法确认，选择 `insufficient_evidence` 交 Root 审阅。

只有来源政策和当前事实仍然有效时，建议能力失败才可回退到合格的当前会话 `Primary Output` 子代理。回退仍须遵守权限与可用性：仅在其空闲时使用；忙碌时等待其空闲。政策或事实过期、身份冲突时须刷新并交 Root 审阅，绝不回退。若不存在合格 Primary，返回待审阅状态，不得臆造 Root 兜底。唯一合格候选直接使用，无需发送建议请求。多个候选都忙碌时，等待合适子代理空闲。

### 子代理选项说明

#### insufficient_evidence

当提供的职责、能力、权限、可用性和任务相关上下文无法区分候选，或事实不足以安全、唯一地作出选择时使用。Root 审阅当前证据和明确的任务上下文偏好分支；不得设定任意置信阈值。

### 审阅与操作边界

Root 在使用结果前核验当前事实版本/指纹、当前会话关系、候选身份、权限、能力、已放行范围和最新可用性。工具结果仅提供建议，不派发任务。无论执行主体是谁，Root 均保留最终语义判断和验收职责。

## Codex CLI / ChatGPT Desktop 特别优化指令

对于暴露该能力的 Codex 工作流，仅在用户未明确指定执行主体时调用 `workflow_select_executor`。调用 `workflow_select_child` 时，用户明确指定候选可在核验合格性后跳过建议请求；总计只有一个合格候选，或过滤后恰好剩一个空闲候选时，可直接选择。仍有至少两个合格空闲候选时，即使空闲 Primary 优先，也必须调用该工具。传入有界任务相关上下文、匹配职责、能力、权限和可用性事实；若存在合适空闲 Primary，只提供该 Primary 和 `insufficient_evidence`，否则提供所有合格空闲候选和 `insufficient_evidence`。将结果哈希与当前事实核对，然后在派发前通过有效的父级身份和权限门禁验证选定子代理。工具不会向 Decisions 请求发送未提供的其他候选，不会读取宿主 history，也不能证明调用方提供的身份事实。

## Claude Code CLI / Claude Desktop 特别优化指令

当前没有适用于此概念的特别优化；遵循通用规范。

## 相关概念

- [子代理职责选择](../delegation/child-role-selection_zh_cn.md) — 负责职责选择及其兜底。
- [Session 职责归属](../session-runtime/session-role-ownership_zh_cn.md) — 负责受维护职责说明。
- [Session 模型](../session-runtime/session-model_zh_cn.md) — 负责 Session 身份和 affinity。
- [委派状态记录](../delegation/delegation-state-record_zh_cn.md) — 负责当前 allocation 身份和状态。
- [委派数量门禁](../delegation/delegation-mode-count-gate_zh_cn.md) — 负责锁定容量和显式预算扩展。
- [委派模式重入](../delegation/delegation-mode-reentry_zh_cn.md) — 负责 Fork 的新模式/数量门禁。
- [Output Token 路由](output-token-routing_zh_cn.md) — 负责独立的大输出门禁。
- [决策上下文生成](decision-context-generation_zh_cn.md) — 负责有界决策上下文的生成与审阅。

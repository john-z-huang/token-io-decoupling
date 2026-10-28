# Coding Output Token 路由

[English](output-token-routing.md) | [简体中文](output-token-routing_zh_cn.md)

本文档负责独立判断 Root 直接输出是否会产生大量 Output Token，以及由此产生的 Root/子代理执行边界。不选择执行主体或具体子代理。

## 通用规范

### 独立的大输出判断

根据任务、交付形态和预期输出量评估请求本身。不得使用无关 transcript 大小、任意数值阈值或未经测量的 Token 使用量结论。证据不足以支持是/否判断时，暂停并交 Root 审阅。

用户明确指定谁生成输出或是否生成输出时，应优先遵循用户指令，并跳过相应建议请求。只有用户指令尚未决定该输出路由时，才在 Root 即将直接生成形态或体量可能较大的每项输出前进行此独立评估。评估不要求先选出执行主体或已有可用子代理；它只判断这项直接输出。`no` 允许 Root 在满足其他所有门禁后生成所请求输出。在路由未由用户决定时，`yes` 表示 Root 不得立即物化大输出：Multi-Agent 模式下选择当前会话中已经存在、空闲且合适的子代理；没有空闲者时，等待或挂起，直至有合适者空闲。此评估绝不创建子代理。Single-Agent 模式下不得臆造子代理或任务重构流程；应挂起并报告当前 Session 拓扑无法执行该输出。

用户指令未决定路由时，是/否判断与执行主体选择相互独立。若下游建议请求依赖的决策上下文缺失或不可用，不得伪造上下文或继续发送请求；若已核实事实足够，Root 仍可直接依据本文作出评估，否则应挂起等待审阅。建议仅供参考，不能推翻明确用户指令、派发工作或授权任何影响。

### Output Token Decisions 指令

用户明确的执行指令或输出路由指令已决定操作时，跳过本建议并在高优先级门禁约束下遵循指令。否则，判断 Root 直接输出请求是否会产生大量 Output Token。只使用请求形态、预期输出量、审阅后的任务上下文、当前模式及本文规范。不得设定数值阈值，也不得将无关输入大小当成代理。选择 `yes`、`no` 或 `insufficient_evidence`。事实冲突、未说明请求输出描述，或不足以支持是/否判断时，选择 `insufficient_evidence` 供 Root 审阅。未确定路由时，`yes` 不代表已有子代理或子代理空闲。

### Output Token 选项说明

#### yes

直接输出请求会为 Root 产生大量 Output Token。若用户指令尚未决定路由，Root 必须使用空闲且合适的当前会话子代理，或等待/挂起。若当前模式为 Single-Agent，应挂起并报告拓扑边界；不得臆造子代理或任务重构行为。

#### no

根据提供的任务事实，请求不属于大量 Output Token 输出。Root 只有检查其他所有适用门禁后才能执行。

#### insufficient_evidence

请求形态、预期输出量或任务证据不完整或冲突，无法支持是/否判断。Root 审阅事实和当前 owner；不得默认是或否。

### 操作边界

使用建议前，Root 将其事实、上下文和政策哈希与当前证据比对，并核验当前模式。得到 `yes` 后，Root 还须独立核验所选子代理的当前身份、适任性、权限和空闲状态，之后才可派发。忙碌子代理尚未准备好接受派发。没有合适的空闲子代理时，保留等待/挂起状态；不得为满足此输出路由而新建子代理。建议不得改变明确用户执行指令。

## Codex CLI / ChatGPT Desktop 特别优化指令

当工具可用且用户尚未明确决定输出路由时，单独调用公共 Decisions 工具 `workflow_assess_output_tokens`，传入有界、当前任务事实并为本次调用显式允许外发数据。`yes` 进入空闲子代理选择或等待/挂起；`no` 允许 Root 继续普通门禁。该请求本身不执行任何动作，其结果不能推翻明确用户指令。

## Claude Code CLI / Claude Desktop 特别优化指令

当前没有适用于此概念的特别优化；遵循通用规范。

## 相关概念

- [任务执行主体分配](task-assignment_zh_cn.md) — 负责 Root/子代理执行主体与现有子代理选择。
- [Session 模型](session-model_zh_cn.md) — 负责 Session 身份和拓扑语义。
- [委派数量门禁](delegation-mode-count-gate_zh_cn.md) — 负责锁定子代理容量和显式扩展。
- [委派模式重入](delegation-mode-reentry_zh_cn.md) — 负责 Fork 的新模式选择。
- [委派状态记录](delegation-state-record_zh_cn.md) — 负责当前 allocation 身份和状态。
- [决策上下文生成](decision-context-generation_zh_cn.md) — 负责有界决策上下文的生成与审阅。

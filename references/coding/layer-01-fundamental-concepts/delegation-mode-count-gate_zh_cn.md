# Coding 委派数量门禁

[English](delegation-mode-count-gate.md) | [简体中文](delegation-mode-count-gate_zh_cn.md)

本文档负责多代理子 Agent 数量的选择、锁定和数量预算边界。它消费已选择的模式和状态记录；不定义模式选择、重新进入、子 Agent 创建或生命周期。

## 通用规范

### 数量选择和锁定

选择 Multi-Agent Session 后，采用用户明确给出的正整数子代理数量；否则锁定 1 个子代理的预算。首次 Coding 指令默认选择 Multi-Agent 时也应用此默认值。本 Skill 不限制初始正整数数量的最大值。用户选择了自定义数量选项、但遗漏或给出无效数量时，只提出一个聚焦的补充问题并保持 Mode gate 未放行；不得替换为 1。数量有效时不再提出额外数量问题。其他明确数量无效时，保持路线未放行，直到用户给出有效正整数；不得解释为同意其他数量。数量是完整宿主 Session 生命周期内的子代理总预算，而非每轮、每任务、每阶段或每职责的数量。

路线放行前锁定数量，在父级状态记录中预留恰好该数量的计划 allocation 名额。每个初始名额均使用 `agent: unbound`、`role: unassigned`、`slice_status: pending` 和 `lifecycle: pending`；预留名额不表示 Context、Decision 或具体 Slice 已经放行，也不会初始化子代理。预留本身不选择职责，也不因只预留一个名额就自动选择 Primary Output。当前任务上下文和 Decision 审阅完成后，由[子代理职责选择](child-role-selection_zh_cn.md)确定职责，再由分配 owner 将其记录到未分配名额中。只有角色和本次 Slice 均获放行，且输出属于代码/配置实现或本 Skill 指令/参考文档编写编辑，才可以创建对应子代理。普通非 Skill 文档不会触发或消耗预留名额；由根父级编写，包括同时存在代码修改的任务。每项独立职责消耗一个预留名额；复用不增加名额。数量锁定固定的是总预算，不是尚未绑定子代理名额的具体内容。

### 用户明确批准增加一个名额

如果没有未分配名额，且当前事实表明需要为不同且未占用的职责增加一个子代理，Root 可以向用户请求将锁定数量恰好增加一。模型建议、推断意图、针对其他变更的历史批准或 API 结果都不是用户批准。Root 必须审阅实际用户指令，并在受保护的预留事务中提供其 `SemanticRef` 或 `EvidenceRef`。只有所请求数量等于当前数量加一时，事务才可接受；它会在规范语义引用中保留旧数量来源、将新的用户批准记录为当前来源，并以单个原子事务增加一个名额并预留尚未占用的职责。操作回执记录批准证据及新旧数量。事实缺失、批准不清、职责已预留或创建，或现有批准约定不能表示该确切数量（其批准数量字段最多接受四）时，保留当前状态并停止；不得强行转换或拆分请求。用户明确指定的初始数量不受该批准字段上限约束。

增加名额不会仅凭预算选择职责、放行 Slice 或创建子代理。已有未分配名额时，应在现有数量和正常放行门禁内使用，无需预算批准。尚未创建子代理的 unbound 名额可由父级授权在当前数量内调整职责计划，但新职责必须未被占用。子代理一旦创建，其身份、名额和职责在本 Session 中永久绑定：不得回收或替换，包括通过 Fork 或 handoff successor。只有超过当前数量的额外子代理才需要上述确切的单名额用户批准，且必须为不同、未占用的职责，绝不允许借此替换已创建子代理。若所有受维护职责都已占用，批准不能授权重复职责。必需名额或能力不可用时阻塞依赖工作，不得默默更改数量。

## Codex CLI / ChatGPT Desktop 特别优化指令

目前没有针对该厂商的特别优化指令；遵循上述通用规范。

## Claude Code CLI / Claude Desktop 特别优化指令

目前没有针对该厂商的特别优化指令；遵循上述通用规范。

## 相关概念

- [Coding Delegation Mode Confirmation](delegation-mode-confirmation_zh_cn.md) — 定位根模式确认归属。
- [Coding Delegation Re-entry](delegation-mode-reentry_zh_cn.md) — 定位门禁重新进入归属。
- [Coding Delegation State Record](delegation-state-record_zh_cn.md) — 定位状态记录归属。
- [Coding Child Creation](delegation-child-creation_zh_cn.md) — 定位子 Agent 创建归属。
- [Coding Child Lifecycle](delegation-child-lifecycle_zh_cn.md) — 定位子 Agent 生命周期归属。
- [Coding Child Role Selection](child-role-selection_zh_cn.md) — 定位使用已批准容量的职责选择。

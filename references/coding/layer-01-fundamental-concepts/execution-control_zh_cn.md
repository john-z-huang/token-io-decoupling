# Coding Execution Control

本模块负责 Coding 执行规划：有界阶段、Decision Checkpoint、Interaction Slice 放行和执行阶段反馈。它假定当前工作流已经提供 Contract、角色/Session 上下文、运行环境能力和委派状态。本模块不决定模式、拓扑、Agent/Session 创建、分配、数量、复用、替换、例外、验证、文档、Git 或最终验收。

## 两级规划

输入侧职责定义目标、约束、架构决策、风险和验收标准。已分配的执行职责将批准的方向转换为有界的检查、实现和定向检查步骤。在单代理路线中，这些是当前 Session 的逻辑阶段；在多代理路线中，工作流分配的 Worker 只能执行已放行的 slice。

在实质性决策前需要项目事实时，使用有界 reconnaissance slice。执行者返回压缩事实、有证据支持的选项和未解决问题；输入侧职责选择方向并更新 Contract。Worker 可以决定如何在 slice 内执行已批准的方向，但不能自行批准新的语义或架构方向。

并行只适用于相互独立且不冲突的 slice。存在依赖、共享写入目标或有序结果时必须顺序放行。上下文传输和仅限父级的反馈遵循当前工作流提供的协议。

## Decision brief 与实现放行

对于不是简单、局部、低风险、明显、可逆且可机械验证的工作，第一次实质性执行 slice 前应准备简洁的 **Decision Brief**。它记录分析结果而不是 private chain-of-thought，至少应包含：

- `Problem`
- `Known facts`
- `Assumptions and unknowns`
- `Decision questions`
- `Solution envelope`
- `Risks`
- `Acceptance`
- `Stages and checkpoints`

如果仍有实质性决策未解决，只能放行 reconnaissance。返回后确认或否定假设，选择批准方向并放行实现。如果新证据改变实质性决策，应暂停当前方向并重新执行决策门禁。不得放行让一个执行者同时分析、选择、实现和验证未定方案的未解决组合指令。

## Interaction Slice

对于非简单工作，每次只放行一个 **Interaction Slice**。每个 slice 必须写明：

- `Objective`：必须产出的结果；
- `Authorized scope/mutations`：允许的路径、行为和写入；
- `Return conditions`：结束 slice 的证据或里程碑；
- `Unreleased boundary`：仍被阻塞的下一个子系统、风险域、语义选择或变更。

Slice 是控制单元，不是逐命令脚本。只要 Contract 和边界未变，执行者可以继续处理低决策密度的机械步骤；到达 return conditions 或跨越未放行边界前必须暂停。简单的快路径任务可以将实现和聚焦检查保留在一个 slice 中。

到达实质性边界时，使用压缩的 Control Checkpoint，只报告下一步决策所需的状态、发现、变更范围、验证、问题、所需动作和未放行边界。输入侧职责选择 `Continue`、`Amend` 或 `Stop`；`Continue` 只放行下一个有界 slice，`Amend` 必须在恢复前修改 Contract 或边界。在单代理路线中，这是内部推理暂停，不模拟发给自己的消息。

## 有界阶段与反馈

只有当下一阶段依赖高价值判断时才设置阻塞式 Decision Checkpoint，例如存在竞争的架构/API 选择、跨越公共接口/schema/兼容性/安全边界、调试出现实质分叉、范围将大幅扩大，或验证失败需要改变 Contract。

对于高不确定性工作，预先声明一组短小、能够产出证据的阶段。每个阶段以观察结果或决策边界结束，而不是命令列表。执行者在声明边界暂停；普通读取、局部编辑、formatter/lint 修复、直接测试修复和重复 compile/test 循环留在已批准阶段内。不要仅为了汇报低价值机械步骤增加 checkpoint 或执行 slice。

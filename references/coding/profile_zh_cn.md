# Coding Runtime Profile

本模块负责当前 Coding Flow 的模型绑定与 reasoning-effort 策略。它属于部署策略，不是 Token I/O Decoupling 架构本身。未来模型变化通常只应修改本文件，不应连带改写角色、上下文、checkpoint 或 Multimodal 的职责边界。

主 [`../../SKILL_zh_cn.md`](../../SKILL_zh_cn.md) 中的跨 Flow Profile 约束同时适用。

## Session 映射

启动 Coding Flow 时先确认当前 Code Agent 的模型身份，再映射职责到 Session：

- **当前 Agent 已明确是 `gpt-5.6-luna`**：进入 **Single-Agent Luna Mode**。当前 Session 同时承担 Input-side Reasoning Role 与 Primary Output Role，直接完成项目探索、实现、调试、机械验证和输出；不得仅为了双角色拓扑再创建或要求存在额外 Luna Primary Output Agent。由于该 Session 同时承担高价值推理职责，其常规物化工作保持 `reasoning_effort=xhigh`。
- **当前 Agent 不能明确确认自己是 `gpt-5.6-luna`**：按输入侧推理角色约束自身行为，并使用独立 `gpt-5.6-luna` 承担 Primary Output Role，保持正常双 Session Coding Flow。

角色与 Session 语义以 [`session-model_zh_cn.md`](session-model_zh_cn.md) 为准。

## Reasoning-effort 分级

- 正常双 Session Coding 中，独立 Primary Output Luna 默认使用 `reasoning_effort=xhigh`。一般需求开发、非平凡重构或调试、复杂测试/验证代码，以及其他需要较多实现判断的工作使用 `xhigh`；输出很长或项目规模很大本身不能作为继续提高强度的理由。
- 对主要工作是开发文档编写/修改、代码注释、简单单元测试、低风险机械性修改或其他有界辅助物化的任务，优先使用 `reasoning_effort=high`。额外的辅助性 Coding Worker 默认使用 `high`，除非其具体任务明确符合 `xhigh` 条件。
- 只有宿主明确支持对应档位，并且任务严格有界、语义风险低且容易机械验证时，才使用 `reasoning_effort=medium` 或更低强度。适合的例子包括：运行已经选定的 test/formatter/lint 并压缩结果、收集文件/路径元数据、精确搜索或提取、字面量替换、按明确模板做格式整理或更新生成表格。低于 `medium` 的档位原则上只用于只读工作或确定性的机械变换。不得把 Semantic Contract ownership、架构/产品判断、跨模块实现、复杂调试、复杂测试设计、公共 API/schema/权限变更交给这些轻量 Worker。

## 定向 max 升级

`reasoning_effort=max` 是异常升级手段，不是普通 Worker 默认配置。

只有某个具体事项已经由现有 `high`/`xhigh` Worker 反复失败、来回振荡或出现明确阻塞时，才使用 max。父 Agent 为该事项创建新的、范围严格收窄的 max Worker；条件允许时，原 Worker 先按照 [`context-exchange_zh_cn.md`](context-exchange_zh_cn.md) 定义的文件化 Context Exchange 机制，在 primary worktree 中写好可复用上下文与 handoff 文档，新 max Worker 读取这些内容后接手，而不是从零重新探索项目。

阻塞解除后，后续无关工作恢复正常 `xhigh`/`high` 档位，不让 max 继续成为默认值。

Single-Agent Luna Mode 只有在 fresh verification、真正并行、当前上下文明显失效/膨胀、存在明确独立隔离收益，或某个具体任务反复阻塞而需要定向 `max` 升级时才允许创建额外 Agent。项目探索、实现、测试、长输出或笼统的“任务复杂”本身不是例外理由。

## Profile 本地约束

- 不得把 Coding 中要求使用 Luna 的角色静默替换为其他模型。
- 若需要独立 Luna 角色但无法确认 `gpt-5.6-luna` 身份、无法显式选择该模型，或宿主无法满足当前 dispatch 所要求的 reasoning-effort 档位，则停止对应实质性 Coding 工作并简短报告阻塞。
- 纯只读、严格有界的诊断，在能够确认 Luna 身份但宿主无法设置 reasoning effort 时可以继续；不得因此把复杂项目状态工作回退给高级父模型，也不得把原本要求 `high` 或 `xhigh` 的任务静默降级给轻量强度。

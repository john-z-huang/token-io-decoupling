# OpenAI Coding Model Profile

本文件负责当前已验证 Coding 部署中的具体 OpenAI 模型绑定与 reasoning-effort 策略。它属于部署策略，不是 Token I/O Decoupling 架构。宿主专属操作由 active Host Adapter 提供；通用 Session 语义由 [`../../coding/session-model_zh_cn.md`](../../coding/session-model_zh_cn.md) 与 [`../../coding/runtime_zh_cn.md`](../../coding/runtime_zh_cn.md) 定义。

## 角色绑定与双角色 eligibility

启动 Coding Flow 时，应先通过 Host Adapter 确认当前 Session 的模型身份，再应用本 Profile：

- **Input-side Reasoning**：当前高级父模型/Session 负责高价值语义决策。
- **Primary Output**：本 OpenAI 部署要求的执行模型为 `gpt-5.6-luna`。
- **双角色 eligibility**：当前 Session 能明确确认自身为 `gpt-5.6-luna`，并且 Host 能在该 Session 满足当前任务要求的 reasoning-effort 档位时，本 Profile 声明当前 Session 同时可以承担 Input-side Reasoning 与 Primary Output；因此通用 Runtime 映射默认进入 **Single-Session Coding Mode**，除非存在需要额外 Session 的具体结构性理由。
- **正常双 Session 映射**：当前 Agent 不能明确确认自己是 `gpt-5.6-luna` 时，当前 Agent 只承担输入侧推理职责，并使用独立 `gpt-5.6-luna` Session 承担 Primary Output。

Single-Session Coding Mode 保持当前部署已有行为：当前 Luna 直接完成项目探索、实现、调试、机械验证与输出，不为了维持双角色形式再把普通工作委派给另一个 Luna。由于该 Session 同时承担高价值推理职责，其普通实质性物化使用 `reasoning_effort=xhigh`。

## Reasoning-effort 分级

- 正常双 Session Coding 中，独立 Primary Output Luna 默认使用 `reasoning_effort=xhigh`。一般需求开发、非平凡重构或调试、复杂测试/验证代码，以及其他需要在**已批准语义方案内进行较多执行判断**的工作使用 `xhigh`。这一强度档位不会把问题定义、架构选择、未解决的语义权衡或验收 ownership 转移给 Primary Output；输出很长或项目规模很大本身不能作为继续提高强度的理由。
- 对主要工作是开发文档编写/修改、代码注释、简单单元测试、低风险机械性修改或其他有界辅助物化的任务，优先使用 `reasoning_effort=high`。额外辅助 Coding Worker 默认使用 `high`，除非其具体任务明确符合 `xhigh` 条件。
- 只有 Host 明确支持对应档位，并且任务严格有界、语义风险低且容易机械验证时，才使用 `reasoning_effort=medium` 或更低强度。适合的例子包括运行已经选定的 test/formatter/lint 并压缩结果、收集文件/路径元数据、精确搜索或提取、字面量替换、按明确模板格式整理或更新生成表格。低于 `medium` 的档位原则上只用于只读工作或确定性机械变换。不得把 Semantic Contract ownership、架构/产品判断、跨模块实现、复杂调试、复杂测试设计、公共 API/schema/权限变更交给这些轻量 Worker。

## 定向 max 升级

`reasoning_effort=max` 是异常升级手段，不是普通 Worker 默认配置。

只有某个具体事项已经由现有 `high`/`xhigh` Worker 反复失败、来回振荡或出现明确阻塞时，才使用 max。父 Agent 为该事项创建新的、范围严格收窄的 max Worker；条件允许时，原 Worker 先按照 [`../../coding/context-exchange_zh_cn.md`](../../coding/context-exchange_zh_cn.md) 定义的文件化 Context Exchange 机制，在 primary worktree 中写好可复用上下文与 handoff 文档，新 max Worker 读取这些内容后接手，而不是从零重新探索项目。

阻塞解除后，后续无关工作恢复正常 `xhigh`/`high` 档位，不让 max 继续成为默认值。

当前 Luna Session 处于 Single-Session Coding Mode 时，只有 fresh verification、真正并行、当前上下文明显失效/膨胀、存在明确独立隔离收益，或某个具体任务反复阻塞而需要定向 `max` 升级时才允许创建额外 Agent。项目探索、实现、测试、长输出或笼统的“任务复杂”本身不是例外理由。

## Profile 约束

- 不得把本 Profile 绑定到 Luna 的 Coding 角色静默替换为其他模型。
- 若需要独立 Luna 角色但无法确认 `gpt-5.6-luna` 身份、无法显式选择该模型，或 Host 无法满足当前 dispatch 所要求的 reasoning-effort 档位，则停止对应实质性 Coding 工作并简短报告阻塞。
- 纯只读、严格有界的诊断，在能够确认 Luna 身份但 Host 无法设置 reasoning effort 时可以继续；不得因此把复杂项目状态工作回退给高级父模型，也不得把原本要求 `high` 或 `xhigh` 的任务静默降级给轻量强度。
- 不得仅因为高级父模型技术上也能实现代码，就推断其应吸收 Primary Output；上述绑定是为了 Token I/O 隔离而有意设置的部署策略。

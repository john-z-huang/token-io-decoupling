# Coding Flow

本 Flow 用于项目探索、规划、实现、重构、修复、代码/配置/文档物化、构建测试与调试等 Coding 场景。它保留 `token-io-decoupling` 已有的 Input-side Reasoning 与 Primary Output 两类逻辑职责，但逻辑角色不等于独立 Agent 实例；具体使用单 Session 还是多 Session，由当前模型 Profile 与真实隔离收益决定。普通 Coding 任务不得因为 Skill 同时支持 Multimodal Flow 而创建 Primary Observation Agent。

所有角色同时遵循 [`shared-protocols.md`](shared-protocols.md)。

## 架构角色

### 输入侧推理 Agent

负责高信息密度工作：理解用户意图与业务语义、做架构和风险判断、形成或修订 Semantic Contract、处理重大决策升级、执行语义验收，并向用户解释必要的推理级决策。

输入侧 Agent 不应承担主要用于展开既有决策的大体量输出，也不应默认摄入高体量、低决策密度的项目原始状态。

### Primary 输出角色

负责高体量项目探索、原始工具输出处理、语义压缩、局部执行计划、代码/文档/配置物化、编译测试、调试修复和机械验证。

承担 Primary Output Role 的 Agent 对项目原始信息采用渐进式读取：优先先看摘要、统计和相关路径，再按需展开具体文件、diff 或日志。它可以决定“怎么执行”，但不能自行改变已批准目标、架构、约束或验收标准。

## Luna Single-Agent Mode

当当前运行中的 Code Agent 能明确确认自身为 `gpt-5.6-luna` 时，Coding Flow 默认进入 **Single-Agent Luna Mode**：

- 当前 Session 同时承担 Input-side Reasoning Role 与 Primary Output Role，不创建、不中转到、也不要求存在额外 Luna Primary Output Agent。
- 角色边界仍作为逻辑执行纪律存在：先固化高价值目标、约束和验收，再渐进读取项目状态、实现、机械验证并做最终语义验收；不需要为了这些阶段制造 Agent handoff。
- 当前 Luna 对自身的普通探索、实现、测试、修复和输出属于同 Session 自执行，不构成 Dispatch，也不打印虚构的 self-dispatch。
- 项目规模大、修改文件多、输出长、需要 build/test/debug 或笼统的“任务复杂”都不是创建额外 Luna 的理由。

只有存在独立结构性收益时才允许额外 Agent，例如：

- 需要不受当前实现历史影响的 fresh verification；
- 需要真正并行，且各任务互不依赖、不会争用相同写入目标；
- 当前 Session 的上下文明显失效、冲突严重或膨胀到不再适合继续工作；
- 存在明确的独立上下文、权限或其他隔离需求，且收益高于 handoff 成本。

这些例外允许创建额外 Agent，但不得把 same-model delegation 恢复成普通 Coding 的默认路径。Multimodal Flow 的 Primary Observation Agent 具有独立的高体量视觉/时序 context ownership，不受本节“普通 Coding 默认单 Session”规则削弱。

## Context Firewall

在正常双 Session Coding Flow 中，输入侧 Agent 不直接执行可能把大量项目原始状态带入自身上下文的开放式检查。`git diff`、大型 `git status`/日志、`find`、`rg`、文件树、构建/测试输出及同类高体量检查默认交给承担 Primary Output Role 的独立 Agent，由其读取、筛选并返回决策所需事实。

在 Single-Agent Luna Mode 中不存在跨 Session 的 Context Firewall；当前 Luna 直接承担 Primary Output Role 并消费必要项目状态，但仍必须使用渐进式读取和语义压缩，避免无目的地一次性倾倒整个项目、完整日志或无关 diff 到活跃上下文。

只有输出严格有界、明显很小且不会形成项目状态倾倒的元数据查询可由正常双 Session 模式的输入侧直接执行，例如 `pwd`、`git branch --show-current`、单个文件存在性检查等。判断依据是潜在原始输出体积，而不是命令名称本身。

独立 Primary Output Agent 返回诊断时默认进行语义压缩，不回传完整命令输出。只报告父 Agent 做下一步判断所需的事实、异常、相关路径和必要的小段证据；需要更多证据时按 Evidence-on-Demand 定向展开。

## Primary Execution Session 与 Session Affinity

同一连续 Coding 工作流默认维持一个 **Primary Execution Session**：

- 正常双 Session 模式下，它是独立的 Primary Luna；
- Single-Agent Luna Mode 下，它就是当前 Luna Session，不得为了获得所谓 Primary Session Affinity 再创建一个 Luna。

后续项目探索、实现、诊断、测试、修复和局部执行优先复用该 Primary Execution Session。复用的目的包括保留项目工作上下文、减少重复探索，并提高稳定 prompt prefix 的复用机会。不得宣称同一 Agent 必然命中 prompt cache，也不得宣称新 Agent 必然无法命中缓存。

只有存在前述独立验证、真正并行、上下文失效/容量压力或明确隔离收益时才新建执行 Session。Primary Execution Session 应保持 sticky but not immortal：优先复用，但允许在正确性、上下文容量或隔离需求要求时重建。

## 上下文共享与 Semantic Contract

### 简单、自包含任务

正常双 Session 模式使用精简提示：只给目标、必要约束、相关路径和需要返回的事实。能由 Primary Output Agent 自行读取的文件或项目状态，不由输入侧 Agent 大段复制到提示词中。

Single-Agent Luna Mode 不需要把当前 Agent 已知信息重新编码成发送给自己的提示；只在当前上下文中维护完成任务所需的最小稳定目标、约束、关键决策与验收标准。

### 复杂、强上下文任务

正常双 Session 模式中，当任务明显依赖大量会话、业务或项目背景时，优先把宿主能够安全共享的完整相关上下文交给 Primary Output Agent，并额外提供简短 Semantic Contract。这样避免输入侧 Agent 为重新描述已经存在的背景信息而产生大量输出，同时用 Contract 固化最终有效决策。

Single-Agent Luna Mode 继续使用 Semantic Contract 作为逻辑决策锚点，但不得为了形式完整把它当作 self-delegation prompt 再发送给自己。

Semantic Contract 的字段、amendment 与上下文阻塞规则以 [`shared-protocols.md`](shared-protocols.md) 为准。

## 两级规划与执行

输入侧职责负责语义级规划：目标、约束、架构决策、风险和验收标准。Primary Output 职责负责执行级规划，包括读取哪些文件、具体修改顺序、局部实现选择、编译测试和修复步骤。

正常双 Session 模式需要项目事实才能决策时，先让 Primary Output Agent 探索项目并返回压缩事实，再由输入侧 Agent 做高价值判断；输出侧发现会改变已批准目标、架构、约束或验收标准的新事实时，暂停相关方向并极简升级。

Single-Agent Luna Mode 在同一 Session 内按上述职责顺序工作，不制造角色间消息传递；发现重大新事实时直接修订当前有效 Contract 后继续。

并行只用于互不依赖且不会争用相同写入目标的任务；存在依赖、共享文件或前后结果关系时顺序执行。

## Coding Verification Boundary

Primary Output 职责负责机械验证和高体量证据处理，包括构建、测试、lint、formatter、类型检查、diff 检查、意外文件修改检查以及相关原始日志分析。

输入侧职责负责语义验收：用户目标是否满足、Semantic Contract 是否落实、业务/兼容性约束是否被破坏、机械验证报告的风险是否可接受。

正常双 Session 模式下，Primary Output Agent 只向输入侧 Agent 返回压缩后的验证结论，输入侧不默认重新读取完整 diff、测试日志或大型文件。Single-Agent Luna Mode 则由当前 Session 完成机械验证后直接进行语义验收，不为了验证边界创建额外 Agent；只有确有独立审查价值时才使用 fresh verifier。

## 输入侧输出纪律

在正常双 Session 模式下，输入侧 Agent 的输出以高信息密度为目标，只输出完成高级决策、Semantic Contract、决策升级、语义验收和必要用户交互所需的内容。

凡文本主要是在展开已经确定的信息，而不是产生新的高价值决策，应交给 Primary Output Agent，例如：

- 大段代码、完整文件或详细逐文件实现步骤；
- 长篇 README、设计文档、报告或说明；
- 大量项目现状复述、完整 diff/测试报告；
- 可以由输出侧 Agent 直接物化的长最终答复。

Single-Agent Luna Mode 中当前 Agent 已经承担 Primary Output Role，因此直接完成这些物化工作，不得为了遵守本节而把长输出再次委派给另一个 Luna。

当正常双 Session 模式的最终答复本身很长且宿主不能直接复用输出侧结果时，优先让 Primary Output Agent 把完整内容写入用户指定文件或工作区，输入侧 Agent 只返回极简摘要和位置，不重新生成长文。

## 与 Multimodal Flow 的边界

普通 Coding 任务始终留在本 Flow。只有当任务确实需要消费连续 GUI Observation、大量图片/截图、视频帧、设计参考或其他高体量视觉世界状态时，才切换或先进入 Multimodal Flow。

如果 Multimodal Flow 已完成视觉分析并需要修改代码，Coding Flow 只接收其窄 Handoff Contract；不得为了实现代码而把完整图片集、视频帧、Computer Use 历史、OCR 全文或视觉分析历史重新灌入 Primary Execution Session。

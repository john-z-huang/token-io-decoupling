# Coding Flow

本 Flow 用于项目探索、规划、实现、重构、修复、代码/配置/文档物化、构建测试与调试等 Coding 场景。它保留 `token-io-decoupling` 已有的双角色架构；普通 Coding 任务不得因为 Skill 同时支持 Multimodal Flow 而创建 Primary Observation Agent。

所有角色同时遵循 [`shared-protocols.md`](shared-protocols.md)。

## 架构角色

### 输入侧推理 Agent

负责高信息密度工作：理解用户意图与业务语义、做架构和风险判断、形成或修订 Semantic Contract、处理重大决策升级、执行语义验收，并向用户解释必要的推理级决策。

输入侧 Agent 不应承担主要用于展开既有决策的大体量输出，也不应默认摄入高体量、低决策密度的项目原始状态。

### Primary 输出 Agent

负责高体量项目探索、原始工具输出处理、语义压缩、局部执行计划、代码/文档/配置物化、编译测试、调试修复和机械验证。

Primary 输出 Agent 对项目原始信息采用渐进式读取：优先先看摘要、统计和相关路径，再按需展开具体文件、diff 或日志。它可以决定“怎么执行”，但不能自行改变已批准目标、架构、约束或验收标准。

## Context Firewall

输入侧 Agent 不直接执行可能把大量项目原始状态带入自身上下文的开放式检查。`git diff`、大型 `git status`/日志、`find`、`rg`、文件树、构建/测试输出及同类高体量检查默认交给 Primary 输出 Agent，由其读取、筛选并返回决策所需事实。

只有输出严格有界、明显很小且不会形成项目状态倾倒的元数据查询可由输入侧直接执行，例如 `pwd`、`git branch --show-current`、单个文件存在性检查等。判断依据是潜在原始输出体积，而不是命令名称本身。

Primary 输出 Agent 返回诊断时默认进行语义压缩，不回传完整命令输出。只报告父 Agent 做下一步判断所需的事实、异常、相关路径和必要的小段证据；需要更多证据时按 Evidence-on-Demand 定向展开。

## Primary 输出 Agent 与 Session Affinity

同一连续 Coding 工作流默认维持一个 Primary 输出 Agent；当前 OpenAI Profile 中即 Primary Luna。后续项目探索、实现、诊断、测试、修复和局部执行优先复用该 Agent，不为每个简单检查机械地创建新 Agent。

复用的目的包括保留项目工作上下文、减少重复探索，并提高稳定 prompt prefix 的复用机会。不得宣称同一 Agent 必然命中 prompt cache，也不得宣称新 Agent 必然无法命中缓存。

只有存在明确理由时才新建输出侧 Agent，例如：

- 需要不受实现历史影响的独立验证；
- Primary Agent 的上下文明显失效、冲突严重或膨胀到不再适合继续工作；
- 需要真正并行，且各任务互不依赖、不会争用相同写入目标；
- 当前任务与 Primary Agent 已有上下文无关，隔离收益明确高于复用收益。

Primary Agent 应保持 sticky but not immortal：优先复用，但允许在正确性、上下文容量或隔离需求要求时重建。

## 上下文共享与 Semantic Contract

### 简单、自包含任务

使用精简提示：只给目标、必要约束、相关路径和需要返回的事实。能由 Primary 输出 Agent 自行读取的文件或项目状态，不由输入侧 Agent 大段复制到提示词中。

### 复杂、强上下文任务

当任务明显依赖大量会话、业务或项目背景时，优先把宿主能够安全共享的完整相关上下文交给 Primary 输出 Agent，并额外提供简短 Semantic Contract。这样避免输入侧 Agent 为重新描述已经存在的背景信息而产生大量输出，同时用 Contract 固化最终有效决策。

Semantic Contract 的字段、amendment 与上下文阻塞规则以 [`shared-protocols.md`](shared-protocols.md) 为准。

## 两级规划与执行

输入侧 Agent 负责语义级规划：目标、约束、架构决策、风险和验收标准。需要项目事实才能决策时，先让 Primary 输出 Agent 探索项目并返回压缩事实，再由输入侧 Agent 做高价值判断。

Primary 输出 Agent 在收到 Semantic Contract 后自行完成执行级规划，包括读取哪些文件、具体修改顺序、局部实现选择、编译测试和修复步骤。输入侧 Agent 不预先展开文件级、行级或命令级长计划。

如果输出侧发现会改变已批准目标、架构、约束或验收标准的新事实，必须暂停相关方向，把事实、影响和需要的决策极简升级给输入侧 Agent。输入侧更新 Contract 后，再由同一个 Primary Agent 继续。

并行只用于互不依赖且不会争用相同写入目标的任务；存在依赖、共享文件或前后结果关系时顺序执行。

## Coding Verification Boundary

Primary 输出 Agent 负责机械验证和高体量证据处理，包括构建、测试、lint、formatter、类型检查、diff 检查、意外文件修改检查以及相关原始日志分析。它只向输入侧 Agent 返回压缩后的验证结论。

输入侧 Agent 负责语义验收：用户目标是否满足、Semantic Contract 是否落实、业务/兼容性约束是否被破坏、输出侧报告的风险是否可接受。输入侧 Agent 不默认重新读取完整 diff、测试日志或大型文件来重复机械验证。

需要确认某项结论时采用 Evidence-on-Demand。验证失败时优先让同一个 Primary 输出 Agent 修复并重新机械验证；重大语义偏差再升级给输入侧 Agent。

## 输入侧输出纪律

输入侧 Agent 的输出以高信息密度为目标，只输出完成高级决策、Semantic Contract、决策升级、语义验收和必要用户交互所需的内容。

凡文本主要是在展开已经确定的信息，而不是产生新的高价值决策，应交给 Primary 输出 Agent，例如：

- 大段代码、完整文件或详细逐文件实现步骤；
- 长篇 README、设计文档、报告或说明；
- 大量项目现状复述、完整 diff/测试报告；
- 可以由输出侧 Agent 直接物化的长最终答复。

输入侧 Agent 可以直接解释自己做出的关键决策；如果用户要求把这些决策展开成完整长文、代码或其他大体量产物，再交给 Primary 输出 Agent。

当最终答复本身很长且宿主不能直接复用输出侧结果时，优先让 Primary 输出 Agent 把完整内容写入用户指定文件或工作区，输入侧 Agent 只返回极简摘要和位置，不重新生成长文。

## 与 Multimodal Flow 的边界

普通 Coding 任务始终留在本 Flow。只有当任务确实需要消费连续 GUI Observation、大量图片/截图、视频帧、设计参考或其他高体量视觉世界状态时，才切换或先进入 Multimodal Flow。

如果 Multimodal Flow 已完成视觉分析并需要修改代码，Coding Flow 只接收其窄 Handoff Contract；不得为了实现代码而把完整图片集、视频帧、Computer Use 历史、OCR 全文或视觉分析历史重新灌入 Primary 输出 Agent。
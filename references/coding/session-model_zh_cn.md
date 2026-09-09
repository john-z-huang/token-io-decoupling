# Coding Session Model

本模块负责 Coding Flow 的角色定义、Session 拓扑、Context Firewall 与 Primary Execution Session Affinity。具体 Host/模型 eligibility 与运行参数单独通过 [`runtime_zh_cn.md`](runtime_zh_cn.md) 解析。

所有角色同时遵循 [`../shared-protocols_zh_cn.md`](../shared-protocols_zh_cn.md)。

## 架构角色

### 输入侧推理 Agent

负责高信息密度工作：理解用户意图与业务语义、做架构和风险判断、形成或修订 Semantic Contract、处理重大决策升级、执行语义验收，并向用户解释必要的推理级决策。

输入侧 Agent 不应承担主要用于展开既有决策的大体量输出，也不应默认摄入高体量、低决策密度的项目原始状态。

### Primary 输出角色

负责高体量项目探索、原始工具输出处理、语义压缩、局部执行计划、代码/文档/配置物化、编译测试、调试修复和机械验证。

承担 Primary Output Role 的 Agent 对项目原始信息采用渐进式读取：优先先看摘要、统计和相关路径，再按需展开具体文件、diff 或日志。它可以决定“怎么执行”，但不能自行改变已批准目标、架构、约束或验收标准。

## Single-Session Coding Mode

只有 active Runtime Contract 同时确认以下条件时，Coding Flow 才进入 **Single-Session Coding Mode**：

- 所选 Model Profile 明确声明当前 Session 同时可以承担 Input-side Reasoning 与 Primary Output；
- Host 能在当前 Session 满足当前任务要求的运行参数；
- 不存在需要另一个 Session 的独立结构性收益。

此模式下：

- 当前 Session 同时承担两类 Coding 职责；不得仅为了维持双角色形式而创建、handoff 到或要求存在额外 Primary Output Agent；
- 角色边界仍作为逻辑执行纪律存在：先固化高价值目标、约束、决策和验收，再渐进读取项目状态、实现、机械验证并进行最终语义验收；
- 当前 Agent 自己的普通探索、实现、测试、修复和输出属于同 Session 自执行，不构成 Dispatch；不得打印虚构的 self-dispatch，也不得构造发给同一 Session 的提示词；
- 仓库规模大、修改文件多、输出长、需要 build/test/debug 或笼统的“任务复杂”都不是创建额外 Session 的理由。

只有存在独立结构性收益时才允许额外 Agent，例如：

- 需要不受当前实现历史影响的 fresh verification；
- 需要真正并行，且各任务互不依赖、不会争用相同写入目标；
- 当前 Session 的上下文明显失效、冲突严重或膨胀到不再适合继续工作；
- 存在明确的独立上下文、权限或其他隔离需求，且收益高于 handoff 成本。

所选 Model Profile 还可以为“某个具体任务反复阻塞”定义严格收窄的 escalation 例外。该例外以 [`runtime_zh_cn.md`](runtime_zh_cn.md) 与 active Profile 为准，不得把“更强模型或运行参数”本身当成普遍拆分 Session 的理由。

这些例外不得把 same-runtime delegation 恢复成普通 Coding 的默认路径。Multimodal Flow 继续保留自己的独立高体量 Observation ownership，不受 Coding 的同 Session 规则削弱。

## 正常双 Session Coding Mode

当 active Runtime Contract 声明当前 Session 可以承担 Input-side Reasoning、但不能承担 Primary Output，并且 Host 能创建或复用兼容的独立 Primary Output Session 时，使用正常双 Session 拓扑：

```text
当前父 Session
    └─ Input-side Reasoning

独立 Primary Execution Session
    └─ Primary Output
```

拆分的原因是 active deployment 对 Runtime eligibility 或上下文 ownership 的要求，而不是因为存在两个逻辑角色名称。具体模型选择和执行参数不属于本模块。

若无法按 active Runtime 创建所需独立 Session，不得静默退化为 Single-Session Coding Mode；应执行 active Profile 的 unavailable 规则。

## Context Firewall

在正常双 Session Coding Flow 中，输入侧 Agent 不直接执行可能把大量项目原始状态带入自身上下文的开放式检查。`git diff`、大型 `git status`/日志、`find`、`rg`、文件树、构建/测试输出及同类高体量检查默认交给承担 Primary Output Role 的独立 Agent，由其读取、筛选并返回决策所需事实。

Single-Session Coding Mode 不存在跨 Session 的 Context Firewall；当前 Session 直接承担 Primary Output Role 并消费必要项目状态，但仍必须使用渐进式读取和语义压缩，避免无目的地一次性倾倒整个项目、完整日志或无关 diff 到活跃上下文。

只有输出严格有界、明显很小且不会形成项目状态倾倒的元数据查询可由正常双 Session 模式的输入侧直接执行，例如 `pwd`、`git branch --show-current`、单个文件存在性检查等。判断依据是潜在原始输出体积，而不是命令名称本身。

独立 Primary Output Agent 返回诊断时默认进行语义压缩，不回传完整命令输出。只报告父 Agent 做下一步判断所需的事实、异常、相关路径和必要的小段证据；需要更多证据时按 Evidence-on-Demand 定向展开。

## Primary Execution Session 与 Session Affinity

同一连续 Coding 工作流默认维持一个 **Primary Execution Session**：

- 正常双 Session 模式下，它是 active Runtime 分配给 Primary Output Role 的独立 Session；
- Single-Session Coding Mode 下，它就是当前 Session；不得为了获得所谓 Primary Session Affinity 再创建一个 Session。

后续项目探索、实现、诊断、测试、修复和局部执行优先复用该 Primary Execution Session。复用的目的包括保留项目工作上下文、减少重复探索，并提高稳定 prompt prefix 的复用机会。不得宣称同一 Agent 必然命中 prompt cache，也不得宣称新 Agent 必然无法命中缓存。

只有独立验证、真正并行、上下文失效/容量恢复、明确隔离或 active Profile 定义的定向 escalation 场景才新建执行 Session。Primary Execution Session 应保持 sticky but not immortal：优先复用，但允许在正确性、上下文容量或隔离需求要求时重建。

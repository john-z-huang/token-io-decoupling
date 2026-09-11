# Coding Session Model

本模块负责 Coding Flow 的角色定义、Session 拓扑、Context Firewall 与 Primary Execution Session Affinity。具体 Host/模型 eligibility 与运行参数单独通过 [`runtime_zh_cn.md`](runtime_zh_cn.md) 解析。

所有角色同时遵循 [`../shared-protocols_zh_cn.md`](../shared-protocols_zh_cn.md)。

## 架构角色

### 输入侧推理 Agent

负责高信息密度工作：理解用户意图与业务语义，定义和拆解问题，识别假设与未知项，提出决策问题，按明确标准比较候选方向，做架构和风险判断，形成或修订 Semantic Contract，设计有界阶段、Interaction Slice 与阻塞式 checkpoint，设置自适应反馈频率，逐个放行 slice，处理重大决策升级，执行语义验收，并向用户解释必要的推理级决策。

在派发实质性执行前，输入侧 Agent 始终拥有问题模型、证据含义、未解决的语义权衡、批准的解决方案范围以及放行实现的决定权。项目证据体量大并不会改变这些职责。输入侧 Agent 可以要求收集证据和生成候选项，但必须由输入侧决定证据对用户目标意味着什么，以及某个方向是否已获批准。

在正常双 Session 执行期间，输入侧 Agent 还拥有交互频率和 slice 边界的决定权。它每次只批准一个 Interaction Slice，解释 Progress Signal，并对每个阻塞式 Control Checkpoint 回复 `Continue`、`Amend` 或 `Stop`（也可以先通过定向 Evidence-on-Demand 获取证据再决定）。不得只是等待长期独立运行的 Output Agent，也不得预先放行所有未来阶段。

输入侧 Agent 不应承担主要用于展开既有决策的大体量输出，也不应默认摄入高体量、低决策密度的项目原始状态。

### Primary 输出角色

负责高体量项目探索、原始工具输出处理、证据收集与语义压缩、在已批准语义方案内的执行级规划、代码/配置物化、实现修复以及临时的实现反馈检查。

承担 Primary Output Role 的 Agent 对源代码和项目原始信息采用渐进式读取：优先先看摘要、统计和相关路径，再按需展开具体文件或日志。它可以分析证据、提出有证据支持的候选项，也可以在当前 Interaction Slice 内决定如何执行已批准的方向，但不能自行批准或改变未解决的语义/架构决策、用户/业务权衡、目标、约束或验收标准。它执行的编译、lint、单元测试或窄范围集成检查只是用于指导局部修复的实现反馈，不是最终改动结果验证。它不执行非简单的仓库 Git 检查或操作；这些职责属于独立的 Documentation/Comments & Git Operations 角色。

每个独立 Coding Worker 都必须在已授权 slice 内发送极简 Progress Signal，在 slice 的 return conditions 或重大强制边界处返回压缩 Control Checkpoint，并在跨越 `Unreleased boundary` 前暂停。并行不会扩大 Worker 的 slice，也不会自动放行未来工作。

### Context Bootstrap/Refresh 职责

Context Bootstrap/Refresh 是按需的辅助职责，不是第五个核心角色，也不是强制的 Session 拓扑。只有达到 `execution-control_zh_cn.md` 中的选择阈值时，父级 Input-side Reasoning Agent 才创建或复用一个 Bootstrap Worker。该 Worker 构建或增量刷新有界、带 fingerprint 的 capsule，其中包含中性项目事实、准确 source pointer、policy-routing pointer 以及 freshness/invalidation 数据。它不负责问题定义、Semantic Contract 决策、实现、验证结论或文档物化，也不得递归委派。

Bootstrap Worker 独立读取完整的强制 Skill 与仓库指令；它的 capsule 只能补充这些指令，不能替代它们。下游 Worker（包括初始 verifier）可以通过定向只读暴露接收 capsule，然后直接读取点名的权威文件。独立验证意味着独立判断，不能把此前的 verifier 结论当作证据；不要求 verifier 从零重新发现稳定的项目布局和 policy routing。项目或 Skill 发生实质相关变化后，复用同一个 Bootstrap Worker 做增量 refresh。在同一个 task conversation 中，后续验证 slice 复用一个独立 verifier，并要求它针对每个新的实质性最终状态 fingerprint/epoch 独立重新评估；只有确实存在独立隔离需求时才创建额外 verifier，例如不兼容的环境/快照、不同的权限或安全域，或明确要求的独立审计。

### Change Verification Agent

负责 Primary Output 实现 slice 完成后的最终、独立改动验证。它接收最终项目状态、当前有效 Semantic Contract、验收标准、变更范围证据和临时实现检查，然后渐进检查相关 diff 与周边行为，并执行适当的整体检查，例如集成、回归、跨模块、系统或端到端测试。它返回压缩后的证据、覆盖缺口、失败和剩余风险；不负责架构或产品决策、语义验收或修复工作。

选择该角色时，Change Verification Agent 首先使用新的独立 Session，避免继承 Primary Output 的实现历史。其验证 slice 对产品代码、测试、文档、配置和 Git 状态保持只读。它消费 Documentation/Comments & Git Operations Agent 提供的变更范围清单和 Git 证据，然后独立验证内容与行为；也可以使用当前有界 Bootstrap capsule 作为事实/路由上下文，但必须独立判断所提供的最终状态和所需证据。不执行非简单 Git 查询或操作。临时测试/构建输出可由 Host 隔离。它不得递归委派。若发现需要实质修复，应由父级输入侧 Agent 将修复返回 Primary Output；修复后，父 Agent 应复用同一个 verifier，为新的验证 slice 和最终状态 fingerprint/epoch 重新独立评估验收矩阵，不能把此前结论作为证据。只有父 Agent 确认存在多个确实隔离的验证需求时，才创建额外 verifier，例如并发不兼容的环境/快照、不同的权限或安全域，或明确要求的独立审计。

当仓库提供累计的完整套件入口或等价 manifest 时，全新的 verifier 应先运行该入口，再做针对变更风险的定向分析；详细的验证资产、覆盖缺口和文档快路径规则由 Coding Verification Boundary 负责。verifier 报告缺口时仍保持只读，修复返回 Primary Output；针对修复后的 epoch 复用同一个 verifier，不要为每项检查创建新的 verifier。

### Documentation/Comments & Git Operations Agent

负责两类彼此独立的职责。第一类是验证通过后的、按需开发文档和代码注释物化：它接收最终已验证项目状态、当前有效 Contract、明确的文档/注释范围和压缩后的验证结论，只修改获准的文档与注释位置。第二类是所有非简单的项目级 Git 职责，包括仓库同步（`fetch`/`pull`）、分支和 worktree 生命周期、暂存、提交、历史整合（`rebase`/`merge`/`cherry-pick`）、冲突处理、reset/clean/stash、标签、远端配置、推送以及适用的 Issue/PR 交付。它只能在父 Agent 放行的 Git Interaction Slice 内检查或修改 Git 元数据与远端状态。

文档/注释 slice 与 Git slice 分别放行。只有在使用已批准内容完成明确获准的 Git 操作时，才允许进行 Git 冲突解决编辑；如果解决冲突需要新的产品、行为或语义决策，必须暂停，并将该决策或修复返回父级 Input-side Agent 与 Primary Output。除这一狭窄例外，它不得修改功能、测试、fixture、schema、生成行为或其他实现逻辑；也不负责最终改动验证或语义验收。英文与简体中文 Markdown 必须遵守仓库双语规则保持语义镜像。

当任一职责需要执行时，父级 Input-side Reasoning Agent 才创建和管理 Documentation/Comments & Git Operations Agent。它使用独立的有界上下文，对文档/注释和复杂 Git 工作均默认采用 active Profile 的 `high` effort 档位；不得递归委派。父 Agent 可以在实现前为同步或分支/worktree 准备放行 Git slice，在实现后为历史整合或冲突处理放行，也可以在最终语义验收后为提交、推送和 Issue/PR 交付放行。角色、Contract 或 Session Affinity 都不会授予授权：每个 slice 必须明确仓库/worktree/ref/remote 范围、允许的变更与外部副作用，以及 return conditions。

## Single-Session Coding Mode

只有 active Runtime Contract 同时确认以下条件时，Coding Flow 才进入 **Single-Session Coding Mode**：

- 所选 Model Profile 明确声明当前 Session 同时可以承担 Input-side Reasoning 与 Primary Output；
- Host 能在当前 Session 满足当前任务要求的运行参数；
- 不存在需要另一个 Session 的独立结构性收益。

此模式下：

- 当前 Session 同时承担 Input-side Reasoning 与 Primary Output 的实现/临时检查；不得仅为了维持双角色形式而创建、handoff 到或要求存在额外 Primary Output Agent；
- 角色边界仍作为逻辑执行纪律存在：先固化高价值目标、约束、决策和验收，再渐进读取项目状态、实现、运行临时反馈检查，在需要时取得独立改动验证，最后进行语义验收；
- 对有实质性的功能改动，当前 Session 不承担最终 Change Verification Agent 职责。实现完成后由输入侧 Agent 创建一个新的独立 verifier Session，并在同一个 task conversation 的后续验证 slice 中复用它；每个新的最终状态 fingerprint/epoch 都必须独立重新评估，不能把此前结论作为证据。额外 verifier Session 只能用于确实隔离的验证需求。验证通过后如有需要，还可创建独立 Documentation/Comments & Git Operations Agent；
- interaction slice 与 Continue/Amend/Stop 决策作为内部推理边界保留；不得向同一 Session 模拟发送 Progress Signal 或 Control Checkpoint 消息；
- 当前 Agent 自己的普通探索、实现、聚焦测试、修复和实现输出属于同 Session 自执行，不构成 Dispatch；不得打印虚构的 self-dispatch，也不得构造发给同一 Session 的提示词；
- 仓库规模大、修改文件多、输出长、需要 build/test/debug 或笼统的“任务复杂”都不是创建额外 Session 的理由。

只有存在独立结构性收益时才允许额外 Agent，例如：

- 首次需要不受当前实现历史影响的独立验证，之后在各验证 epoch 中复用该 verifier；
- 需要真正并行，且各任务互不依赖、不会争用相同写入目标；
- 当前 Session 的上下文明显失效、冲突严重或膨胀到不再适合继续工作；
- 存在明确的独立上下文、权限或其他隔离需求，且收益高于 handoff 成本。
- 需要在验证后隔离文档/注释物化，或隔离非简单 Git 操作，避免实现上下文继续承担这些职责。

所选 Model Profile 还可以为“某个具体任务反复阻塞”定义严格收窄的 escalation 例外。该例外以 [`runtime_zh_cn.md`](runtime_zh_cn.md) 与 active Profile 为准，不得把“更强模型或运行参数”本身当成普遍拆分 Session 的理由。

这些例外不得把 same-runtime delegation 恢复成普通 Coding 的默认路径。Multimodal Flow 继续保留自己的独立高体量 Observation ownership，不受 Coding 的同 Session 规则削弱。

## 正常双 Session Coding Mode

当 active Runtime Contract 声明当前 Session 可以承担 Input-side Reasoning、但不能承担 Primary Output，并且 Host 能创建或复用兼容的独立 Primary Output Session 时，使用正常双 Session 拓扑：

```text
当前父 Session
    └─ Input-side Reasoning

独立 Primary Execution Session
    └─ Primary Output

可选的独立 Change Verification Session（跨验证 epoch 复用）
    └─ Change Verification

可选的 Documentation/Comments & Git Operations Session
    └─ Documentation/Comments & Git Operations
```

第一个拆分的原因是 active deployment 对 Runtime eligibility 或上下文 ownership 的要求，而不是因为存在两个逻辑角色名称。可选的 verifier 拆分用于实质性改动的独立 fresh review 收益；Documentation/Comments & Git Operations 拆分用于验证后的文档隔离或非简单 Git 操作的明确隔离。具体模型选择和执行参数不属于本模块。

若无法按 active Runtime 创建所需独立 Session，不得静默退化为 Single-Session Coding Mode；应执行 active Profile 的 unavailable 规则。

## Context Firewall

在正常双 Session Coding Flow 中，输入侧 Agent 不直接执行可能把大量项目原始状态带入自身上下文的开放式检查。非简单 Git 检查（`status`、`diff`、日志、历史、远端状态）、同步、分支/worktree 变更、暂存、提交、rebase/merge、冲突处理、推送和远端/PR 操作都交给 Documentation/Comments & Git Operations Agent。Primary Output 处理源代码/配置探索和实现反馈，不执行非简单 Git 工作。Change Verification 消费新角色提供的变更范围清单和 Git 证据，并独立验证内容与行为。每个 Agent 都只读取、筛选并返回父 Agent 下一步决策所需事实。

Context Firewall 限制的是项目原始状态进入输入侧上下文，并不限制输入侧推理，也不转移决策 ownership。输入侧 Agent 仍必须定义问题、确定所需证据、解释压缩后的发现、在重大方向之间做选择，并放行下一阶段。

Single-Session Coding Mode 不存在跨 Session 的 Context Firewall；当前 Session 直接承担 Primary Output Role 并消费必要项目状态，但仍必须使用渐进式读取和语义压缩，避免无目的地一次性倾倒整个项目、完整日志或无关 diff 到活跃上下文。

只有输出严格有界、明显很小的只读元数据查询可由正常双 Session 模式的输入侧直接执行，例如 `pwd`、`git branch --show-current`、`git rev-parse --show-toplevel`、单个文件存在性检查等。任何读取 diff、状态集合、历史、远端状态或其他非简单仓库状态的 Git 查询，都属于 Documentation/Comments & Git Operations Agent。判断依据是潜在原始输出体积和仓库状态影响，而不是命令名称本身。

独立 Primary Output 或 Change Verification Agent 返回诊断时默认进行语义压缩，不回传完整命令输出。只报告父 Agent 做下一步判断所需的事实、异常、相关路径和必要的小段证据；需要更多证据时按 Evidence-on-Demand 定向展开。Documentation/Comments & Git Operations Agent 同样只返回其文档/注释变更范围、变更范围清单、Git 操作结果和相关检查。

## Primary Execution Session 与 Session Affinity

同一连续 Coding 工作流默认维持一个 **Primary Execution Session**：

- 正常双 Session 模式下，它是 active Runtime 分配给 Primary Output Role 的独立 Session；
- Single-Session Coding Mode 下，它就是当前 Session；不得为了获得所谓 Primary Session Affinity 再创建一个 Session。

后续项目探索、实现、诊断、测试、修复和局部执行优先复用该 Primary Execution Session。复用的目的包括保留项目工作上下文、减少重复探索，并提高稳定 prompt prefix 的复用机会。不得宣称同一 Agent 必然命中 prompt cache，也不得宣称新 Agent 必然无法命中缓存。

为选定的独立改动验证创建初始执行 Session，或因真正并行、上下文失效/容量恢复、明确的文档/注释或非简单 Git 操作隔离，或 active Profile 定义的定向 escalation 场景才新建执行 Session。在同一个 task conversation 中，后续验证 epoch 复用选定的 verifier；只有确实隔离的验证需求才创建额外 verifier。Primary Execution Session 应保持 sticky but not immortal：默认复用于实现和临时反馈，但允许在正确性、上下文容量或隔离需求要求时重建。选定的 verifier 与 Documentation/Comments & Git Operations Worker 均独立于 Primary Execution，不替代 Primary Execution Session。

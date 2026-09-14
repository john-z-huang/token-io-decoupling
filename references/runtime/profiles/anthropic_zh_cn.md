# Anthropic Coding Model Profile

本文件负责 Claude Code Coding 部署使用的具体 Anthropic 模型绑定与执行层策略。它属于部署策略，不是 Token I/O Decoupling 架构本身。宿主机制由 Claude Code Host Adapter 提供；通用 Session 语义由 [`../../coding/session-model_zh_cn.md`](../../coding/session-model_zh_cn.md) 与 [`../../coding/runtime_zh_cn.md`](../../coding/runtime_zh_cn.md) 定义。

本 Profile 面向 Claude Code + Anthropic API 模型族。其他 Claude Code provider 可能以不同方式解析 alias，或拥有不同模型可用性；除非实际 runtime 满足下述绑定，否则不得直接复用本 Profile。

## 角色绑定与执行层

启动 Coding Flow 时，先通过 Host Adapter 确认当前 Session 的实际 model identity，再应用本 Profile：

- **Input-side Reasoning**：当前高级 Claude 父 Session 负责高价值语义决策。本 Profile 假设主 Session 已选择适合高级推理的 Claude runtime；不得仅因为 Haiku-class 或其他轻量 runtime 也能写代码，就允许其自动承担 input-side responsibility。
- **实质 Primary Output**：要求使用的 Anthropic 执行模型为 **`claude-sonnet`**。
- **Change Verification**：选择该角色时，为该 task conversation 启动一个全新的独立 `claude-sonnet` Session 进行最终改动结果验证，然后复用该 verifier 执行后续验证 slice。每个新的最终状态 fingerprint/epoch 都必须独立重新评估；此前结论不能作为证据。只有确实存在独立隔离需求时才创建额外 verifier Session，例如不兼容的环境/快照、不同的权限或安全域，或明确要求的独立审计。
- **Documentation/Comments & Git Operations**：选择该角色时，使用独立的 `claude-sonnet` Session 负责获准的验证后文档/代码注释物化，以及所有非简单仓库 Git 操作。它负责同步、分支/worktree 操作、暂存、提交、历史整合、reset/clean/stash、冲突处理、标签、远端、推送和适用的 Issue/PR 交付；只有极小的只读 Git 元数据查询可以留在该角色之外。
- **Context Bootstrap/Refresh**：选择该职责时，使用独立或可复用的 **`claude-sonnet`** Worker 进行有界事实与 policy-routing capsule 物化，默认使用 `effort=medium`。确定性的 metadata/source-hash 或增量 refresh capsule 工作在仍可机械验证时，可以改用 **`claude-haiku`**；必须留在 Sonnet 上时使用 `effort=low`。语义解释仍由 Input-side Reasoning 负责。
- **轻量 Output / 辅助 Worker**：严格有界、低语义风险、易机械验证的工作，在独立 Worker 具有明确 model-tiering 收益时，应优先使用 **`claude-haiku`**。
- **Dual-role eligibility**：当前 Session 能明确确认自身为 `claude-sonnet`，并且 Host 能在同一 Session 满足当前任务要求的 Sonnet effort 时，本 Profile 声明该 Session 同时适配 Input-side Reasoning 与实质 Primary Output。通用 Runtime 因此进入 **Single-Session Coding Mode**，除非存在独立结构性拆分理由。
- **正常双 Session 映射**：当前高级父 Session 不是 `claude-sonnet` 时，父 Session 只承担输入侧推理职责，并创建/复用独立 `claude-sonnet` Primary Output subagent 承担实质执行。

本绑定有意使用 provider 的层级 alias `claude-sonnet` 与 `claude-haiku`，而不是固定版本 ID。Claude Code 会把每个 alias 解析为宿主当前提供的最新模型版本，因此本 Profile 无需修改本文件即可跟随产品当前的各层模型。这也意味着本 Profile 承诺的是**层级**保证——实质执行落在 Sonnet 层、轻量执行落在 Haiku 层——而不是某个具体版本。应在 Coding Flow 启动时记录每个 alias 实际解析到的版本，并在版本变化后重新执行采用检查。

Single-Session Coding Mode 描述的是**实质 Primary Execution Session**，不是禁止有价值的辅助模型分层。当前 Sonnet 层 Session 直接完成源代码/项目探索、实现、调试、临时聚焦检查和实现输出，不为了维持双角色形式再把普通工作委派给另一个 Sonnet Session。它不承担非简单 Git 操作。当某个有界任务适合低成本隔离并存在明确结构收益时，仍可创建 Haiku 辅助 Worker；该辅助派发不会把主执行拓扑变成“正常双 Session Primary Output 模式”。

Single-Session Coding Mode 不会取消验证与交付角色。对实质性功能改动，输入侧 Agent 仍会启动一个全新的独立 Change Verification Session，并在同一个 task conversation 的后续验证 epoch 中复用它；每个 epoch 都必须独立重新评估，不能沿用此前结论。只有确实存在独立隔离需求时才创建额外 verifier Session；需要文档或非简单 Git 工作时，还可创建独立的 Documentation/Comments & Git Operations Session。

## 先选模型层，再选 effort

本 Profile 先选择**模型层**，随后只应用该模型真实支持的 Runtime 控制项。

### 路由到 Haiku

当任务严格有界、语义风险低且易机械验证时，优先使用 `claude-haiku`。适合的工作包括：

- 有界 repo / file / symbol exploration 与事实 inventory，前提是不负责决定架构或产品语义；
- 运行已经选定的 build/test/lint/formatter/type-check，收集失败并把原始日志压缩成事实；
- 文件/路径元数据收集、精确搜索/提取、确定性格式整理、字面替换、generated-table update 及类似机械变换；
- 当目标语义已经由 Semantic Contract 固定时，做小范围文档/注释同步；
- 已经明确行为和预期 assertion 的简单单元测试物化；
- 对彼此独立的问题进行并行只读调查，结果由父级或 Sonnet 执行路径做机械/语义检查。

Haiku 是**有界执行器和证据 Worker**，不是更便宜的通用 Primary Output。不得让其承担 Semantic Contract、架构/产品判断、跨模块实现、非平凡调试、复杂测试设计、public API/schema/migration/permission 变更、安全敏感修改，或正确执行明显依赖大量自主判断的任务。

如果某个任务最初符合 Haiku 层，但执行中发现会改变目标、架构、兼容性、风险或 Acceptance 的歧义，应停止当前方向并把压缩事实返回父级。父级完成 Contract amendment 后，再决定下一阶段是否切换到 Sonnet。

### 路由到 Sonnet

一般 feature implementation、非平凡 refactor/debug、跨模块修改、复杂 test/verification logic、已批准 migration、兼容性敏感工作、安全敏感工作，以及其他需要较多实现判断的实质 Primary Output 使用 `claude-sonnet`。

无法明确确认任务是否真的低风险且易机械验证时，应优先使用 Sonnet，而不是扩张 Haiku 边界。

## Sonnet effort 分级

Claude Code 当前在 Sonnet 层支持 `low`、`medium`、`high`、`xhigh`、`max` effort。只有任务已经路由到 Sonnet 后，才应用 effort，并按任务实际难度选择档位：

- **`low`**：简单的文档修改和简单的代码编写——语义已经确定的文档/注释同步，以及推理深度需求很小的小范围明确代码修改。
- **`medium`**：一般开发。这是常规 feature implementation、一般 refactor/debug 和实现反馈测试代码的默认档位。
- **`high`**：困难任务——跨模块修改、非平凡调试、兼容性或安全敏感工作、已批准 migration、复杂 test/verification logic，以及已经在 `medium` 档位受阻的任务。

`xhigh` 不是本 Profile 的默认档位。原本会使用 `xhigh` 的工作按 `high` 处理；只有 `high` 反复失败的任务才使用下方定向 `max` 升级。

角色归属：

- **实质 Primary Output**：一般开发使用 `medium`；已放行任务属于简单文档修改或简单代码编写时使用 `low`；任务确实困难时使用 `high`。这一档位阶梯不会把问题定义、架构选择、未解决的语义权衡或验收 ownership 转移给 Primary Output；输出很长或项目规模很大本身不能作为升档理由。
- **Change Verification**：选择的 verifier 默认使用 `high`，因为它需要针对最终变更状态独立选择并解释整体检查。它只负责验证证据，不负责修复、架构决策或语义验收。
- **Documentation/Comments & Git Operations**：文档/注释物化使用 `low`；非简单仓库 Git 操作使用 `medium`，因为它属于常规操作而不是简单编辑。其文档写入范围排除功能与测试；其 Git 范围限制为明确放行的仓库/worktree/ref/remote 操作。不得用来弥补验证失败或自行做未经批准的产品决策。
- **其他辅助 Sonnet Worker**：默认使用 `medium`；只有具体任务确实困难时才升到 `high`，只有属于简单文档修改或简单代码编写时才降到 `low`。
- **定向升级**：`effort=max` 只用于某个范围严格收窄的任务已经让现有 Sonnet `high` Worker 反复失败、振荡或明确阻塞时。

Effort 名称只是宿主/Runtime 控制项，不是跨模型通用的能力单位；相同名称在不同模型上的标定不能直接等价比较。

## Haiku 推理控制边界

**不得**把 Sonnet 的 `low`/`medium`/`high`/`max` 规则机械复制给 Haiku。当前产品中 Haiku 层没有 effort surface，因此本 Profile 主要通过**任务 eligibility + 模型选择**控制 Haiku 的成本与能力边界，不虚构 Haiku effort tier。由于层级 alias 会跟随宿主当前版本，应把该 effort surface 当作需要重新确认的宿主 capability，而不是层级的永久属性：即使未来某个 Haiku 层版本支持 effort，本 Profile 也不会在没有显式修订的情况下授权把 Sonnet 的档位复制过去。

Haiku 层与 Sonnet 层在 Anthropic API 层的 thinking 语义也不同。本 Profile 不要求固定 thinking budget，也不人为定义 Haiku 对应的 effort 等价物。一个有界任务如果需要明显更强推理，应改路由到 Sonnet，而不是在 Haiku 上模拟 Sonnet effort。

## 定向 max escalation

`effort=max` 是 Sonnet 的异常升级，不是普通 Primary Output 默认配置，也不是 Haiku 配置。

只有现有 Sonnet `high` Worker 已经对某个具体事项反复失败、来回振荡或明确阻塞时，才创建一个新的、范围严格收窄的 `claude-sonnet` max-effort Worker。条件允许时，前任 Worker 先按照 [`../../coding/context-exchange_zh_cn.md`](../../coding/context-exchange_zh_cn.md) 在 primary worktree 写好可复用 context/handoff 文档，新 max Worker 读取这些内容后接手，而不是从零探索项目。

阻塞解除后，后续工作恢复常规 Sonnet `medium`/`high` 档位；如果新的后续任务独立满足 Haiku eligibility，也可以回到 Haiku 轻量层。

当前 Sonnet 层 Session 处于 Single-Session Coding Mode 时，只有初始选定的独立验证、验证后的文档/注释或非简单 Git 操作隔离、真正并行、当前上下文明显失效/膨胀、存在明确独立隔离收益、某个具体任务反复阻塞而需要定向 `max` 升级，**或有界 Haiku model tiering** 时才允许创建额外 Agent。后续验证 epoch 复用已选 verifier；额外 verifier Session 需要确实隔离的验证需求。仓库规模、长输出、build/test 工作或笼统“任务复杂”本身，不是把实质 Primary Output 再拆成另一个 Sonnet Session 的理由。

## Claude Code model substitution 边界

Claude Code 可能因为 organization `availableModels`、provider 限制、fallback chain 或 runtime availability 替换/切换所请求的 subagent model。这个宿主行为**不是**本 Profile 的 fallback。

由于本 Profile 绑定的是层级 alias 而不是固定版本，需要区分两类不同事件：

- **层级内版本漂移**：`claude-sonnet` 或 `claude-haiku` 解析到同一层级的更新版本。这是 alias 的预期行为，不属于 substitution；继续执行并记录新版本。
- **层级不匹配**：Sonnet 层的请求被 Haiku 层、Opus 层、其他层级或未知模型承接。这属于 capability mismatch，按下方 unavailable 规则处理。

每个独立且受 Profile 绑定的 Worker 都必须：

1. 请求其角色要求的层级 alias（`claude-sonnet` 或 `claude-haiku`）；
2. 只有 Sonnet 层确实要求 effort 时才请求对应 Sonnet effort；
3. Claude Code 能暴露实际 Runtime 时检查真实生效值，并记录每个 alias 解析到的具体版本；
4. 实际 model 与所选执行层不匹配时，不得静默把该 Worker 重新解释为“仍符合 Profile”；
5. Sonnet effort 被 clamp 到低于任务要求的档位时，按下方 unavailable rule 处理。

“工具调用没有报错”本身不足以证明请求的 Runtime 已真实生效，尤其在 non-interactive/background 场景中 clamp/substitution 可能不明显。

## Profile 约束与 unavailable handling

- 不得把实质 Primary Output `claude-sonnet` 静默替换成 Opus、Fable、Haiku 层模型或 inherited parent model。alias 解析到同一 Sonnet 层的更新版本属于预期行为，不是 substitution；解析到其他层级才是。
- 不得把 Haiku-tier Worker 静默换成 Sonnet 后仍宣称“低成本层成功执行”。Haiku 不可用时，父级可以在明确认识到低成本层不可用后，主动把这个有界任务 reroute 到 Sonnet；这属于显式策略选择，不是接受 Host fallback。
- 需要独立实质 Primary Output 但无法选择或确认 `claude-sonnet` 时，停止对应实质 Coding 或验证工作并简短报告 Runtime 阻塞。不得因为 verifier 绑定不可用就让 Primary Output 自行验证实质性改动。
- Sonnet 所需 effort 因 provider/组织 cap 无法真实应用时，停止受影响的实质任务，不得假设请求值已经生效。
- Haiku-eligible 任务无法使用 Profile 绑定的 Haiku 层时，可以在不违反 Context Firewall / role policy 的前提下留在当前已授权 Session，显式 reroute 到 Sonnet，或报告 capability/cost-tier mismatch；不得把未知 substituted model 当成等价 Haiku。
- 不得因为 Claude Code inherited/substituted 一个高级父模型，就把高体量实质项目状态工作重新放回父 Session。Token I/O 分离仍是有意部署策略。

## Provider 边界

Anthropic API 下，本 Profile 绑定 `claude-sonnet` 与 `claude-haiku` 两个层级 alias，具体版本由宿主决定。其他 provider 可能把同名 alias 解析为不同版本、使用不同 ID 或可用性，也可能根本不支持层级 alias，并在 context limit 与 thinking 控制上存在差异。不得在未核验实际 Runtime 的情况下假定 Amazon Bedrock、Google Cloud Agent Platform、Microsoft Foundry、LLM gateway 或 organization override 与本 Profile 兼容。

未来若要支持特定 provider，应新增独立 Profile 或经过明确验证的变体，而不是弱化当前精确绑定。
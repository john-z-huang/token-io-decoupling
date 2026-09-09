# Anthropic Coding Model Profile

本文件负责 Claude Code Coding 部署使用的具体 Anthropic 模型绑定与执行层策略。它属于部署策略，不是 Token I/O Decoupling 架构本身。宿主机制由 Claude Code Host Adapter 提供；通用 Session 语义由 [`../../coding/session-model_zh_cn.md`](../../coding/session-model_zh_cn.md) 与 [`../../coding/runtime_zh_cn.md`](../../coding/runtime_zh_cn.md) 定义。

本 Profile 面向 Claude Code + Anthropic API 模型族。其他 Claude Code provider 可能以不同方式解析 alias，或拥有不同模型可用性；除非实际 runtime 满足下述绑定，否则不得直接复用本 Profile。

## 角色绑定与执行层

启动 Coding Flow 时，先通过 Host Adapter 确认当前 Session 的实际 model identity，再应用本 Profile：

- **Input-side Reasoning**：当前高级 Claude 父 Session 负责高价值语义决策。本 Profile 假设主 Session 已选择适合高级推理的 Claude runtime；不得仅因为 Haiku-class 或其他轻量 runtime 也能写代码，就允许其自动承担 input-side responsibility。
- **实质 Primary Output**：要求使用的 Anthropic 执行模型为 **`claude-sonnet-5`**。
- **轻量 Output / 辅助 Worker**：严格有界、低语义风险、易机械验证的工作，在独立 Worker 具有明确 model-tiering 收益时，应优先使用 **`claude-haiku-4-5-20251001`**。
- **Dual-role eligibility**：当前 Session 能明确确认自身为 `claude-sonnet-5`，并且 Host 能在同一 Session 满足当前任务要求的 Sonnet effort 时，本 Profile 声明该 Session 同时适配 Input-side Reasoning 与实质 Primary Output。通用 Runtime 因此进入 **Single-Session Coding Mode**，除非存在独立结构性拆分理由。
- **正常双 Session 映射**：当前高级父 Session 不是 `claude-sonnet-5` 时，父 Session 只承担输入侧推理职责，并创建/复用独立 `claude-sonnet-5` Primary Output subagent 承担实质执行。

本绑定使用完整 model ID，而不是 `sonnet` / `haiku` alias。Claude Code alias 会因 provider 不同而解析到不同版本，也会随着产品更新指向新模型；本 Profile 有意要求显式 runtime identity，避免 alias 漂移静默改变部署语义。

Single-Session Coding Mode 描述的是**实质 Primary Execution Session**，不是禁止有价值的辅助模型分层。当前 Session 本身就是 Sonnet 5 时，可以直接承担实质探索、实现、调试、机械验证与输出；同时，当某个有界任务适合低成本隔离并存在明确结构收益时，仍可创建 Haiku 辅助 Worker。该辅助派发不会把主执行拓扑变成“正常双 Session Primary Output 模式”。

## 先选模型层，再选 effort

本 Profile 先选择**模型层**，随后只应用该模型真实支持的 Runtime 控制项。

### 路由到 Haiku 4.5

当任务严格有界、语义风险低且易机械验证时，优先使用 `claude-haiku-4-5-20251001`。适合的工作包括：

- 有界 repo / file / symbol exploration 与事实 inventory，前提是不负责决定架构或产品语义；
- 运行已经选定的 build/test/lint/formatter/type-check，收集失败并把原始日志压缩成事实；
- 文件/路径元数据收集、精确搜索/提取、确定性格式整理、字面替换、generated-table update 及类似机械变换；
- 当目标语义已经由 Semantic Contract 固定时，做小范围文档/注释同步；
- 已经明确行为和预期 assertion 的简单单元测试物化；
- 对彼此独立的问题进行并行只读调查，结果由父级或 Sonnet 执行路径做机械/语义检查。

Haiku 是**有界执行器和证据 Worker**，不是更便宜的通用 Primary Output。不得让其承担 Semantic Contract、架构/产品判断、跨模块实现、非平凡调试、复杂测试设计、public API/schema/migration/permission 变更、安全敏感修改，或正确执行明显依赖大量自主判断的任务。

如果某个任务最初符合 Haiku 层，但执行中发现会改变目标、架构、兼容性、风险或 Acceptance 的歧义，应停止当前方向并把压缩事实返回父级。父级完成 Contract amendment 后，再决定下一阶段是否切换到 Sonnet。

### 路由到 Sonnet 5

一般 feature implementation、非平凡 refactor/debug、跨模块修改、复杂 test/verification logic、已批准 migration、兼容性敏感工作、安全敏感工作，以及其他需要较多实现判断的实质 Primary Output 使用 `claude-sonnet-5`。

无法明确确认任务是否真的低风险且易机械验证时，应优先使用 Sonnet，而不是扩张 Haiku 边界。

## Sonnet effort 分级

Claude Code 当前对 Sonnet 5 支持 `low`、`medium`、`high`、`xhigh`、`max` effort。只有任务已经路由到 Sonnet 后，才应用 effort：

- **实质 Primary Output**：一般 feature implementation、非平凡 refactor/debug、复杂 test/verification code、已批准 Contract 内的 migration，以及其他需要较多实现判断的事项使用 `effort=xhigh`。
- **有界 Sonnet support work**：任务仍需要 Sonnet 级判断，但比常规 Primary Output 更窄时使用 `effort=high`，例如 focused technical document、非平凡但局部的测试，或不适合安全下放 Haiku 的有界实现。
- **更低 Sonnet effort**：`medium`/`low` 不再是那些本来可以安全交给 Haiku 的任务的默认降本手段。只有任务仍明确需要 Sonnet，但可以用较低推理深度换成本/延迟时才使用。
- **定向升级**：`effort=max` 只用于某个范围严格收窄的任务已经让现有 Sonnet `high`/`xhigh` Worker 反复失败、振荡或明确阻塞时。

Effort 名称只是宿主/Runtime 控制项，不是跨模型通用的能力单位；相同名称在不同模型上的标定不能直接等价比较。

## Haiku 推理控制边界

**不得**把 Sonnet 的 `high`/`xhigh`/`max` 规则机械复制给 Haiku。当前 Claude Code effort 支持列表不包含 Haiku 4.5，因此本 Profile 主要通过**任务 eligibility + 模型选择**控制 Haiku 的成本与能力边界，不虚构 Haiku effort tier。

Haiku 4.5 在 Anthropic API 层的 thinking 语义与 Sonnet 5 也不同。本 Profile 不要求固定 thinking budget，也不人为定义 Haiku 对应的 effort 等价物。一个有界任务如果需要明显更强推理，应改路由到 Sonnet，而不是在 Haiku 上模拟 Sonnet effort。

## 定向 max escalation

`effort=max` 是 Sonnet 的异常升级，不是普通 Primary Output 默认配置，也不是 Haiku 配置。

只有现有 Sonnet `high`/`xhigh` Worker 已经对某个具体事项反复失败、来回振荡或明确阻塞时，才创建一个新的、范围严格收窄的 `claude-sonnet-5` max-effort Worker。条件允许时，前任 Worker 先按照 [`../../coding/context-exchange_zh_cn.md`](../../coding/context-exchange_zh_cn.md) 在 primary worktree 写好可复用 context/handoff 文档，新 max Worker 读取这些内容后接手，而不是从零探索项目。

阻塞解除后，后续工作恢复常规 Sonnet `xhigh`/`high` 档位；如果新的后续任务独立满足 Haiku eligibility，也可以回到 Haiku 轻量层。

当前 Sonnet 5 Session 处于 Single-Session Coding Mode 时，可以因为 fresh verification、真正并行、当前上下文明显失效/膨胀、明确隔离收益、定向 max escalation，**或有界 Haiku model tiering** 创建额外 Agent。仓库规模、长输出、build/test 工作或笼统“任务复杂”本身，不是把实质 Primary Output 再拆成另一个 Sonnet Session 的理由。

## Claude Code model substitution 边界

Claude Code 可能因为 organization `availableModels`、provider 限制、fallback chain 或 runtime availability 替换/切换所请求的 subagent model。这个宿主行为**不是**本 Profile 的 fallback。

每个独立且受 Profile 绑定的 Worker 都必须：

1. 请求其执行层要求的准确模型（`claude-sonnet-5` 或 `claude-haiku-4-5-20251001`）；
2. 只有 Sonnet 层确实要求 effort 时才请求对应 Sonnet effort；
3. Claude Code 能暴露实际 Runtime 时检查真实生效值；
4. 实际 model 不再匹配所选执行层时，不得静默把该 Worker 重新解释为“仍符合 Profile”；
5. Sonnet effort 被 clamp 到低于任务要求的档位时，按下方 unavailable rule 处理。

“工具调用没有报错”本身不足以证明请求的 Runtime 已真实生效，尤其在 non-interactive/background 场景中 clamp/substitution 可能不明显。

## Profile 约束与 unavailable handling

- 不得把实质 Primary Output `claude-sonnet-5` 静默替换成 Opus、Haiku、Fable、其他 Sonnet 版本或 inherited parent model。
- 不得把 Haiku-tier Worker 静默换成 Sonnet 后仍宣称“低成本层成功执行”。Haiku 不可用时，父级可以在明确认识到低成本层不可用后，主动把这个有界任务 reroute 到 Sonnet；这属于显式策略选择，不是接受 Host fallback。
- 需要独立实质 Primary Output 但无法选择或确认 `claude-sonnet-5` 时，停止对应实质 Coding 工作并简短报告 Runtime 阻塞。
- Sonnet 所需 effort 因 provider/组织 cap 无法真实应用时，停止受影响的实质任务，不得假设请求值已经生效。
- Haiku-eligible 任务无法使用准确 Haiku 绑定时，可以在不违反 Context Firewall / role policy 的前提下留在当前已授权 Session，显式 reroute 到 Sonnet，或报告 capability/cost-tier mismatch；不得把未知 substituted model 当成等价 Haiku。
- 不得因为 Claude Code inherited/substituted 一个高级父模型，就把高体量实质项目状态工作重新放回父 Session。Token I/O 分离仍是有意部署策略。

## Provider 边界

Anthropic API 下，本 Profile 当前绑定 `claude-sonnet-5` 与仍处于 active 状态的 Haiku 4.5 完整 model ID `claude-haiku-4-5-20251001`。其他 provider 可能使用不同 ID、可用性、context limit、thinking 控制或 alias 映射。不得在未核验实际 Runtime 的情况下假定 Amazon Bedrock、Google Cloud Agent Platform、Microsoft Foundry、LLM gateway 或 organization override 与本 Profile 兼容。

未来若要支持特定 provider，应新增独立 Profile 或经过明确验证的变体，而不是弱化当前精确绑定。
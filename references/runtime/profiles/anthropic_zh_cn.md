# Anthropic Coding Model Profile

本文件负责 Claude Code Coding 部署使用的具体 Anthropic 模型绑定与 effort 策略。它属于部署策略，不是 Token I/O Decoupling 架构本身。宿主机制由 Claude Code Host Adapter 提供；通用 Session 语义由 [`../../coding/session-model_zh_cn.md`](../../coding/session-model_zh_cn.md) 与 [`../../coding/runtime_zh_cn.md`](../../coding/runtime_zh_cn.md) 定义。

本 Profile 面向 Claude Code + Anthropic API 模型族。其他 Claude Code provider 可能以不同方式解析 alias，或拥有不同模型可用性；除非实际 runtime 满足下述绑定，否则不得直接复用本 Profile。

## 角色绑定与 dual-role eligibility

启动 Coding Flow 时，先通过 Host Adapter 确认当前 Session 的实际 model identity，再应用本 Profile：

- **Input-side Reasoning**：当前高级 Claude 父 Session 负责高价值语义决策。本 Profile 假设主 Session 已选择适合高级推理的 Claude runtime；不得仅因为 Haiku-class 或其他轻量 runtime 也能写代码，就允许其自动承担 input-side responsibility。
- **Primary Output**：要求使用的 Anthropic 执行模型为 **`claude-sonnet-5`**。
- **Dual-role eligibility**：当前 Session 能明确确认自身为 `claude-sonnet-5`，并且 Host 能在同一 Session 满足当前任务要求的 effort 时，本 Profile 声明该 Session 同时适配 Input-side Reasoning 与 Primary Output。通用 Runtime 因此进入 **Single-Session Coding Mode**，除非存在独立结构性拆分理由。
- **正常双 Session 映射**：当前高级父 Session 不是 `claude-sonnet-5` 时，父 Session 只承担输入侧推理职责，并创建/复用独立 `claude-sonnet-5` Primary Output subagent。

本绑定使用完整 model ID，而不是 `sonnet` alias。Claude Code 的 alias 会因 provider 不同而解析到不同版本，也会随着产品更新指向新的模型；本 Profile 有意要求显式 runtime identity，避免 alias 漂移静默改变部署语义。

Single-Session Coding Mode 与其他 Runtime 使用的是同一套 Core 模式。当前 Session 本身就是 Sonnet 5 时，直接完成项目探索、实现、调试、机械验证与输出，不为了保持双角色形式再把普通工作委派给另一个 Sonnet 5。

## Effort 分级

Claude Code + Sonnet 5 当前支持 `low`、`medium`、`high`、`xhigh`、`max` effort。本 Profile 按 Coding 任务类型映射如下：

- **Primary Output 实质工作**：一般 feature implementation、非平凡 refactor/debug、复杂 test/verification code、已批准 Contract 内的 migration，以及其他需要较多实现判断的事项使用 `effort=xhigh`。
- **有界辅助物化**：开发文档、代码注释、简单单元测试、低风险机械修改及类似有界 support work 优先使用 `effort=high`。额外辅助 Coding Worker 默认使用 `high`，除非其具体任务明确达到 `xhigh` 条件。
- **严格有界机械工作**：只有任务语义风险低、易机械验证时才使用 `effort=medium` 或 `low`，例如运行已选定检查并压缩结果、收集文件/路径元数据、精确搜索/提取、字面替换、确定性格式化或 generated-table update。`low` 原则上只用于短小的确定性/只读工作。
- **不得降低语义 ownership**：轻量 Worker 不承担 Semantic Contract、架构/产品判断、跨模块实现、复杂调试、复杂测试设计或 public API/schema/permission 变更。

Effort 名称只是宿主/Runtime 控制项，不是跨模型通用的能力单位。不得假设不同 Anthropic 模型或其他厂商中同名 effort 对应完全相同的底层推理预算。

## 定向 max escalation

`effort=max` 属于异常升级，不是普通 Primary Output 默认配置。

只有现有 `high`/`xhigh` Worker 已经对某个具体事项反复失败、来回振荡或明确阻塞时，才创建一个新的、范围严格收窄的 `claude-sonnet-5` max-effort Worker。条件允许时，前任 Worker 先按照 [`../../coding/context-exchange_zh_cn.md`](../../coding/context-exchange_zh_cn.md) 在 primary worktree 写好可复用 context/handoff 文档，新 max Worker 读取这些内容后接手，而不是从零探索项目。

阻塞解除后，后续工作恢复常规 `xhigh`/`high` 档位；不能因为一次 max escalation 成功，就让不相关工作继续长期使用 max。

当前 Sonnet 5 Session 处于 Single-Session Coding Mode 时，只有 fresh verification、真正并行、当前上下文明显失效/膨胀、明确隔离收益，或某个具体事项反复阻塞需要定向 max escalation 时才创建额外 Agent。项目探索、实现、测试、长输出或笼统的“任务复杂”都不是例外理由。

## Claude Code model substitution 边界

Claude Code 在 organization `availableModels` 或 provider 限制阻止所请求模型时，可能自动把 subagent 切换到其他 model。这个宿主行为**不是**本 Profile 的 fallback。

每个独立且受 Profile 绑定的 Worker 都必须：

1. 请求准确的 `claude-sonnet-5` 与所需 effort；
2. Claude Code 能暴露实际 Runtime 时检查真实生效值；
3. 实际 model 不是 `claude-sonnet-5` 时，不得把该 Worker 当作本 Profile 的 Primary Output；
4. 实际 effort 被 clamp 到低于任务要求的档位时，按下方 unavailable rule 处理。

“工具调用没有报错”本身不足以证明请求的 Runtime 已真实生效，尤其在 non-interactive/background 场景下，部分 clamp/substitution 可能不会以明显交互提示展示。

## Profile 约束与 unavailable handling

- 不得把 Primary Output 静默替换成 `opus`、`haiku`、`fable`、其他 Sonnet 版本或 inherited parent model。
- 需要独立 Primary Output 但无法选择或确认实际运行的是 `claude-sonnet-5` 时，停止对应实质性 Coding 工作并简短报告 Runtime 阻塞。
- 所需 effort 因模型/provider 不支持或组织级 cap 被压低而无法真实应用时，停止受影响的实质任务，不得假设请求值已经生效。
- 如果 model identity 已正确确认，但更高 effort 无法设置，纯只读、严格有界、确定性/低风险诊断可以继续；不得利用该例外进入实质 implementation。
- 不得因为 Claude Code 自动 inherited/substituted 一个高级父模型，就把高体量项目状态工作重新放回父 Session。Primary Output 绑定是 Token I/O 分离的有意部署策略。
- built-in Explore / Plan 可以用于适合的有界 one-shot research，但因为它们不提供满足 Session Affinity 所需的可恢复 agent identity，不得作为 sticky Primary Execution Session。

## Provider 边界

Anthropic API 下，当前 Claude Code 官方文档把 `sonnet` alias 解析为 Sonnet 5，把 `opus` alias 解析为 Opus 5；其他 provider 可能把同一 alias 映射到更旧版本。本 Profile 因此显式使用 `claude-sonnet-5`，不得在未验证实际 model identity 的情况下假定 Amazon Bedrock、Google Cloud Agent Platform、Microsoft Foundry、LLM gateway 或 organization model override 与本 Profile 兼容。

未来若要支持特定 provider，应新增独立 Profile 或经过明确验证的变体，而不是弱化当前 Profile 的精确绑定。
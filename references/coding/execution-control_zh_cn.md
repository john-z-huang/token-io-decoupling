# Coding Execution Control

本模块负责 Coding Flow 的规划职责、有界实现阶段、阻塞式 Decision Checkpoint、机械验证边界与输入侧输出纪律。

角色与 Session 语义来自 [`session-model_zh_cn.md`](session-model_zh_cn.md)；Semantic Contract 与 Evidence-on-Demand 等共享原语来自 [`../shared-protocols_zh_cn.md`](../shared-protocols_zh_cn.md)。

## 两级规划与执行

输入侧职责负责语义级规划：目标、约束、架构决策、风险和验收标准。Primary Output 职责负责执行级规划，包括读取哪些文件、具体修改顺序、局部实现选择、编译测试和修复步骤。

正常双 Session 模式需要项目事实才能决策时，先让 Primary Output Agent 探索项目并返回压缩事实，再由输入侧 Agent 做高价值判断；输出侧发现会改变已批准目标、架构、约束或验收标准的新事实时，暂停相关方向并极简升级。

Single-Agent Luna Mode 在同一 Session 内按上述职责顺序工作，不制造角色间消息传递；发现重大新事实时直接修订当前有效 Contract 后继续。

并行只用于互不依赖且不会争用相同写入目标的任务；存在依赖、共享文件或前后结果关系时顺序执行。多个独立 Agent 需要复用状态时，应使用 [`context-exchange_zh_cn.md`](context-exchange_zh_cn.md)，而不是由父 Agent 重新生成长篇摘要。

## 有界 Coding 阶段与 Decision Checkpoint

正常双 Session Coding 不得把“事件驱动进度反馈”理解成：复杂实现只派发一次，然后让独立 Primary Output Agent 一路跨过所有实质决策边界直到最终结束。对于存在明显语义不确定性的工作，输入侧 Agent 应在执行前或执行过程中划分少量 **有界 Coding 阶段**，并明确哪些阶段边界属于 **阻塞式 Decision Checkpoint**。

阻塞式 checkpoint 应选择性使用。适合设置在下一阶段确实依赖高价值判断的地方，例如：

- 项目探索发现多个相互竞争的架构方案或 API 边界选择；
- 实现将跨越多个模块、公共接口、schema、migration、兼容性边界或安全敏感行为；
- 调试进入重大分叉，不同修复方案具有不同产品或架构后果；
- 一个实现阶段已经完成，而下一阶段会显著扩大范围或做出难以回滚的修改；
- 机械验证暴露失败或回归，其可接受修复方式需要改变 Semantic Contract。

到达阻塞式 Decision Checkpoint 后，独立 Primary Output Agent 必须在进入下一实质阶段前**暂停**，只返回压缩 checkpoint 信息。可按需使用 `Status`、`Findings`、`Changed`、`Verification`、`Issue`、`Need` 等字段；无内容字段不机械补齐，也不得附完整 diff 或日志。输入侧 Agent 随后审查该 checkpoint，必要时通过 Evidence-on-Demand 获取最小证据，修订 Contract 或阶段指令，并明确放行下一有界阶段。

不得为低决策密度机械步骤创建阻塞式 checkpoint。普通文件读取、已批准设计内的局部代码修改、formatter/lint 修复、直接的测试修复、重复 compile/test 循环及其他执行细节继续留在 Primary Execution Session 中。“实现完成”或“开始验证”只有在预先声明为 blocking checkpoint，或新事实确实触发语义升级时，才必须暂停等待父级分析；否则它们可以只是普通事件驱动进度消息。

简单、局部、低风险任务仍允许一次 Dispatch 后完成实现与验证直至结束。Coding checkpoint 的目标是防止长时间无监督的语义漂移，而不是强制父子 Agent 高频 ping-pong，也不是复制 Multimodal Routine Interaction 明确避免的逐步遥控模式。

Single-Agent Luna Mode 只把相同的有界阶段纪律作为内部推理边界，不模拟发送给自己的 checkpoint 消息：到达已声明边界或出现重大新事实时，当前 Session 重新评估当前有效 Semantic Contract，完成必要高价值判断后再继续。

独立 Primary Output Agent 的推荐形式：

```text
Stage 1: 检查当前 auth/session 架构并找出最窄兼容修复；在需要修改 public API 或 persistence schema 前暂停
Checkpoint: Findings: refresh state 同时存在于 middleware 与 storage；Issue: 有两种可行 ownership；Need: 实现前选择 middleware-owned 或 storage-owned
Amendment: 保持 public API 稳定；选择 storage-owned state；批准 Stage 2：实现并运行定向测试，只有当验证要求修改 Contract 时再次暂停
```

## 受监督的操作阶段

对于高不确定性的正常双 Session Coding 工作——例如首次构建、陌生环境 bootstrap、工具链诊断，或外部依赖/替代执行路径——输入侧 Agent 应预先划分一组短小、能够产出证据的阶段。每个阶段应以明确的观察结果或决策边界结束，而不是枚举命令。

每个预先声明的阶段结束时，独立 Primary Output Agent 必须返回压缩 checkpoint 并暂停。输入侧 Agent 审查证据，必要时修订 Semantic Contract 或下一阶段指令，并明确放行下一阶段。独立 Primary Output Agent 还必须在变更系统或用户环境之前，以及发现权限或网络阻塞、偏离选定执行路径，或出现实质不同修复/替代方案时立即 checkpoint。

已批准阶段内的低价值命令、日志和机械重试留在独立 Primary Output Agent 的上下文中。本规则不要求逐命令汇报或固定频率的无信息心跳，也不强制所有 Coding 任务都拆成小阶段：已知、低风险且易于机械验证的操作仍可从执行连续到验证。

## Coding Verification Boundary

Primary Output 职责负责机械验证和高体量证据处理，包括构建、测试、lint、formatter、类型检查、diff 检查、意外文件修改检查以及相关原始日志分析。

输入侧职责负责语义验收：用户目标是否满足、Semantic Contract 是否落实、业务/兼容性约束是否被破坏、机械验证报告的风险是否可接受。

正常双 Session 模式下，Primary Output Agent 只向输入侧 Agent 返回压缩后的验证结论，输入侧不默认重新读取完整 diff、测试日志或大型文件。Single-Agent Luna Mode 则由当前 Session 完成机械验证后直接进行语义验收，不为了验证边界创建额外 Agent；只有确有独立审查价值时才使用 fresh verifier。

## 输入侧输出纪律

在正常双 Session 模式下，输入侧 Agent 的输出以高信息密度为目标，只输出完成高级决策、Semantic Contract、决策升级、语义验收和必要用户交互所需的内容。

当 Primary Output Agent 完成所分配的工作，并已在自己的 Session 中输出详细汇报后，输入侧 Agent 必须先分析该汇报，再压缩后回复用户。回复应仅包含必要的核心结果、变更范围、验证状态、未解决的问题或风险以及后续动作（如适用）。应引导用户前往输出侧 Agent 的上下文汇总查看原始详细汇报。输入侧 Agent 不得复制或大段重述该汇报；只有用户明确主动索取更多细节时才可扩展，且扩展内容必须严格限定在用户请求的范围内。除非用户提出此类请求，输入侧 Agent 在完成分析后始终保持精简输出。

凡文本主要是在展开已经确定的信息，而不是产生新的高价值决策，应交给 Primary Output Agent，例如：

- 大段代码、完整文件或详细逐文件实现步骤；
- 长篇 README、设计文档、报告或说明；
- 大量项目现状复述、完整 diff/测试报告；
- 可以由输出侧 Agent 直接物化的长最终答复。

Single-Agent Luna Mode 不存在可供用户跳转的独立输出侧 Session 或上下文汇总。当前 Agent 已经承担 Primary Output Role，因此直接完成这些物化工作；任务或用户确有需要时，可以直接提供必要的详细汇报。本节关于双 Session 的“压缩并引导查看”规则不要求其模拟独立的输出侧汇报，也不得为了遵守本节而把长输出再次委派给另一个 Luna。

当正常双 Session 模式的最终答复本身很长且宿主不能直接复用输出侧结果时，优先让 Primary Output Agent 把完整内容写入用户指定文件或工作区，输入侧 Agent 只返回极简摘要和位置，不重新生成长文。

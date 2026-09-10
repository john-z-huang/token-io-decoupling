# Coding Execution Control

本模块负责 Coding Flow 的规划职责、有界实现阶段、阻塞式 Decision Checkpoint、机械验证边界与输入侧输出纪律。

角色与 Session 语义来自 [`session-model_zh_cn.md`](session-model_zh_cn.md)；Semantic Contract 与 Evidence-on-Demand 等共享原语来自 [`../shared-protocols_zh_cn.md`](../shared-protocols_zh_cn.md)。

## 两级规划与执行

输入侧职责负责语义级规划：目标、约束、架构决策、风险和验收标准。Primary Output 职责负责执行级规划，包括读取哪些文件、具体修改顺序、局部实现选择、编译测试和修复步骤。

正常双 Session 模式需要项目事实才能决策时，先让 Primary Output Agent 探索项目并返回压缩事实，再由输入侧 Agent 做高价值判断；输出侧发现会改变已批准目标、架构、约束或验收标准的新事实时，暂停相关方向并极简升级。

Single-Session Coding Mode 在同一 Session 内按上述职责顺序工作，不制造角色间消息传递；发现重大新事实时直接修订当前有效 Contract 后继续。

并行只用于互不依赖且不会争用相同写入目标的任务；存在依赖、共享文件或前后结果关系时顺序执行。多个独立 Agent 需要复用状态时，应使用 [`context-exchange_zh_cn.md`](context-exchange_zh_cn.md)，而不是由父 Agent 重新生成长篇摘要。

## 派发前推理与实现放行

除简单、局部、低风险、方案明显、可逆且可机械验证的工作外，输入侧 Agent 必须在第一次实质性 Dispatch 前形成简洁的 **Decision Brief**。该 brief 记录输入侧分析结果，而不是 hidden chain-of-thought。至少应包含：

- `Problem`
- `Known facts`
- `Assumptions and unknowns`
- `Decision questions`
- `Preliminary solution envelope`
- `Risks`
- `Acceptance`
- `Stages and checkpoints`

不得要求或暴露私有思维链。brief 可以很短，但必须明确未解决的决策、所需证据和放行条件。

当 brief 仍缺少完成重大决策所需的项目事实时，第一次 Dispatch 只能是**有界 reconnaissance**。派发内容必须明确待回答的问题和待收集的证据，默认不修改文件或环境，只返回压缩后的发现、有证据支持的候选项和未解决问题，并在报告后暂停。Primary Output Agent 可以分析项目并提出候选方案，但不能替输入侧选择或放行语义/架构方向。

reconnaissance 完成后，输入侧 Agent 综合证据，确认或推翻假设，选择批准方向，更新 Decision Brief 或 Semantic Contract，并显式放行实现阶段。如果新证据改变了重大决策，必须在继续前暂停并重新执行这一推理门槛。Single-Session Coding Mode 以内部推理边界执行同样的门槛，不创建虚假的 self-dispatch。

当重大语义、架构、兼容性、安全、schema 或公共接口决策仍未解决时，不得派发宽泛的组合式指令，例如“分析问题、选择最佳方案、实现并验证”。简单快路径任务仍可一次 Dispatch 完成实现与验证，但前提是批准方向明显且结果可机械验证。

## Interaction Slice 与自适应反馈

对于正常双 Session Coding 中的非简单工作，输入侧 Agent 每次只批准一个 **Interaction Slice**。每个 slice 必须说明：

- `Objective`：本 slice 必须产出的结果；
- `Authorized scope/mutations`：slice 内允许访问的路径、行为和写入；
- `Return conditions`：结束 slice 的证据或里程碑；
- `Unreleased boundary`：仍被阻塞的下一个子系统、风险域、语义选择或变更。

独立 Output Agent 在已授权 slice 内保留低决策密度的自主性，但不能仅因能够预判下一步就跨越尚未放行的边界。slice 是控制单元，不是逐命令脚本。简单、局部、低风险、方向明显、可逆且可机械验证的工作仍可作为单个快路径 slice 一轮完成实现与验证。

使用两类反馈，二者都必须压缩且不得产生日志洪流：

- **Progress Signal** 是已授权 slice 内的非阻塞、极简里程碑报告。只要边界和 Contract 未改变，Output Agent 可以不等待回复而继续。不使用固定间隔心跳，也不逐命令汇报。
- **Control Checkpoint** 是 slice 结束或到达重大边界时的阻塞式会合点。Output Agent 必须在跨越边界前暂停，只返回与下一步决策有关的事实、变更、验证结果、问题和所需动作。

反馈频率是自适应的，不按固定墙钟间隔触发。至少在 reconnaissance 或 diagnosis 结束时、一个连贯行为/实现 slice 完成且下一步将进入另一个子系统或风险域前、验证产生重大结论时，以及出现任何 Contract、架构、范围、权限、安全或公共接口偏差时设置 Control Checkpoint。如果预计某个 slice 长时间没有自然里程碑，输入侧 Agent 必须在派发前定义中间 Progress Signal，或缩小该 slice。

每次 Control Checkpoint 后，输入侧 Agent 必须分析压缩证据并选择 `Continue`、`Amend` 或 `Stop`（也可以先通过 Evidence-on-Demand 获取证据再决定）。不得只确认收到，也不得预先放行后续所有阶段。`Continue` 只放行一个新说明的 slice；`Amend` 在恢复前修改 Contract 或 slice 边界；`Stop` 结束该方向。Single-Session Coding Mode 以内部推理边界执行同样顺序，不模拟父子消息。

## 有界 Coding 阶段与 Decision Checkpoint

正常双 Session Coding 不得把“事件驱动进度反馈”理解成：复杂实现只派发一次，然后让独立 Primary Output Agent 一路跨过所有实质决策边界直到最终结束。对于存在明显语义不确定性的工作，输入侧 Agent 应在执行前或执行过程中划分少量 **有界 Coding 阶段**，并明确哪些阶段边界属于 **阻塞式 Decision Checkpoint**。

阻塞式 checkpoint 应选择性使用。适合设置在下一阶段确实依赖高价值判断的地方，例如：

- 项目探索发现多个相互竞争的架构方案或 API 边界选择；
- 实现将跨越多个模块、公共接口、schema、migration、兼容性边界或安全敏感行为；
- 调试进入重大分叉，不同修复方案具有不同产品或架构后果；
- 一个实现阶段已经完成，而下一阶段会显著扩大范围或做出难以回滚的修改；
- 机械验证暴露失败或回归，其可接受修复方式需要改变 Semantic Contract。

到达阻塞式 Decision Checkpoint（即 Interaction Slice 边界上的 Control Checkpoint）后，独立 Primary Output Agent 必须在进入下一实质阶段前**暂停**，只返回压缩 checkpoint 信息。可按需使用 `Status`、`Findings`、`Changed`、`Verification`、`Issue`、`Need` 等字段；无内容字段不机械补齐，也不得附完整 diff 或日志。输入侧 Agent 随后审查该 checkpoint，必要时通过 Evidence-on-Demand 获取最小证据，选择 `Continue`、`Amend` 或 `Stop`，并且最多明确放行下一个有界 slice。

不得为低决策密度机械步骤创建阻塞式 checkpoint。普通文件读取、已批准设计内的局部代码修改、formatter/lint 修复、直接的测试修复、重复 compile/test 循环及其他执行细节继续留在 Primary Execution Session 中。“实现完成”或“开始验证”只有在预先声明为 blocking checkpoint，或新事实确实触发语义升级时，才必须暂停等待父级分析；否则它们可以只是普通事件驱动进度消息。

简单、局部、低风险任务仍允许一次 Dispatch 后完成实现与验证直至结束。Coding checkpoint 的目标是防止长时间无监督的语义漂移，而不是强制父子 Agent 高频 ping-pong，也不是复制 Multimodal Routine Interaction 明确避免的逐步遥控模式。

Single-Session Coding Mode 只把相同的有界阶段纪律作为内部推理边界，不模拟发送给自己的 checkpoint 消息：到达已声明边界或出现重大新事实时，当前 Session 重新评估当前有效 Semantic Contract，完成必要高价值判断后再继续。

独立 Primary Output Agent 的推荐形式：

```text
Stage 1: 检查当前 auth/session 架构并找出最窄兼容修复；在需要修改 public API 或 persistence schema 前暂停
Checkpoint: Findings: refresh state 同时存在于 middleware 与 storage；Issue: 有两种可行 ownership；Need: 实现前选择 middleware-owned 或 storage-owned
Amendment: 保持 public API 稳定；选择 storage-owned state；批准 Stage 2：实现并运行定向测试，只有当验证要求修改 Contract 时再次暂停
```

## 受监督的操作阶段

对于高不确定性的正常双 Session Coding 工作——例如首次构建、陌生环境 bootstrap、工具链诊断，或外部依赖/替代执行路径——输入侧 Agent 应预先划分一组短小、能够产出证据的阶段。每个阶段应以明确的观察结果或决策边界结束，而不是枚举命令。

每个预先声明的阶段结束时，独立 Primary Output Agent 必须返回压缩 Control Checkpoint 并暂停。输入侧 Agent 审查证据，选择 `Continue`、`Amend` 或 `Stop`，必要时修订 Semantic Contract 或下一 slice 指令，并且最多明确放行下一阶段。独立 Primary Output Agent 还必须在变更系统或用户环境之前，以及发现权限或网络阻塞、偏离选定执行路径，或出现实质不同修复/替代方案时立即 checkpoint。

已批准阶段内的低价值命令、日志和机械重试留在独立 Primary Output Agent 的上下文中。本规则不要求逐命令汇报或固定频率的无信息心跳，也不强制所有 Coding 任务都拆成小阶段：已知、低风险且易于机械验证的操作仍可从执行连续到验证。

## Coding Verification Boundary

Primary Output 职责负责机械验证和高体量证据处理，包括构建、测试、lint、formatter、类型检查、diff 检查、意外文件修改检查以及相关原始日志分析。

输入侧职责负责语义验收：用户目标是否满足、Semantic Contract 是否落实、业务/兼容性约束是否被破坏、机械验证报告的风险是否可接受。

在最终语义验收时，输入侧 Agent 必须把每项验收标准映射到 Primary Output 的压缩证据并给出明确判断：

```text
Acceptance criterion → evidence → input-side judgment
```

判断必须确认用户目标已满足、实现仍在批准的解决方案范围内、业务与兼容性约束保持不变、执行过程中没有偷偷引入未经批准的语义决策，并且验证留下的剩余风险可接受。这个基于证据的映射不要求重新读取完整 diff、完整测试日志或大型文件；只通过 Evidence-on-Demand 请求完成判断所需的最小额外证据。

正常双 Session 模式下，Primary Output Agent 只向输入侧 Agent 返回压缩后的验证结论，输入侧不默认重新读取完整 diff、测试日志或大型文件。Single-Session Coding Mode 则由当前 Session 完成机械验证后直接进行语义验收，不为了验证边界创建额外 Agent；只有确有独立审查价值时才使用 fresh verifier。

## 输入侧输出纪律

在正常双 Session 模式下，输入侧 Agent 的输出以高信息密度为目标，只输出完成高级决策、Semantic Contract、决策升级、语义验收和必要用户交互所需的内容。

当 Primary Output Agent 完成所分配的工作，并已在自己的 Session 中输出详细汇报后，输入侧 Agent 必须先分析该汇报，再压缩后回复用户。回复应仅包含必要的核心结果、变更范围、验证状态、未解决的问题或风险以及后续动作（如适用）。应引导用户前往输出侧 Agent 的上下文汇总查看原始详细汇报。输入侧 Agent 不得复制或大段重述该汇报；只有用户明确主动索取更多细节时才可扩展，且扩展内容必须严格限定在用户请求的范围内。除非用户提出此类请求，输入侧 Agent 在完成分析后始终保持精简输出。

凡文本主要是在展开已经确定的信息，而不是产生新的高价值决策，应交给 Primary Output Agent，例如：

- 大段代码、完整文件或详细逐文件实现步骤；
- 长篇 README、设计文档、报告或说明；
- 大量项目现状复述、完整 diff/测试报告；
- 可以由输出侧 Agent 直接物化的长最终答复。

Single-Session Coding Mode 不存在可供用户跳转的独立输出侧 Session 或上下文汇总。当前 Agent 已经承担 Primary Output Role，因此直接完成这些物化工作；任务或用户确有需要时，可以直接提供必要的详细汇报。本节关于双 Session 的“压缩并引导查看”规则不要求其模拟独立的输出侧汇报，也不得仅为了委派长输出而创建另一个 same-runtime Session。

当正常双 Session 模式的最终答复本身很长且宿主不能直接复用输出侧结果时，优先让 Primary Output Agent 把完整内容写入用户指定文件或工作区，输入侧 Agent 只返回极简摘要和位置，不重新生成长文。

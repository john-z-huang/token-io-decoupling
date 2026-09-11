# Coding Execution Control

本模块负责 Coding Flow 的规划职责、有界实现阶段、阻塞式 Decision Checkpoint、实现/最终验证边界、Documentation/Comments & Git Operations 放行门槛与输入侧输出纪律。

角色与 Session 语义来自 [`session-model_zh_cn.md`](session-model_zh_cn.md)；Semantic Contract 与 Evidence-on-Demand 等共享原语来自 [`../shared-protocols_zh_cn.md`](../shared-protocols_zh_cn.md)。

## 两级规划与执行

输入侧职责负责语义级规划：目标、约束、架构决策、风险和验收标准。Primary Output 职责负责实现的执行级规划，包括读取哪些源代码/配置文件、具体修改顺序、局部实现选择、临时聚焦检查和修复步骤。选择 Change Verification 时，该职责负责独立最终检查的执行级规划；Documentation/Comments & Git Operations 职责负责验证后的有界文档/注释物化规划，以及所有非简单仓库 Git 操作的规划。输入侧职责负责每个 slice 的授权与放行，该 Worker 只执行获准 slice 明确包含的文档或 Git 操作。

正常双 Session 模式需要项目事实才能决策时，先让 Primary Output Agent 探索项目并返回压缩事实，再由输入侧 Agent 做高价值判断；输出侧发现会改变已批准目标、架构、约束或验收标准的新事实时，暂停相关方向并极简升级。

Single-Session Coding Mode 在同一 Session 内按上述职责顺序工作，不制造角色间消息传递；发现重大新事实时直接修订当前有效 Contract 后继续。

并行只用于互不依赖且不会争用相同写入目标的任务；存在依赖、共享文件或前后结果关系时顺序执行。多个独立 Agent 需要复用状态时，应使用 [`context-exchange_zh_cn.md`](context-exchange_zh_cn.md)，而不是由父 Agent 重新生成长篇摘要。

### Context Bootstrap/Refresh 选择

Context Bootstrap/Refresh 是可选的辅助 slice。满足以下任一条件时，选择一个由父 Agent 管理且不递归委派的 Bootstrap Worker：预计至少有两个相互独立的下游 Worker；某个 fresh Worker 原本需要广泛探索项目并加载三个或更多路由 policy module；或相关 source set 大约超过 20k 原始字符 / 5k token-equivalents 且 capsule 会被复用。Single-Session 工作、一个小型 Worker、本地或仅文档的快路径、已知只涉及一两个文件，以及预期复用不超过建立成本的情况都应跳过。Bootstrap Worker 只能物化带 source fingerprint 与 freshness 数据的有界事实/policy-routing capsule，不负责语义决策或验证结论。上述规则是可测量的路由标准，不代表 billed token、cache 命中、成本、额度、延迟或质量方面的声明。

复用前，对照当前状态检查 capsule 的 `HEAD`/tree、tracked-delta fingerprint、列出的 source hash、相关未跟踪项目状态以及 active task/scope。任何实质性失配都要求父 Agent 复用同一个 Bootstrap Worker，增量刷新受影响的事实和 pointer；或者要求接收 Worker 直接读取点名的权威 source。任何 Worker 都不得依赖过时的 capsule 声明。Refresh 不满足独立的 Change Verification。

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

当重大语义、架构、兼容性、安全、schema 或公共接口决策仍未解决时，不得派发宽泛的组合式指令，例如“分析问题、选择最佳方案、实现并验证”。简单快路径任务仍可一次 Dispatch 完成实现和适用的聚焦检查，但前提是批准方向明显且结果可机械验证；若选择最终 verifier，仍必须单独 Dispatch。

## Interaction Slice 与自适应反馈

对于正常双 Session Coding 中的非简单工作，输入侧 Agent 每次只批准一个 **Interaction Slice**。每个 slice 必须说明：

- `Objective`：本 slice 必须产出的结果；
- `Authorized scope/mutations`：slice 内允许访问的路径、行为和写入；
- `Return conditions`：结束 slice 的证据或里程碑；
- `Unreleased boundary`：仍被阻塞的下一个子系统、风险域、语义选择或变更。

独立 Worker 在已授权 slice 内保留低决策密度的自主性，但不能仅因能够预判下一步就跨越尚未放行的边界。slice 是控制单元，不是逐命令脚本。简单、局部、低风险、方向明显、可逆且可机械验证的工作仍可作为单个快路径实现 slice；选择最终 verifier 时，其验证仍属于独立 slice。

使用两类反馈，二者都必须压缩且不得产生日志洪流：

- **Progress Signal** 是已授权 slice 内的非阻塞、极简里程碑报告。只要边界和 Contract 未改变，Worker 可以不等待回复而继续。不使用固定间隔心跳，也不逐命令汇报。
- **Control Checkpoint** 是 slice 结束或到达重大边界时的阻塞式会合点。Worker 必须在跨越边界前暂停，只返回与下一步决策有关的事实、变更、检查结果、问题和所需动作。

反馈频率是自适应的，不按固定墙钟间隔触发。至少在 reconnaissance 或 diagnosis 结束时、一个连贯行为/实现 slice 完成且下一步将进入另一个子系统或风险域前、验证产生重大结论时，以及出现任何 Contract、架构、范围、权限、安全或公共接口偏差时设置 Control Checkpoint。如果预计某个 slice 长时间没有自然里程碑，输入侧 Agent 必须在派发前定义中间 Progress Signal，或缩小该 slice。

每次 Control Checkpoint 后，输入侧 Agent 必须分析压缩证据并选择 `Continue`、`Amend` 或 `Stop`（也可以先通过 Evidence-on-Demand 获取证据再决定）。不得只确认收到，也不得预先放行后续所有阶段。`Continue` 只放行一个新说明的 slice；`Amend` 在恢复前修改 Contract 或 slice 边界；`Stop` 结束该方向。Single-Session Coding Mode 以内部推理边界执行同样顺序，不模拟父子消息。

## 有界 Coding 阶段与 Decision Checkpoint

正常双 Session Coding 不得把“事件驱动进度反馈”理解成：复杂实现只派发一次，然后让独立 Primary Output Agent 一路跨过所有实质决策边界直至最终验证结束。对于存在明显语义不确定性的工作，输入侧 Agent 应在执行前或执行过程中划分少量 **有界 Coding 阶段**，并明确哪些阶段边界属于 **阻塞式 Decision Checkpoint**。

阻塞式 checkpoint 应选择性使用。适合设置在下一阶段确实依赖高价值判断的地方，例如：

- 项目探索发现多个相互竞争的架构方案或 API 边界选择；
- 实现将跨越多个模块、公共接口、schema、migration、兼容性边界或安全敏感行为；
- 调试进入重大分叉，不同修复方案具有不同产品或架构后果；
- 一个实现阶段已经完成，而下一阶段会显著扩大范围或做出难以回滚的修改；
- Change Verification 暴露出只有修改 Semantic Contract 才能接受的失败或回归。

到达阻塞式 Decision Checkpoint（即 Interaction Slice 边界上的 Control Checkpoint）后，独立 Primary Output Agent 必须在进入下一实质阶段前**暂停**，只返回压缩 checkpoint 信息。可按需使用 `Status`、`Findings`、`Changed`、`Verification`、`Issue`、`Need` 等字段；无内容字段不机械补齐，也不得附完整 diff 或日志。输入侧 Agent 随后审查该 checkpoint，必要时通过 Evidence-on-Demand 获取最小证据，选择 `Continue`、`Amend` 或 `Stop`，并且最多明确放行下一个有界 slice。

不得为低决策密度机械步骤创建阻塞式 checkpoint。普通文件读取、已批准设计内的局部代码修改、formatter/lint 修复、直接的测试修复、重复 compile/test 循环及其他实现细节继续留在 Primary Execution Session 中。“实现完成”或“开始临时检查”只有在预先声明为 blocking checkpoint，或新事实确实触发语义升级时，才必须暂停等待父级分析；否则它们可以只是普通事件驱动进度消息。选定的最终 Change Verification 与 Documentation/Comments & Git Operations 阶段仍应在各自 slice 边界暂停。

简单、局部、低风险任务仍允许一次 Dispatch 后完成实现和适用的聚焦检查直至结束。若输入侧 Agent 选择最终 Change Verification，该验证仍必须单独 Dispatch；否则必须明确记录任务过于简单、没有 fresh review 的具体收益。Coding checkpoint 的目标是防止长时间无监督的语义漂移，而不是强制父子 Agent 高频 ping-pong，也不是复制 Multimodal Routine Interaction 明确避免的逐步遥控模式。

Single-Session Coding Mode 只把相同的有界阶段纪律作为内部推理边界，不模拟发送给自己的 checkpoint 消息：到达已声明边界或出现重大新事实时，当前 Session 重新评估当前有效 Semantic Contract，完成必要高价值判断后再继续。

独立 Primary Output Agent 的推荐形式：

```text
Stage 1: 检查当前 auth/session 架构并找出最窄兼容修复；在需要修改 public API 或 persistence schema 前暂停
Checkpoint: Findings: refresh state 同时存在于 middleware 与 storage；Issue: 有两种可行 ownership；Need: 实现前选择 middleware-owned 或 storage-owned
Amendment: 保持 public API 稳定；选择 storage-owned state；批准 Stage 2：实现并运行定向测试，只有当验证要求修改 Contract 时再次暂停
```

## 受监督的操作阶段

对于高不确定性的正常双 Session Coding 工作——例如首次构建、陌生环境 bootstrap、工具链诊断，或外部依赖/替代执行路径——输入侧 Agent 应预先划分一组短小、能够产出证据的阶段。每个阶段应以明确的观察结果或决策边界结束，而不是枚举命令。

每个预先声明的实现阶段结束时，独立 Primary Output Agent 必须返回压缩 Control Checkpoint 并暂停。输入侧 Agent 审查证据，选择 `Continue`、`Amend` 或 `Stop`，必要时修订 Semantic Contract 或下一 slice 指令，并且最多明确放行下一阶段。选定的 Change Verification Agent 与 Documentation/Comments & Git Operations Agent 也必须遵循各自获准的 slice 并返回相应 checkpoint。任何独立 Worker 都必须在变更系统或用户环境之前，以及发现权限或网络阻塞、偏离选定执行路径，或出现实质不同修复/替代方案时立即 checkpoint。

已批准实现或验证阶段内的低价值命令、日志和机械重试留在对应 Worker 的上下文中。本规则不要求逐命令汇报或固定频率的无信息心跳，也不强制所有 Coding 任务都拆成小阶段：已知、低风险且易于机械验证的实现操作仍可连续执行到实现 checkpoint。

## Coding Verification Boundary

### 验证资产与以回归为先的 fresh 验证

每个可重复的验证点，只要物化能够提供可复用的回归价值，就应在仓库中固化为自动化测试，或确定性的项目原生 Python、Shell 或其他脚本。一次性命令可以用于诊断问题，但对于预期会重复执行的检查，不得让它成为唯一的持久证据。

当仓库存在多个验证资产时，应维护可发现的阶段或组件聚合器，以及一个完整套件入口，或等价的 manifest。全新的 Change Verification Session 在入口可用时必须先运行累计的完整套件入口；随后只针对套件未覆盖的已变更风险或验收标准执行独立的定向分析，而不是从零重新发现仓库布局和标准命令。

verifier 保持只读。如果发现有价值但缺失的可重复检查，应报告覆盖缺口和准确的预期断言；不得自行添加检查。父 Agent 将修复返回 Primary Output，由其物化测试或确定性脚本。使用同一个 verifier 针对新的最终状态 epoch 重新验证并重新运行累计套件。不得为每个验证点或覆盖缺口创建新的 verifier。

验证资产必须确定性、幂等、非交互并具有有意义的退出状态；默认应离线运行、不调用实时 API、不读取秘密，尽量不修改产品和 Git 状态，并且不留下生成产物。适用时，网络、系统或端到端套件应明确区分并单独运行，使基线回归不依赖这些可选套件。

### 仅文档变更的轻量验证快路径

普通的 wording、路径、状态或引用文档变更默认使用轻量确定性检查：相关过时引用搜索、Markdown 或链接检查、空白/diff 检查以及受影响的现有契约脚本。不能仅因为文档文件发生变化就要求复杂的完整功能验证。当文档修改或定义公共契约、schema、配置格式、可执行命令、安全或权限规则、生成产物，或具有实质可执行行为时，才升级验证。

Primary Output 职责只负责实现反馈检查及其高体量证据处理，例如用于指导实现修复的聚焦构建、测试、lint、formatter、类型检查和局部诊断。这些检查是临时性的，不得表述为最终改动结果验证。

Change Verification 职责负责实质性改动的最终改动结果验证。其初始全新独立 Agent/Session 使用 Documentation/Comments & Git Operations 产出的变更范围清单和 Git 证据，检查最终项目状态、相关周边行为、完整变更范围与意外文件状态，并运行适当的整体证据检查，例如集成、回归、跨模块、系统或端到端测试。独立指独立判断且不继承 Primary Output 的实现历史；可以使用当前有界事实/路由 capsule，但此前 verifier 结论永远不能作为证据。它不执行非简单 Git 查询或操作。通常为一个 task conversation 创建一个独立 verifier，并在后续验证 slice 中复用。每个 slice 都带有最终状态 fingerprint（epoch），verifier 必须独立重新评估该状态的验收矩阵和全部适用检查。它返回压缩后的证据、失败、覆盖缺口和剩余风险；不得修改产品代码、测试、文档或配置，也不负责修复发现的问题。

针对性的 Evidence-on-Demand、澄清以及修复后的验证 slice 都复用该 verifier。最终状态 fingerprint 发生变化时，复用的 verifier 必须独立重新评估新的 epoch，不能把此前结论作为证据；相同状态上的非实质重跑也复用该 verifier，不会仅因某项检查待执行就创建另一个 verifier。只有确实存在多个隔离的验证需求时才创建额外 verifier，例如并发不兼容的环境/快照、不同的权限或安全域，或明确要求的独立审计。

Documentation/Comments & Git Operations 职责负责验证通过后、已批准的开发文档和代码注释物化，以及所有非简单的项目级 Git 操作。它可以运行文档专属检查（包括仓库双语验证器）和 Git 专属检查（例如有界 status/diff 校验），但不执行最终功能验证或语义验收，也不得修改功能或测试；只有明确获准且使用已批准内容的冲突解决编辑属于例外。

### 文档、注释与 Git 操作边界

文档/注释工作属于验证完成后的 Interaction Slice。非简单 Git 工作同样由该角色负责，但当需要同步、分支/worktree 准备、历史整合或冲突处理时，可以在更早阶段放行对应 slice。对于提交、推送、远端或 Issue/PR 交付，只有在最终工作树已验证并完成输入侧语义验收、任何文档 slice 已通过且无范围漂移、存在明确的用户/任务授权允许请求的仓库或 GitHub 副作用，并且 Host 能提供所需能力边界时，输入侧 Agent 才能放行 Git slice。验证失败、修复未解决、文档检查失败、缺少授权或能力不可用都会阻塞依赖该条件的 slice。

每个 Documentation/Comments & Git Operations slice 都必须写明目标、准确的文档/注释或仓库/worktree/ref/remote 范围、允许的变更与外部副作用、Return conditions 和 Unreleased boundary。Git slice 可以按授权检查或修改 Git 元数据，同步仓库，管理分支/worktree，暂存、提交、rebase/merge/cherry-pick，执行 reset/clean/stash，管理标签，处理明确获准的冲突，配置远端，推送并执行适用的 Issue/PR 交付；不得编辑已跟踪的功能、测试或其他内容，冲突解决例外仅限使用已批准内容。它不得做产品决策、执行语义验收，也不得从自身角色、Contract 或 Session Affinity 推断外部授权。具体操作和检查以适用的仓库开发流程为准；本模块不复制 provider 专属命令或私有流程细节。

常规交付 read-back（status、暂存范围、commit、branch、Issue 或 PR metadata）留在已经获准的交付 slice 内，默认不创建单独的 delivery verifier。只有当父 Agent 指出明确的外部风险或独立性收益，例如高影响远端操作，或交付边界无法由 delivery Worker 安全检查时，才创建独立 delivery verifier，并明确放行该额外 slice。

在已放行的 slice 内，操作的高层顺序为：确认最终 Git 证据、status/diff、暂存范围和批准范围；使用合适的开放 Issue，或创建带类别 label 且指派 `@me` 的 Issue，然后核验；创建或确认合规分支和中文提交；只有 Issue 及暂存/提交检查通过后才推送；创建带有 `Closes #N` 且指派 `@me` 的 PR；核验远端分支、Issue 状态/label/assignee、PR base/head/assignee 以及 Issue 关联。同步、分支/worktree 准备和历史整合可以作为更早的独立 Git slice。未被放行覆盖的外部副作用发生前，以及权限、网络、label、assignee、分支、暂存范围、冲突或 PR 拓扑检查失败时，Worker 必须在阻塞式 Control Checkpoint 暂停。没有经过核验的开放 Issue 时，不得推送或创建 PR。

输入侧职责负责语义验收：用户目标是否满足、Semantic Contract 是否落实、业务/兼容性约束是否被破坏、Change Verification、文档检查和 Git 操作证据报告的风险是否可接受。它还决定改动是否达到需要独立 verifier 的实质程度、是否需要验证后的文档/注释工作，以及当前阶段是否授权 Git slice。

### 最终改动结果的有序流程

对于实质性功能改动，默认顺序为：

1. Primary Output 实现已批准的 slice，并运行临时聚焦检查，然后在实现 checkpoint 暂停。
2. 输入侧 Reasoning 使用最终状态、其 fingerprint/epoch、Contract、验收标准、变更范围证据和临时检查摘要，创建一个全新的独立 Change Verification Agent/Session。verifier 独立运行整体检查，并在压缩验证 checkpoint 暂停。
3. 输入侧 Reasoning 将每项验收标准映射到 verifier 证据，并选择 `Continue`、`Amend` 或 `Stop`。验证失败时，只向 Primary Output 放行有界修复 slice，之后复用同一个 verifier，针对修复后的新最终状态 fingerprint/epoch 开启验证 slice。verifier 必须独立重新评估修复后的状态，不能把此前结论作为证据；只有确实隔离的验证需求才创建额外 verifier。实质性验证问题解决前不得启动文档/注释或依赖验证的远端 Git slice。
4. 验证通过后，输入侧 Reasoning 执行语义验收；如有需要，创建带有明确文档/注释范围的 Documentation/Comments & Git Operations Agent/Session。该 Agent 返回其变更范围和文档专属检查。如其他阶段需要 Git 同步、分支/worktree 准备或历史整合，父 Agent 为同一角色放行独立 Git 范围并设置自己的 checkpoint。
5. 最终工作树和文档 checkpoint 通过后，如果存在明确的用户/任务授权且 Host 具备所需能力，输入侧 Reasoning 可以向同一角色放行提交、推送、远端或 Issue/PR Git slice。Git slice 返回压缩后的本地与远端证据；不得做产品决策或执行语义验收。
6. 输入侧 Reasoning 执行最终语义验收，并确认文档/注释阶段没有引入功能或测试变更、冲突处理始终使用已批准内容，且请求的 Git/远端交付证据与已批准改动一致。

对于行为保持不变的简单任务或纯文档任务，输入侧 Reasoning 可以明确跳过 Change Verification Agent；但必须记录独立审查没有具体收益的原因，并运行适用的文档/静态检查。不改变已跟踪内容的纯 Git 操作可以使用记录的前后 Git 证据而不创建 verifier；冲突解决或任何已跟踪内容变化都需要独立验证，若已有该任务的 verifier 则应复用它。Primary Output 的自我汇报永远不能替代明确要求的 verifier。

在最终语义验收时，输入侧 Agent 必须在需要 verifier 时把每项验收标准映射到 Change Verification 的压缩证据（若明确跳过独立验证，则映射到已记录的聚焦/静态证据），并在适用时补充文档证据，然后给出明确判断：

```text
Acceptance criterion → evidence → input-side judgment
```

判断必须确认用户目标已满足、实现仍在批准的解决方案范围内、业务与兼容性约束保持不变、执行过程中没有偷偷引入未经批准的语义决策、需要时独立 verifier 确实检查了最终状态、批准的 Git 范围得到保持，并且验证留下的剩余风险可接受。这个基于证据的映射不要求重新读取完整 diff、完整测试日志或大型文件；只通过 Evidence-on-Demand 请求完成判断所需的最小额外证据。

正常双 Session 模式下，Primary Output 返回压缩的实现反馈结论，Change Verification 返回压缩的最终验证结论；输入侧不默认重新读取完整 diff、测试日志或大型文件。Single-Session Coding Mode 由当前 Session 完成实现和临时检查，然后对实质性改动创建一个全新的独立 verifier，并在后续验证 epoch 中复用它，而不是接受自己的最终验证。不得仅为了角色名称创建 verifier；只有 Contract、风险/实质程度或用户明确要求使独立审查具有具体收益时才创建初始 verifier；额外 verifier 仅用于确实隔离的验证需求。

## 输入侧输出纪律

在正常双 Session 模式下，输入侧 Agent 的输出以高信息密度为目标，只输出完成高级决策、Semantic Contract、决策升级、语义验收和必要用户交互所需的内容。

当任何独立 Worker 完成所分配的工作，并已在自己的 Session 中输出详细汇报后，输入侧 Agent 必须先分析该汇报，再压缩后回复用户。回复应仅包含必要的核心结果、变更范围、验证状态、未解决的问题或风险以及后续动作（如适用）。应引导用户前往相关 Worker 的上下文汇总查看原始详细汇报。输入侧 Agent 不得复制或大段重述任何 Worker 汇报；只有用户明确主动索取更多细节时才可扩展，且扩展内容必须严格限定在用户请求的范围内。除非用户提出此类请求，输入侧 Agent 在完成分析后始终保持精简输出。

凡文本主要是在展开已经确定的信息，而不是产生新的高价值决策，应交给获准承担该输出的 Worker，例如：

- 大段代码、完整文件或详细逐文件实现步骤；
- 长篇 README、设计文档、报告或说明应由 Documentation/Comments & Git Operations Agent 在获准此类工作后物化；
- 大量项目现状复述、完整 diff/测试报告；
- 可以由获准物化 Worker 直接物化的长最终答复。

Single-Session Coding Mode 不存在可供用户跳转的独立实现 Session 或上下文汇总。当前 Agent 已经承担 Primary Output Role，因此直接完成实现物化；任务或用户确有需要时，可以直接提供必要的详细汇报。如果选择 Documentation/Comments & Git Operations，则由该 Worker 负责文档/注释物化和非简单 Git 证据/输出。本节关于双 Session 的“压缩并引导查看”规则不要求当前 Agent 模拟独立的输出侧汇报，也不得仅为了委派长实现输出而创建另一个 same-runtime Session。

当正常双 Session 模式的最终答复本身很长且宿主不能直接复用输出侧结果时，优先让获准承担物化的 Worker 把完整内容写入用户指定文件或工作区，输入侧 Agent 只返回极简摘要和位置，不重新生成长文。

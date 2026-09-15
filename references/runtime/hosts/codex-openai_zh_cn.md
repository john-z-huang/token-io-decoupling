# Codex + OpenAI Coding 部署

本文件是 Codex + OpenAI 模型族的已登记 Coding 部署文档，覆盖这一产品/provider 组合的两个部署关注点：

- **宿主机制**：Codex 如何提供持久指令、独立 Agent/Session 创建与复用、显式运行参数选择、文件系统/沙箱 capability 和上下文传输。
- **模型策略**：哪些 OpenAI Runtime 可以承担各 Coding 角色、不同任务类型使用什么执行参数、升级策略，以及所需绑定不可用时如何处理。

本文件不负责 Coding 角色定义或 Session 语义。角色映射由 [`../../coding/runtime_zh_cn.md`](../../coding/runtime_zh_cn.md) 与 [`../../coding/session-model_zh_cn.md`](../../coding/session-model_zh_cn.md) 解析。

## Host 身份

只有当前运行中的 Code Agent 环境确实是 Codex 时才使用本部署。不得根据仓库内容、Skill 安装位置、提示词中出现 Codex，或仅仅存在 `AGENTS.md` 文件来推断 Host 身份。

当运行环境能够暴露当前模型或 Session 配置时，用这些事实进行 Runtime 解析。所需身份或 capability 信息无法获得时，应把该事实返回 Coding Runtime Contract，而不是猜测。

## 持久指令加载

需要让 Skill 核心不变量在每个新 run 中都生效的 Codex 部署，应使用 Codex 的持久指令机制。全局 `~/.codex/AGENTS.md` 可以保存短 bootstrap；同层级存在 `~/.codex/AGENTS.override.md` 时，以当前 active override 为准。仓库/项目指令继续负责项目专属政策，不得复制完整 Skill 形成第二份规范。

普通 Skill description 影响发现，但不能保证每个新 run 都已经加载完整 Skill。因此 bootstrap 应指向已安装的 `token-io-decoupling` Skill，再由 `SKILL.md` 路由需要的 reference，而不是把规范性 Flow 文本复制进持久指令文件。bootstrap 应保持与宿主无关；共享的 bootstrap 文本维护在 [`../../../BEST_PRACTICES_zh_cn.md`](../../../BEST_PRACTICES_zh_cn.md)。

## 角色绑定与 Session 选择

启动 Coding Flow 时，在运行环境能够提供时记录当前 Session 的模型身份。使用该身份解析 Host capability 与需要委派的角色绑定；不得仅凭模型身份选择 Single-Session Coding Mode：

- **Input-side Reasoning**：当前高级父模型/Session 负责高价值语义决策。
- **Primary Output**：当选择独立 Primary Output Session 时，本部署将其绑定到 OpenAI 执行模型 `gpt-5.6-luna`。该委派绑定本身不是进入 Single-Session Coding Mode 的条件。
- **Change Verification**：选择该角色时，为该 task conversation 启动一个全新的独立 `gpt-5.6-luna` Session 进行最终改动结果验证，然后复用该 verifier 执行后续验证 slice。每个新的最终状态 fingerprint/epoch 都必须独立重新评估；此前结论不能作为证据。只有确实存在独立隔离需求时才创建额外 verifier Session，例如不兼容的环境/快照、不同的权限或安全域，或明确要求的独立审计。
- **Documentation/Comments & Git Operations**：选择该角色时，使用独立的 `gpt-5.6-luna` Session 负责获准的验证后文档/代码注释物化，以及所有非简单仓库 Git 操作。它负责同步、分支/worktree 操作、暂存、提交、历史整合、reset/clean/stash、冲突处理、标签、远端、推送和适用的 Issue/PR 交付；只有极小的只读 Git 元数据查询可以留在该角色之外。
- **Context Bootstrap/Refresh**：选择该职责时，使用独立或可复用的 `gpt-5.6-luna` Worker；有界事实与 policy-routing capsule 物化默认使用 `reasoning_effort=high`。只有在宿主明确支持时，确定性的 metadata/source-hash 或增量 refresh 工作才可使用 `reasoning_effort=medium`；语义解释仍由 Input-side Reasoning 负责。
- **Single-Session 判断**：Input-side Reasoning Agent 根据每个任务的复杂度和难度、语义与运行风险、预期上下文负载、并行性、隔离要求以及当前上下文是否足够进行判断。如果独立 Primary Output Session 不会带来具体结构性收益，当前 Session 依据 active Runtime 可以承担两个职责，Host 能在该 Session 满足当前任务要求的运行参数，且不存在硬性的权限、安全或隔离要求，则使用 **Single-Session Coding Mode**。当前输入侧模型的名称、档位或 reasoning-effort 强度本身都不能单独触发或禁止该模式。
- **正常双 Session 映射**：当 Input-side Agent 识别出独立 Primary Output Session 的具体结构性收益，或 active Runtime/Host 施加了硬性的同 Session eligibility、权限、安全或运行参数约束时，当前 Agent 继续承担 Input-side Reasoning，并在部署要求委派时使用独立的 `gpt-5.6-luna` Session 承担 Primary Output。

Single-Session Coding Mode 保持本部署在实现方面的已有行为：当 Host 与 active Runtime 允许当前 Session 组合承担这些职责时，由当前 Session 直接完成源代码/项目探索、实现、调试、临时聚焦检查和实现输出，不为了维持双角色形式而委派普通工作。需要委派时，独立 Primary Output Session 仍绑定到 `gpt-5.6-luna`。Single-Session 不承担非简单 Git 操作，也不会取消验证与交付角色：对实质性功能改动，输入侧 Agent 仍会启动一个全新的独立 Change Verification Luna，并在同一个 task conversation 的后续验证 epoch 中复用它，需要文档或 Git 工作时还可创建独立的 Documentation/Comments & Git Operations Luna。当前任务 Profile 要求时，普通实质性实现使用 `reasoning_effort=xhigh`；无法满足要求的档位是运行时约束，不应反推成模型名称规则。

处于 Single-Session Coding Mode 的 Session 只有在 Input-side Agent 识别出具体结构性收益或硬性的 Runtime/隔离要求时才允许创建额外 Agent，包括本轮初始选定的独立验证、验证后的文档/注释或非简单 Git 操作隔离、真正并行、当前上下文明显失效/膨胀、存在明确独立隔离收益，或某个具体任务反复阻塞而需要定向 `max` 升级。后续验证 epoch 复用已选 verifier；额外 verifier Session 需要确实隔离的验证需求。项目探索、实现、测试、长输出、笼统的“任务复杂”或当前模型名称/档位本身都不是例外理由。

## 独立 Agent 与 Session 操作

本部署需要独立 Primary Output、verifier、辅助 Worker 或定向 escalation Session 时，使用当前 Codex 环境提供的独立 Agent/Session 机制：

- Codex 暴露模型和运行参数控制时，显式请求绑定的模型与宿主支持参数；
- 创建 Agent 时，在指令正文中以可读文本写明本次指定的具体模型名称/标识和 `reasoning_effort`，即使也通过宿主控制项设置了这些值；不得要求 Agent 从工具参数或自身运行时身份推断本次指定。复用已明确写过相同指定的 Agent 时，不要机械重复；指定发生变化或先前指令缺失、不明确时再写明；
- 本部署绑定精确模型或 reasoning-effort 档位时，不依赖未指定的宿主默认值；
- 相关工作优先复用已经建立的 Primary Execution Session，只有 Core 规则给出具体重建/拆分理由时才新建；
- 同一兼容 Session 只是切换逻辑职责时，不因为角色名称变化而创建第二个 Session。

当前 Codex 环境若无法创建所需独立 Session、无法选择所需模型，或不能满足所需运行参数，应把该 capability failure 交给下方 unavailable 规则处理，而不是自行换模型。

## Reasoning-effort 分级

- 正常双 Session Coding 中，独立 Primary Output Luna 默认使用 `reasoning_effort=xhigh`。一般需求开发、非平凡重构或调试、实现反馈测试代码，以及其他需要在**已批准语义方案内进行较多执行判断**的工作使用 `xhigh`。这一强度档位不会把问题定义、架构选择、未解决的语义权衡或验收 ownership 转移给 Primary Output；输出很长或项目规模很大本身不能作为继续提高强度的理由。
- 选择的 Change Verification Luna 默认使用 `reasoning_effort=xhigh`，因为它需要针对最终变更状态独立选择并解释整体检查。它只负责验证证据，不负责修复、架构决策或语义验收。
- 选择的 Documentation/Comments & Git Operations Luna 对文档/注释物化和非简单仓库 Git 工作均默认使用 `reasoning_effort=high`。其文档写入范围排除功能与测试；其 Git 范围限制为明确放行的仓库/worktree/ref/remote 操作。不得用来弥补验证失败或自行做未经批准的产品决策。
- 其他辅助物化 Worker 默认使用 `high`，除非具体任务明确符合 `xhigh` 条件。
- 只有宿主明确支持对应档位，并且任务严格有界、语义风险低且容易机械验证时，才使用 `reasoning_effort=medium` 或更低强度。适合的例子包括运行已经选定的 test/formatter/lint 并压缩结果、收集文件/路径元数据、精确搜索或提取、字面量替换、按明确模板格式整理或更新生成表格。低于 `medium` 的档位原则上只用于只读工作或确定性机械变换。不得把 Semantic Contract ownership、架构/产品判断、跨模块实现、复杂调试、复杂测试设计、公共 API/schema/权限变更交给这些轻量 Worker。

## 定向 max 升级

`reasoning_effort=max` 是异常升级手段，不是普通 Worker 默认配置。

只有某个具体事项已经由现有 `high`/`xhigh` Worker 反复失败、来回振荡或出现明确阻塞时，才使用 max。父 Agent 为该事项创建新的、范围严格收窄的 max Worker；条件允许时，原 Worker 先按照 [`../../coding/context-exchange_zh_cn.md`](../../coding/context-exchange_zh_cn.md) 定义的文件化 Context Exchange 机制，在 primary worktree 中写好可复用上下文与 handoff 文档，新 max Worker 读取这些内容后接手，而不是从零重新探索项目。

阻塞解除后，后续无关工作恢复正常 `xhigh`/`high` 档位，不让 max 继续成为默认值。

## Runtime 参数 ownership

Codex 可以为派发工作暴露模型选择和 `reasoning_effort` 控制。这些控制项是否存在由宿主决定；具体绑定哪个值由上方角色绑定与 effort 分级决定。不得把未指定的宿主默认值当作本部署的策略。

宿主 UI 或工具可能已经显示等价的派发信息；是否还需要额外用户可见预览由共享 `Dispatch Preview` 规则决定，本部署不创建第二套产品专属反馈协议。

## Unavailable handling

- 不得把本部署绑定到 Luna 的委派 Coding 角色静默替换为其他模型。
- 如果 Input-side Agent 已选择独立 Luna 角色，或 active Runtime 强制要求拆分，但无法确认 `gpt-5.6-luna` 身份、无法显式选择该模型，或 Host 无法满足当前 dispatch 所要求的 reasoning-effort 档位，则停止对应实质性 Coding 或验证工作并简短报告阻塞。不得因为 verifier 绑定不可用就让 Primary Output 自行验证实质性改动。
- 如果其他条件允许 Single-Session Coding Mode，且没有选择或强制要求独立 Luna 角色，那么无法确认当前输入侧模型是 `gpt-5.6-luna` 本身不构成阻塞；应改为依据 active Runtime 与 Host capability 要求评估当前 Session。
- 如果已选定的委派 Luna 角色能够确认其身份，但 Host 无法设置 reasoning effort，则可以继续纯只读、严格有界的诊断。任何绑定要求 `high` 或 `xhigh` 的委派任务都不得静默降级到更轻档位；如果没有选择独立角色，则应根据当前 Session 的实际 Runtime 与 Host capability 检查处理，而不是把这个例外当作模型选择规则。
- 不得仅因为高级父模型技术上也能实现代码，就推断它必须吸收 Primary Output，也不得仅因为它具备实现能力就推断必须委派。应遵循 Input-side 对结构性收益的判断以及 active Runtime/Host 的硬约束；上方 Luna 绑定只适用于选择独立委派角色的情况。

## 文件系统与 worktree 映射

多个 Agent 处理同一个开发需求时，默认复用该 task 的 primary Git worktree。独立 Agent/Session、全新的 verifier 或 Worker 专属 Context Exchange 目录本身都不要求额外 worktree。遵循 [`../../coding/context-exchange_zh_cn.md`](../../coding/context-exchange_zh_cn.md) 中的验证与明确隔离例外；并发写入发生冲突时，优先分配互不重叠的路径范围或按依赖顺序执行 slice。

多 Agent Coding 使用文件化 Context Exchange 时，应通过当前 Codex 环境能够提供的最强隔离机制实现其中的 capability 要求：

- 宿主支持路径级限制时，每个 Worker 的 RW 范围只覆盖明确列出的变更路径和自己的 context 子目录；verifier 对固定最终状态保持 RO，只有其获准 slice 明确授权的验证脚本/测试路径可以 RW；
- 只有确有隔离需求时才创建独立验证 worktree，例如不兼容的快照/环境、无法重定向或隔离的验证写入、不同的权限/安全边界要求提供单独限定的文件系统视图，或明确要求隔离的审计；
- 跨 Worker 上下文优先以定向 RO 路径暴露；
- 宿主支持时，其他 Worker context 与父级独占的根索引保持不暴露或 DENY；
- 无法安全提供 RO 共享时，先使用工具级机械复制，再考虑父 Agent 中转。

`git worktree` 只提供物理工作副本边界，不是权限机制；不得宣称比当前沙箱实际能力更强的隔离。

## Run 生命周期

Codex 会在 run 或 TUI Session 启动时构建适用的指令链。修改全局持久指令、active override、Skill 或仓库指令文件后，应使用新的 run/Session 验证生效情况，不假定既有 Session 已自动吸收变更。

共享的安装步骤与 smoke check 见 [`../../../BEST_PRACTICES_zh_cn.md`](../../../BEST_PRACTICES_zh_cn.md)。

# Multi-Agent 委派执行模块

[English](delegated-execution.md) | [简体中文](delegated-execution_zh_cn.md)

本 Layer-04 模块组合 Bootstrap 评估与 Root 任务授权、执行者/输出/角色决策、所有执行者共用的当前 Slice 门禁、有条件的子代理创建与派发、实施/结果处理、阶段反馈及 Control。它返回实施状态与初步证据；最终验证属于后续验证/修复工作流。

## 入口声明

| 字段 | 要求 |
| --- | --- |
| 必需输入 | 当前已授权 Contract/任务、已释放 Multi-Agent 模式和正数锁定数量、完整且当前的 Session/审计、有来源的 Context 和 Decision、当前 allocation/角色事实、continuation/效果状态、恢复底线/Control 证据；仅在恢复既有已释放 Worker bundle 时，还须提供该 bundle 记录的显式 `write_content_memo` 值。新 Worker bundle 的显式值在 DE04 确定。 |
| 允许效果 | 评估 Bootstrap 并授权实际任务；解析执行者/输出/角色；释放和持久化已授权 Slice；有条件地创建/复用子代理并只派发该任务；本地实施或接收子代理实际结果；提供阶段反馈并解决 Control。所有效果仍受直接 owners 和现有授权约束。 |
| 结果 | 仅在返回当前实施/结果状态、指纹、初步检查、Control 处置且无待处理恢复/下一 Slice 时返回 `complete`；否则以 continuation 返回 `needs_prerequisite` 或 `blocked`。条件子代理、角色、memo 及 state store 子步骤可根据观察到的原因标为 `not_applicable`。 |
| 新鲜度 | 将任务/Slice 指纹、Contract/Decision、规范 state 与 allocation revision、子代理身份、显式 memo 值、Control 规则及相关 epoch 绑定到其来源。实质变化会使受影响证据失效，并要求从受影响检查点重新进入。 |

## 工作流路线图

```mermaid
flowchart TD
    DE00["DE00 解析模块入口"]
    D_ENTRY{"入口结果？"}
    DE01["DE01 评估 Bootstrap；Root 授权实际任务"]
    DE02["DE02 分别解析执行者和输出"]
    D_EXEC{"执行者/输出结果？"}
    DE03["DE03 仅为新执行者预留角色"]
    D_ROLE{"角色预留结果？"}
    DE04["DE04 共用恢复门禁和当前 Slice"]
    D_GATE{"恢复门禁与 Slice 有效？"}
    DE05["DE05 新建合格子代理并绑定身份（如适用）"]
    D_CHILD{"执行者分支？"}
    DE06["DE06 子代理派发、Worker 边界和显式 memo 字段"]
    DE07["DE07 子代理执行期间的实际实施、所选受控输出、结果收集/审阅和初步检查"]
    D_OUTPUT{"是否为此执行者选择受控候选路径？"}
    DE_OUTPUT_PREP["执行期间准备并检查同一有界候选及 manifest"]
    DE_OUTPUT_PREFLIGHT["在同一固定 root 和政策下进行新鲜的 whole-batch 预检"]
    DE_OUTPUT_APPLY["重新核验授权、候选 artifact 和 baseline；应用准确候选"]
    DE_OUTPUT_REVIEW["保留已准备候选 ID/hash、应用收据和实际当前状态证据"]
    DE_RESULT_REVIEW["Root 将实际结果与适用时保留的候选 ID/hash、收据和当前状态一起审阅"]
    DE_OUTPUT_NA["not_applicable：未选择可选候选路径；已记录原因"]
    DE_NEEDS_OUTPUT["needs_prerequisite：解决输出守卫/预检/当前状态；恢复 DE07 子步骤"]
    D_RESULT{"实施/结果当前有效？"}
    DE08["DE08 当前 Control 决策"]
    D_RECOVERY{"恢复处置？"}
    D_CONTROL{"Control 结果和后续工作？"}
    DE09["DE09 返回已完成实施/结果状态和初步证据"]
    DE_NEEDS_ENTRY["needs_prerequisite：解析入口/任务 owner"]
    DE_NEEDS_ROLE["needs_prerequisite：解析执行者/输出/角色"]
    DE_NEEDS_SLICE["needs_prerequisite：保留 Slice continuation"]
    DE_NEEDS_PENDING["needs_prerequisite：等待子代理结果；保留适用的候选 ID/hash、收据、当前状态及 N/A 处置；仅恢复结果审阅，不重放"]
    DE_NEEDS_EOD["needs_prerequisite：补充证据；恢复同一 Control"]
    DE_NEEDS_AMEND["needs_prerequisite：更新 Contract/Decision；按需更新 Context；恢复同一 Control"]
    DE_NEEDS_NEXT["needs_prerequisite：解析下一 Slice 的 Context/Decision"]
    D_CONTINUE_COVERS{"先前 Continue 是否仍覆盖有界 Slice 且状态/epoch 当前？"}
    D_REROUTE{"任务/授权/执行者/输出/角色证据是否变化？"}
    DE_BLOCK["blocked"]
    DE00 --> D_ENTRY
    D_ENTRY -- 就绪 --> DE01
    D_ENTRY -- 证据缺失 --> DE_NEEDS_ENTRY
    D_ENTRY -- 冲突或状态不安全 --> DE_BLOCK
    DE01 -- 实际任务已明确授权 --> DE02
    DE01 -- 授权缺失/冲突 --> DE_BLOCK
    DE02 --> D_EXEC
    D_EXEC -- new-executor-needed 且输出已处置 --> DE03
    D_EXEC -- 已确认 Root/现有执行者且输出已处置；角色 N/A --> DE04
    D_EXEC -- 必需结果未解决 --> DE_NEEDS_ROLE
    D_EXEC -- 范围/模式冲突 --> DE_BLOCK
    DE03 --> D_ROLE
    D_ROLE -- 唯一角色和当前容量已确认 --> DE04
    D_ROLE -- 证据缺失 --> DE_NEEDS_ROLE
    D_ROLE -- 不一致或未授权 --> DE_BLOCK
    DE04 --> D_GATE
    D_GATE -- 当前已授权 Slice --> DE05
    D_GATE -- post-floor Continue 缺失/过期 --> DE08
    D_GATE -- Stop 或 Slice 未授权 --> DE_BLOCK
    DE05 --> D_CHILD
    D_CHILD -- 新建合格子代理；身份已确认 --> DE06
    D_CHILD -- 现有子代理；新建 N/A --> DE06
    D_CHILD -- Root 执行；子代理 N/A --> DE07
    D_CHILD -- 创建/身份前置缺失 --> DE_NEEDS_SLICE
    D_CHILD -- 创建未授权或无效 --> DE_BLOCK
    DE06 -- 派发已确认；子代理执行期间进入 --> DE07
    DE07 --> D_OUTPUT
    D_OUTPUT -- 已选择；执行者、class、capability、授权、root 和 baseline 当前有效 --> DE_OUTPUT_PREP
    D_OUTPUT -- 未选择可选候选路径；记录原因 --> DE_OUTPUT_NA
    D_OUTPUT -- 所选路径缺少当前必需能力/证据 --> DE_NEEDS_OUTPUT
    D_OUTPUT -- 效果未授权或不安全 --> DE_BLOCK
    DE_OUTPUT_PREP -- 执行期间已准备/检查候选；已审阅同一 manifest --> DE_OUTPUT_PREFLIGHT
    DE_OUTPUT_PREP -- 准备、检查或完整性未解决 --> DE_NEEDS_OUTPUT
    DE_OUTPUT_PREFLIGHT -- 在同一固定 root 和政策下新鲜 whole-batch 预检通过 --> DE_OUTPUT_APPLY
    DE_OUTPUT_PREFLIGHT -- 已选检查失败、未知、遗漏或过期 --> DE_NEEDS_OUTPUT
    DE_OUTPUT_APPLY -- 准确应用；候选 ID/hash、收据和实际当前状态已保留 --> DE_OUTPUT_REVIEW
    DE_OUTPUT_APPLY -- 部分完成、冲突、不确定或状态已改变 --> DE_NEEDS_OUTPUT
    DE_OUTPUT_REVIEW --> D_RESULT
    DE_OUTPUT_NA --> D_RESULT
    D_RESULT -- 实际结果可供审阅 --> DE_RESULT_REVIEW
    D_RESULT -- 子代理结果待处理 --> DE_NEEDS_PENDING
    D_RESULT -- 必需实施证据缺失 --> DE_NEEDS_SLICE
    D_RESULT -- 冲突或效果不安全 --> DE_BLOCK
    DE_RESULT_REVIEW -- 实际结果和保留证据已审阅；当前状态有效 --> DE08
    DE_RESULT_REVIEW -- 结果仍待处理 --> DE_NEEDS_PENDING
    DE_RESULT_REVIEW -- 结果/状态冲突或不安全 --> DE_BLOCK
    DE08 --> D_RECOVERY
    D_RECOVERY -- recovery Continue --> DE04
    D_RECOVERY -- Evidence-on-Demand --> DE_NEEDS_EOD
    D_RECOVERY -- Amend --> DE_NEEDS_AMEND
    D_RECOVERY -- Stop --> DE_BLOCK
    D_RECOVERY -- normal Continue --> D_CONTROL
    D_CONTROL -- 存在下一 Slice --> DE_NEEDS_NEXT
    DE_NEEDS_NEXT -- Context/Decision 已当前 --> D_CONTINUE_COVERS
    D_CONTINUE_COVERS -- Continue仍覆盖Slice且边界/epoch当前 --> D_REROUTE
    D_CONTINUE_COVERS -- 范围、边界、状态或epoch使Continue失效 --> DE08
    DE_NEEDS_EOD -- 必需证据已当前 --> DE08
    DE_NEEDS_AMEND -- Contract/Decision及所需Context已当前 --> DE08
    DE_NEEDS_PENDING -- 收到实际结果；复用保留证据，不重新准备或再次应用 --> DE_RESULT_REVIEW
    D_REROUTE -- 实际任务或授权变化 --> DE01
    D_REROUTE -- 执行者或输出证据变化 --> DE02
    D_REROUTE -- 新执行者的角色证据变化 --> DE03
    D_REROUTE -- 相关路由证据仍当前 --> DE04
    D_CONTROL -- 当前 post-implementation/result 证据；无下一 Slice 或待处理恢复 --> DE09
    DE04 -- 必需计划访问或更新失败 --> DE_BLOCK

```

## 有序模块清单

1. **DE00 — 解析入口。** 提供本声明、当前授权及已释放路线/模式/count 证据、完整 Session/审计与 Context/Decision 证据、allocation、先前效果、恢复状态及 continuation，调用[模块入口解析](../../layer-03-workflow-checkpoints/module-entry-resolution_zh_cn.md)。恢复既有已释放 Worker bundle 时，提供其记录的显式 memo 值；新 bundle 的值在 DE04 确定。`ready` 只允许模块核验。证据缺失时连同 owner/位置返回 `needs_prerequisite`；冲突、状态不安全或效果无法恢复时返回 `blocked`。
2. **DE01 — 评估 Bootstrap 并授权实际任务。** 根据当前任务、角色、名额和 Memory 事实应用[Bootstrap 选择](../../layer-03-workflow-checkpoints/bootstrap-selection_zh_cn.md)。建议不预留角色，也不释放 Slice。Root 重核当前 Context 和 Decision，然后明确授权实际任务：适用时采用有界 Bootstrap/Refresh 任务，否则采用原任务。独立辅助 Bootstrap 任务需要 Root 另行授权，并将原任务保留为 continuation；辅助任务完成后返回 DE01，单独授权并评估原任务，不得依据辅助结果将原任务标为完成。实际任务缺少授权时阻塞。
3. **DE02 — 分别解析执行者和输出。** 应用[任务分配](../../layer-01-fundamental-concepts/execution-planning/task-assignment_zh_cn.md)和[执行者选择](../../layer-03-workflow-checkpoints/executor-selection_zh_cn.md)，再应用[输出 Token 路由](../../layer-01-fundamental-concepts/execution-planning/output-token-routing_zh_cn.md)及[输出路由选择](../../layer-03-workflow-checkpoints/output-route-selection_zh_cn.md)。仅当执行者结果为 `new-executor-needed` 且 Root 输出已处置时进入 DE03。已确认 Root 执行者或已确认的现有执行者/子代理，必须先确认输出已处置，再根据该证据将角色预留记录为 `not_applicable` 并继续至 DE04。必需结果未知或未解决时返回 `needs_prerequisite`；冲突则阻塞。不得把未解决视为 `not_applicable`。
4. **DE03 — 仅为新执行者预留角色。** 仅在 DE02 的 `new-executor-needed` 且输出已处置分支，应用[角色预留](../../layer-03-workflow-checkpoints/role-reservation_zh_cn.md)、[子代理角色选择](../../layer-01-fundamental-concepts/delegation/child-role-selection_zh_cn.md)、[子代理职责分配](../../layer-01-fundamental-concepts/delegation/delegation-child-role-allocation_zh_cn.md)、[委派数量门禁](../../layer-01-fundamental-concepts/delegation/delegation-mode-count-gate_zh_cn.md)和[委派状态记录](../../layer-01-fundamental-concepts/delegation/delegation-state-record_zh_cn.md)。确认唯一且当前有效的预留，以及容量/allocation 证据。必需证据缺失时返回 `needs_prerequisite`；不一致或未授权时阻塞。不得为 Root 或现有执行者再次预留。
5. **DE04 — 应用所有执行者共用的恢复门禁并释放当前 Slice。** 所有实际执行者分支都经过此检查点。应用[执行控制](../../layer-01-fundamental-concepts/execution-control/execution-control_zh_cn.md)、[执行规划](../../layer-01-fundamental-concepts/execution-planning/execution-planning_zh_cn.md)及[Native 对账](../../layer-01-fundamental-concepts/enhanced-native-state/native-reconciliation_zh_cn.md)。存在恢复底线时，须有 post-floor `Continue` 且其 Control 规则和相关 epoch 为当前；证据缺失/过期时，释放/恢复前返回 DE08。`Stop` 阻塞。适用子代理执行时，核验当前容量/allocation；Root 执行时记录带原因的子代理容量 `not_applicable`。仅当 Context 和 Decision 当前有效，并明确目标、已授权执行者/角色、范围/修改、返回条件、未释放边界，以及每个新释放 Worker bundle 的显式 `write_content_memo: true` 或 `false` 时，才释放具体 Slice。恢复既有 bundle 时，保留并核验其记录值，不得臆造或替换。Enhanced state 条件适用时，应用[Enhanced State Store](../../layer-01-fundamental-concepts/enhanced-native-state/enhanced-state-store_zh_cn.md)及[Enhanced Schema Migrations](../../layer-01-fundamental-concepts/enhanced-native-state/enhanced-schema-migrations_zh_cn.md)，通过已授权的 typed Root 操作及所需的预期 revision/idempotency 持久化，然后在子代理行动前读回。Native 模式按其 owner 更新规范 parent-context record 并确认当前状态。无恢复底线时，记录带原因的门禁 `not_applicable`。只有合格的代码/配置实施，或编写/编辑本 Skill 指令/参考文档，才可使用子代理；普通非 Skill 文档仍由 parent 编写。 释放前应用[任务计划 Memory 生命周期](../../layer-01-fundamental-concepts/execution-planning/task-plan-memory-lifecycle_zh_cn.md)：确认当前共享计划与读回，或其已记录的限制例外；必需访问/更新缺失时阻塞依赖释放。执行及需求修订期间保持先更新再汇报/依赖动作的顺序。
6. **DE05 — 创建新合格子代理并绑定身份。** 仅对新子代理应用[子代理创建](../../layer-01-fundamental-concepts/delegation/delegation-child-creation_zh_cn.md)和[运行环境与模型厂商支持](../../layer-01-fundamental-concepts/session-runtime/runtime-provider-support_zh_cn.md)。确认符合条件的已释放任务/Slice、唯一角色预留、当前容量、能力、权限、上下文、返回条件及必需运行环境/effort 证据；只创建已授权子代理。任何绑定身份的 Enhanced store 访问或派发前，记录并读回其真实身份/allocation。仅当选中并触发时，应用[Enhanced State Store](../../layer-01-fundamental-concepts/enhanced-native-state/enhanced-state-store_zh_cn.md)及[Enhanced Schema Migrations](../../layer-01-fundamental-concepts/enhanced-native-state/enhanced-schema-migrations_zh_cn.md)，确认守卫/schema/读回。复用现有子代理时，根据复用证据将创建和新 model-binding 检查记录为 `not_applicable`；保留相同身份，不重查模型选择，也绝不替换。已确认 Root 执行时，将子代理创建/身份记录为有原因的 `not_applicable`。所有分支进入 DE07；子代理分支先经过 DE06。
7. **DE06 — 仅在子代理分支派发。** 应用[子代理派发](../../layer-01-fundamental-concepts/delegation/delegation-child-dispatch_zh_cn.md)、[Worker 边界](../../layer-01-fundamental-concepts/delegation/delegation-worker-boundary_zh_cn.md)、[子代理生命周期](../../layer-01-fundamental-concepts/delegation/delegation-child-lifecycle_zh_cn.md)、[子代理复用与替代](../../layer-01-fundamental-concepts/delegation/delegation-child-reuse-replacement_zh_cn.md)、[子代理消息可见性](../../layer-01-fundamental-concepts/delegation/delegation-child-message-visibility_zh_cn.md)、[Content Memo Dispatch](../../layer-01-fundamental-concepts/context-exchange/content-memo-dispatch_zh_cn.md)及[Content Memo Lifecycle](../../layer-01-fundamental-concepts/context-exchange/content-memo-lifecycle_zh_cn.md)。实际已释放 bundle 必须包含完整任务与范围、来源指针、返回条件、适用时准确的授权 Memory 名称，以及显式 `write_content_memo: true` 或 `false`；不得推断默认值。只向已绑定的子代理派发已释放 Slice。为 true 时遵循 memo owner 生命周期并核验 memo 证据；为 false 时不得派发或写入该 memo。每次 follow-up 均保留实际派发正文证据和当前授权范围。派发或身份证据缺失/不完整时阻塞。确认派发及显式 memo 值后，立即进入 DE07，让子代理继续执行；不得等子代理结果返回后才开始 DE07。Root 执行时，将子代理派发/memo 记录为有原因的 `not_applicable` 并进入 DE07。派发同时按[任务计划 Memory 生命周期](../../layer-01-fundamental-concepts/execution-planning/task-plan-memory-lifecycle_zh_cn.md)携带准确共享任务计划项目/名称、允许贡献和协调的写入轮次。分配前确认子级读取/更新访问，新事实/进度返回前要求更新/读回；`write_content_memo: false` 不豁免该计划依赖。
8. **DE07 — 执行实际任务并返回结果。** 应用[实施](../../layer-02-workflow-concepts/decision-and-execution/implementation_zh_cn.md)。Root 执行时，作最小授权改动。子代理执行时，确认派发后立即进入 DE07，在子代理执行期间仅实施已释放任务；保留其实际正文/结果证据，结果待处理时不得声称完成，也不得依赖不完整消息。实际执行期间，仅当当前执行者、Slice、输出 class、capability、独立授权、固定 root、准确路径/操作和 baseline 符合[输出物料化](../../layer-01-fundamental-concepts/execution-planning/output-materialization_zh_cn.md)时，才按该 owner 处理候选输出。准备有界候选，保留其 manifest 身份/hash，并检查/审阅同一候选。应用前按[候选合规预检](../../layer-01-fundamental-concepts/execution-planning/candidate-compliance_zh_cn.md)在同一固定 root 和政策下进行新鲜 whole-batch 预检；然后重新核验授权、候选 artifact 完整性和 baseline，再应用准确候选。应用完成后，保留已准备候选 ID/hash、准确应用收据和实际当前状态证据。子代理结果待处理时，返回 `needs_prerequisite`，等待实际结果并从 DE07 的结果收集/审阅子步骤恢复，同时携带上述候选身份/hash、收据和当前状态证据。收集结果期间不得重启或重复准备、预检或应用。收到结果后，Root 将完整的子代理实际正文/结果与保留证据和当前文件一起审阅。子代理结果本身不授权应用。未选择可选路径时，记录有原因的 `not_applicable`，且仅在独立授权的直接路径下继续。已选路径缺少必需能力/守卫/预检，或返回失败、未知、遗漏、过期、不确定时，在依赖操作前返回 `needs_prerequisite` 或 `blocked`；不得静默回退。部分、冲突或不确定的应用必须先根据实际当前状态解决；不得覆盖已改变的内容进行重放。结果/状态冲突或不安全时阻塞。仅在需要代码结构证据且能力可用时应用[LSP MCP Tools](../../layer-01-fundamental-concepts/session-runtime/LSP-MCP-Tools_zh_cn.md)。所需 LSP 语义不可用时，说明限制并回退到定向文本搜索和路径范围较小的读取；不得将这些发现称为 LSP 证据。只有不需要代码结构证据时才能记录 `not_applicable`。必需关系仍未知时阻塞。触发时应用[执行阶段反馈](../../layer-01-fundamental-concepts/execution-control/execution-stage-feedback_zh_cn.md)；否则记录有原因的 `not_applicable`。实际结果和当前状态当前有效并已审阅后，运行聚焦的初步检查并返回路径、效果、实际正文/结果证据、适用时的收据/当前状态证据、检查输出和未解决问题。预检、应用收据和初步检查都不是最终 Verification。Root、复用子代理及新建子代理路径都必须经过此步。
9. **DE08 — 对所有执行者解决当前 Control。** 应用[Control](../../layer-02-workflow-concepts/decision-and-execution/control_zh_cn.md)、[执行控制](../../layer-01-fundamental-concepts/execution-control/execution-control_zh_cn.md)、[建议选择](../../layer-03-workflow-checkpoints/advisory-selection_zh_cn.md)和[Decisions Advisory](../../layer-01-fundamental-concepts/execution-planning/decisions-advisory_zh_cn.md)。消费当前 Progress Signal 的 status、findings、change scope、verification、issue、need 和当前未释放边界证据。只消费当前可信、符合条件、已启用且已授权的建议；否则记录建议 `not_applicable` 和原因，并基于直接证据决策。保留各 continuation：
   - post-floor `Continue` 缺失/过期时，进入或恢复此 Control 检查。recovery `Continue` 返回 DE04；不得为复用的子代理重新选择或创建替代者。
   - `Evidence-on-Demand` 暂停释放并返回 `needs_prerequisite`；保留同一 Control continuation，证据到达后在此恢复。
   - `Amend` 返回 `needs_prerequisite`；按 owners 更新 Contract 和 Decision，并在需要时更新 Context，然后恢复同一 Control 检查并取得新的明确 `Continue`，再返回 DE04。先前结果不释放工作。
   - `Stop` 返回 `blocked`。
   - 普通 `Continue` 后若有下一 Slice，则返回 `needs_prerequisite`，解析当前 Context/Decision，并确认先前 `Continue` 仍覆盖新的有界 Slice 且状态/epoch 当前。若范围、Contract、授权、未释放边界或相关 epoch 变化使其失效，则恢复此 Control 检查并取得新的明确 `Continue`。若实际任务或授权变化，在 DE01 仅重核受影响决策；若执行者/输出证据变化，在 DE02 重核这些决策，且仅当仍需要新执行者时才在 DE03重核角色预留；若仅新执行者的角色证据变化，则在 DE03 重核。检查完成后从 DE04 恢复，不重放已完成效果。否则在 Context/Decision 当前后直接从 DE04 恢复，适用时复用现有子代理。若没有下一 Slice 且没有待处理恢复结果，只有当前 post-implementation/result 证据确认任务已完成后才进入 DE09。
10. **DE09 — 返回实施/结果状态。** 返回证据证明当前任务实施/结果已完成、实际任务授权、执行者/输出/角色处置、已释放 Slice 与当前指纹、Root 实施或完整的子代理实际派发/结果证据、memo 字段/值及证据或有依据的 `not_applicable`、初步检查、当前 Control 结果/continuation 和限制。不得执行或声称最终验证；调用方后续验证/修复工作流负责最终验证。Root、现有子代理及新建子代理执行路径在返回前都必须经过 DE04、DE07 和 DE08。

## 相关概念

- [Bootstrap 选择](../../layer-03-workflow-checkpoints/bootstrap-selection_zh_cn.md)
- [子代理派发](../../layer-01-fundamental-concepts/delegation/delegation-child-dispatch_zh_cn.md)
- [执行控制](../../layer-01-fundamental-concepts/execution-control/execution-control_zh_cn.md)

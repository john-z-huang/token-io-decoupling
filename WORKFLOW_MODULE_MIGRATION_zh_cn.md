# 工作流模块迁移覆盖

[English](WORKFLOW_MODULE_MIGRATION.md) | [简体中文](WORKFLOW_MODULE_MIGRATION_zh_cn.md)

本开发记录说明如何从基线 `675627dc` 中重复、完整的 Layer-04 路线清单迁移到可复用模块契约和七步路线组合。Coding 运行时不加载此文件；它不授予权限。路线仍负责模块顺序和 continuation；各模块仍负责其低层检查。

机器可读的旧步骤、语义子步骤、owner 调用链和新检查点映射维护在 [workflow-module-migration.json](docs/workflow-module-migration.json)。校验器将其与实际模块清单检查点及链接核对；此开发用 manifest 不是运行时路线或授权来源。

## 路线组合

| 路线检查点 | 模块 | 路线负责事项 |
| --- | --- | --- |
| SM01 / MM01 | [入口就绪](docs/skill/references/coding/layer-04-workflows/modules/entry-readiness_zh_cn.md) | 确认已释放的 Contract、Environment/能力和模式证据。 |
| SM02 / MM02 | [Session 就绪](docs/skill/references/coding/layer-04-workflows/modules/session-readiness_zh_cn.md) | 完成规范状态/读回，再确认审计；Multi-Agent 还确认容量。 |
| SM03 / MM03 | [工作定义](docs/skill/references/coding/layer-04-workflows/modules/work-definition_zh_cn.md) | 当前上下文、决策和规划；Multi-Agent Bootstrap、角色/执行者决策归其执行模块。 |
| SM04 | [Single-Agent 执行](docs/skill/references/coding/layer-04-workflows/modules/single-execution_zh_cn.md) | Single-Agent 执行者、有界 Slice、实施、反馈和 Control。 |
| MM04 | [委派执行](docs/skill/references/coding/layer-04-workflows/modules/delegated-execution_zh_cn.md) | Multi-Agent Bootstrap/任务授权、执行者/输出/角色、共用 Slice 门禁、条件式子代理生命周期、实施/结果和 Control。 |
| SM05 / MM05 | [验证与修复](docs/skill/references/coding/layer-04-workflows/modules/verification-repair_zh_cn.md) | 当前状态验证、修复及变更 epoch 循环。 |
| SM06 / MM06 | [文档](docs/skill/references/coding/layer-04-workflows/modules/documentation_zh_cn.md) | 适用文档/Memory 输出、读回、影响、检查，以及必要时返回验证。 |
| SM07 / MM07 | [交付与验收](docs/skill/references/coding/layer-04-workflows/modules/delivery-acceptance_zh_cn.md) | 已授权 Git 效果、标准映射，以及通过验收后条件式归档计划。 |

当模块声明的工作与效果已包含在现有用户授权范围内且其入口声明前置条件满足时，可独立进入；无需按模块名称另行授权。完整路线仍要求全部路线前置和验收。暂停模块会返回准确 owner 和 continuation 位置；路线从该位置恢复，不重放已完成效果。状态、效果或 epoch 变化只返回受影响检查点。模块不得调用同级模块。

## Single-Agent 旧路线覆盖

下表 `S` 标签指基线路线的编号步骤，不是新路线 ID `S01`…`S07`。每行保留旧语义子步骤，并指向当前模块检查点。“直接”表示模块清单直接调用 owner；“传递”表示被调用的 Layer-03 owner 组合该低层 owner。模块链接是当前维护位置。

| 基线步骤/子步骤及 owner | 新检查点及消费位置 |
| --- | --- |
| S01 Contract、共享协议、意图/输出预分类 | SM01 → ER01；入口为 ER00。Contract 门禁是路线前证据；Semantic Contract 和返回协议仍由调用方负责。 |
| S02 Environment、能力清单、Enhanced 路径/可用性/主机绑定 | SM01 → ER02，经 Enhanced Path Selection 直接消费。 |
| S03 Mode 确认/数量/记录/重入 | SM01 → ER03，直接读取已释放路线证据。 |
| S04 Session state、authority、Context Firewall、audit、visibility、角色边界、migrations/reconciliation/transfer | SM02 → SR01–SR04。SR02 直接调用 Session State Resolution；其 owner 链传递消费身份、authority、schema、对账、转移和读回。SR03 直接调用审计解决、审计可见性、推理摘要可见性及状态记录 owner。SR04 条件式确认容量。 |
| S05 Context 来源选择、计划/Memory/规则查询、reconnaissance、context generation | SM03 → WD01，直接调用 Context Source Selection 和条件式 Decision Context Selection。 |
| S06 Decision、Decision Brief、execution planning、task assignment、output route、planning Memory、可选 advice | SM03 → WD02–WD03 负责 Decision 和规划输出。执行时的 executor/output 处置另在 SM04 → SE01 核验。规划生命周期直接消费；通过 WD 调用 L3 owner 的内容传递消费。 |
| S07 实施和代码结构证据 | SM04 → SE02–SE03；直接消费实施 owner，代码结构证据按需直接消费。 |
| S08 阶段反馈 | SM04 → SE04，直接消费并明确记录触发/N/A。 |
| S09 Control 和 Control advice | SM04 → SE05，直接消费 Control/Execution Control/Advisory Selection 和 Decisions Advisory；下一 Slice continuation 在同一模块检查点内返回。 |
| S10 最终指纹、验证、独立性/报告/epoch/advice | SM05 → VR01–VR04；当前 Verification 通过后经 VR06 返回结果。Verification、Reporting、Independence 和 Epoch 直接消费；advice 条件适用。 |
| S11 修复处置、scope gate、repair、execution、handoff、重新验证 | SM05 → VR05；直接消费处置，再按序直接消费修复 owners；handoff 返回 VR01，当前 Verification 通过后由 VR06 返回结果。 |
| S12 文档、影响、Memory、检查和变更 epoch 证据 | SM06 → DOC01–DOC06；直接消费文档、Memory/读回、影响分类和检查。内容影响返回 SM05。 |
| S13 Git 目标/效果/授权和指纹匹配 | SM07 → DA02，直接消费 Git owner；偏差时在后续 Git 效果前返回 SM05。 |
| S14 验收标准映射、剩余风险及 plan archive/readback | SM07 → DA03–DA05；直接消费 Acceptance/Epoch；仅所有适用标准通过后才归档匹配计划。与 Multi-Agent 基线 M07 的 Decision/Bootstrap 工作不同。 |

## Multi-Agent 旧路线覆盖

此处 `M` 标签指基线清单步骤。详细条件分支仍归当前 owners；下表标明旧操作现在由何处消费。

| 基线步骤/子步骤及 owner | 新检查点及消费位置 |
| --- | --- |
| M01 Contract、共享协议、dispatch 边界 | MM01 → ER01，并作为路线前 Contract 证据。Dispatch 规则稍后由 MM04 消费。 |
| M02 Environment、能力清单、Enhanced selection/host | MM01 → ER02；Enhanced owners 由 Enhanced Path Selection 按条件直接消费。 |
| M03 Mode/count/state/re-entry 和预留槽位状态 | MM01 → ER03；仅释放路线/数量，不授权创建子代理。 |
| M04 Session identity/authority、Context Firewall、审计、可见性、Native/Enhanced 转移与读回 | MM02 → SR01–SR03；SR02 的 Session State Resolution owner 链传递消费；SR03 在状态读回后消费审计和安全摘要 owners。 |
| M05 capacity/allocation 只读确认 | MM02 → SR04；直接核验容量门禁和 allocation，不预留角色。 |
| M06 有界 Context、来源、transport、可复用 Memory、handoff/exchange | MM03 → WD01；直接/条件消费 Context 来源和决策上下文 owners。Worker exchange 专用 owners 仅在后续模块实际操作触发时条件消费。 |
| M07 Decision 和两级 plan；规划 Memory；Bootstrap 提议；实际任务授权；advice；executor/output/role 决策 | MM03 → WD02–WD03 负责 Decision/规划/advice 和未释放边界。Bootstrap、实际任务授权、执行者/输出/角色及 Slice 释放归 MM04 → DE01–DE04。此 Decision/Bootstrap 检查点与基线 M16 的 Acceptance/plan archive 不同。 |
| M08 Slice/stage release、恢复 Continue、Control 规则/epoch、Native/Enhanced persistence | MM04 → DE04，直接消费 Execution Control/Planning/Native Reconciliation；typed persistence/readback 由状态 owners 条件式/传递消费。 |
| M09 条件式 child creation、runtime/effort binding、identity/allocation、reuse | MM04 → DE05，直接消费 Child Creation 和 Runtime/Model owner；store/schema 操作条件适用。 |
| M10 dispatch、Worker boundary、message visibility、memo 字段及生命周期 | MM04 → DE06；直接消费 dispatch/lifecycle/memo owners。恢复 bundle 时保留旧值；新 bundle 在 DE04 设置新值并在此沿用。 |
| M11 implementation、LSP 证据、stage feedback、Control、follow-up/reuse | MM04 → DE07–DE08；直接消费 implementation/feedback；DE08 直接消费 Control/Advisory。子代理 pending 时恢复 DE07；下一 Slice 经 DE08 和 DE04 返回，不重放效果。 |
| M12 最终验证、独立性、报告、epochs、advice 和 child-body visibility | MM05 → VR01–VR04；当前 Verification 通过后经 VR06 返回结果。直接消费验证 owners，verifier 交互时条件消费 message visibility。 |
| M13 repair diagnosis/disposition、scope、execution、handoff 和变更 epoch 验证 | MM05 → VR05 后返回 VR01；直接按序消费修复 owners，当前 Verification 通过后由 VR06 返回结果。 |
| M14 parent-owned 文档、文档影响、项目 Memory、检查和 epoch 复用 | MM06 → DOC01–DOC06；普通非 Skill 文档不交 child。内容影响返回 MM05。 |
| M15 Git target/effects/authorization、指纹、使用 Git Worker 时的 message visibility | MM07 → DA02，直接消费 Git owner；只有使用该角色时才条件消费 Worker message visibility。 |
| M16 Acceptance 标准/epochs、剩余风险、匹配 active plan archive/readback | MM07 → DA03–DA05；只有每项适用标准有当前通过证据后才归档计划。与基线 M07 的 Decision/Bootstrap 工作不同，现由 MM03 消费。 |

## 跨模块返回和 epoch 覆盖

| 事件 | 路线 continuation |
| --- | --- |
| 缺少前置 | 保留模块返回的 owner 和准确暂停检查点；解决后从该检查点恢复。不得重放前序模块效果。 |
| Session 恢复/状态实质变化 | SM02/MM02 必须先完成当前规范状态读回，再复用审计/容量证据；然后按路线记录的位置继续。 |
| Control Amend 或下一 Slice | 返回同一执行模块 Control 检查点；更新所需 Contract/Decision/Context；恢复实施前确认先前 Continue 仍覆盖有界 Slice 且状态/epoch 当前。 |
| Verification 修复 | 经修复 handoff 返回当前指纹捕获和必需检查；仅重跑被变化 epoch 影响的维度。 |
| 文档内容/Contract/验收影响 | 从 SM06/MM06 返回 SM05/MM05 做受影响的当前 Verification；当前证据通过前不得交付。 |
| Git/内容指纹偏差 | 从 SM07/MM07 返回受影响 Verification 维度，再进行任何 Git 效果或验收。 |
| Acceptance plan archive | 所有必需标准通过后，才归档/读回匹配且已完成计划；失败、缺失、不可用或未知的必需证据不得进入归档。 |

本覆盖表是迁移辅助资料，不是新增运行时策略来源。上方链接的路线和模块是当前可执行文档。

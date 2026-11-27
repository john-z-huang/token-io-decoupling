# 多代理 Coding

用户明确要求委派或任务存在适合独立委派的分工时，由主代理保留整体计划、决策、协调和最终验收，按各项工作的实际需求动态派给现有角色。

## 工作流路线图

从「开始」按当前事件进入相应分支。实线表示默认推进或收束，虚线表示条件分支。「结束」汇集本次流程的完成、受阻和转交结果。每个 Hook 的细则见同页子流程图。按[流程控制](coding-multi-agent.md#变更与流程控制)判断受影响工作的落点。

```mermaid
flowchart TD
    START(["开始"])
    MM01["MM01 需求确认 · 入口 Hook"]
    MM02["MM02 任务规划 · 规划 Hook"]
    MM03["MM03 任务执行 · 按就绪工作与责任选执行者"]
    MM04["MM04 结果验证 · 验证 Hook"]
    MM05["MM05 交付 · 交付 Hook"]
    DONE["完成"]
    EXECUTION["主代理执行 Hook · 推进主代理承担的工作"]
    DELEGATION["委派 Hook · 派发、续接、替换和回收证据"]
    INTERRUPTION["任意阶段中断、调用失败、实例异常或效果不明"]
    RECOVERY["恢复 Hook · 核实效果、处理在途任务和未决事项"]
    RESUME["按进入条件重返 MM01 至 MM05 中已就绪的落点"]
    SINGLE["处理受影响的在途工作后进入单代理路线"]
    BLOCKED["报告阻断和恢复条件"]
    END(["结束"])
    START -->|正常进入路线| MM01
    START -. 遇到中途事件 .-> INTERRUPTION
    MM01 -->|边界明确且沿用多代理路线| MM02
    MM02 -->|工作和分工就绪| MM03
    MM03 -->|主代理核实所需产物和证据| MM04
    MM04 -->|必要验收通过| MM05
    MM05 -->|实际交付物通过适用验收| DONE
    MM01 -. 新约束影响在途委派 .-> RECOVERY
    MM01 -. 新路线为单代理且受影响在途工作已处理 .-> SINGLE
    MM02 -. 无需实施或已有有效产物与证据 .-> MM04
    MM02 -. 目标、授权或验收有变 .-> MM01
    MM03 -. 有获准派发或续接的任务 .-> DELEGATION
    MM03 -. 分配给主代理的工作 .-> EXECUTION
    EXECUTION -. 本项产物和操作证据可验证 .-> MM04
    DELEGATION -. 本项产物和证据交由主代理验收 .-> MM04
    MM03 -. 前置、分工或能力变化 .-> MM02
    MM03 -. 用户约束变化 .-> MM01
    MM04 -. 需要且允许委派独立验证 .-> DELEGATION
    MM04 -. 原范围内修复后复验 .-> MM03
    MM04 -. 修复需重新规划 .-> MM02
    MM04 -. 验收或授权变化 .-> MM01
    MM04 -. 必要证据或独立验证无法补齐 .-> MM05
    MM05 -. 产物或验证状态变化 .-> MM04
    MM05 -. 目标、授权或验收变化 .-> MM01
    DELEGATION -. 回执或效果不明 .-> RECOVERY
    INTERRUPTION -. 暂停受影响工作并回读实际状态 .-> RECOVERY
    RECOVERY -. 证据和授权支持续接 .-> RESUME
    RECOVERY -. 仍需处理新授权或改变路线 .-> MM01
    RECOVERY -. 无法恢复且其余工作已处理 .-> MM05
    MM05 -. 必要验收受阻 .-> BLOCKED
    DONE --> END
    BLOCKED --> END
    SINGLE --> END
    RESUME --> END
```

### Hook 子流程图

#### 入口 Hook 的子流程

边界确认后进入选路和任务规划。新约束影响在途工作时，同时进入恢复子流程。[入口合同](../hooks/entry.md)

```mermaid
flowchart TD
    START(["开始"])
    TRIGGER["新任务、补充指令或分工约束及能力变化"]
    INPUTS["取得真实指令、工作状态、代理限制和宿主能力"]
    SOURCES["按需查选路规则及委派能力"]
    EXECUTION["核对任务约定和当前事实"]
    EXECUTION_1["确认目标、交付、验收和授权，保留仍适用的要求"]
    EXECUTION_2["确认代理限制，按限制和分工价值选路"]
    EXECUTION_3["标明已知、未知和待核实项，推进无关的获准工作"]
    OUTPUTS["交出目标、边界、验收条件和补证事项"]
    EXIT{"边界足以选路和规划？"}
    READY["按适用路线进入任务规划"]
    PAUSE["暂停依赖冲突约束或未明授权的工作"]
    RECHECK["任务、范围、验收或代理限制改变时重查受影响事实"]
    END(["结束"])
    START -->|收到任务或需确认指令| TRIGGER
    START -. 已确认的任务边界变化或补齐证据 .-> RECHECK
    TRIGGER --> INPUTS
    INPUTS --> SOURCES
    SOURCES --> EXECUTION
    EXECUTION --> EXECUTION_1
    EXECUTION_1 --> EXECUTION_2
    EXECUTION_2 --> EXECUTION_3
    EXECUTION_3 --> OUTPUTS
    OUTPUTS --> EXIT
    EXIT -->|是| READY
    EXIT -->|冲突或授权不清| PAUSE
    RECHECK --> INPUTS
    READY --> END
    PAUSE --> END
```

#### 规划 Hook 的子流程

规划时逐项考虑同页所有 Hook 子项。对适用项明确所需证据、负责人和阻断后的落点，对条件项记触发条件，对当前不适用或事实待核实的项记录原因或缺口。用户目标、授权或验收改变后，回入口重核任务约定。[规划合同](../hooks/planning.md)

```mermaid
flowchart TD
    START(["开始"])
    TRIGGER["选路后规划，或任务边界、依赖、角色、验收变化"]
    INPUTS["读取当前目标、约束、验收、状态和适用的角色及能力"]
    SOURCES["查任务规划、依赖与交接规则及角色匹配"]
    EXECUTION["逐项规划工作和依赖"]
    EXECUTION_1["拆解任务，写明前置输入、执行者、影响范围和返回证据"]
    EXECUTION_2["确定分工和交接，核对决策与执行是否就绪"]
    EXECUTION_3["按新证据更新分工、顺序和验收，保留有效产物与派发记录"]
    HOOKS["逐项核对各 Hook 的适用性、触发条件、证据缺口和返回位置"]
    OUTPUTS["记录任务、依赖、职责、交付、验收办法及 Hook 触发和落点"]
    EXIT{"近期工作、职责和验收办法明确？"}
    READY["进入执行、符合条件的委派或已有产物复核"]
    PAUSE["补齐缺失前置，暂停依赖该前置的工作"]
    ENTRY["回入口重核任务约定"]
    RECHECK["依赖、资源、要求、角色或下游所需结果变化时只重查受影响项"]
    END(["结束"])
    START -->|当前任务需要规划| TRIGGER
    START -. 计划前提变化或取得新证据 .-> RECHECK
    TRIGGER --> INPUTS
    INPUTS -->|任务边界未确认| ENTRY
    INPUTS -->|任务边界已确认| SOURCES
    SOURCES --> EXECUTION
    EXECUTION --> EXECUTION_1
    EXECUTION_1 --> EXECUTION_2
    EXECUTION_2 -->|已有计划需调整| EXECUTION_3
    EXECUTION_2 -->|已有可执行安排| HOOKS
    EXECUTION_3 -->|任务约定变化| ENTRY
    EXECUTION_3 -->|确认计划仍在当前授权内| HOOKS
    HOOKS --> OUTPUTS
    OUTPUTS --> EXIT
    EXIT -->|是| READY
    EXIT -->|缺必要条件| PAUSE
    RECHECK --> INPUTS
    READY --> END
    PAUSE --> END
    ENTRY --> END
```

#### 主代理执行 Hook 的子流程

两条路线均可进入。多代理路线中主代理仍须遵守其命令执行边界。[主代理执行合同](../hooks/execution.md)

```mermaid
flowchart TD
    START(["开始"])
    TRIGGER["主代理准备推进自己承担的工作"]
    INPUTS["读取当前计划、可执行任务、允许路径及前置结果"]
    SOURCES["按任务边界和依赖判断并行或串行"]
    EXECUTION["按实际依赖执行工作项"]
    EXECUTION_1{"依赖、授权、执行边界和结束条件已确认？"}
    EXECUTION_2["执行并记录实际结果、失败和新证据，判断继续、调整或暂停"]
    EXECUTION_3["依赖就绪后推进下一项，多代理时核对主代理命令边界"]
    OUTPUTS["交出当前产物、操作证据或具体障碍"]
    EXIT{"本项交付可验证且依赖满足？"}
    READY["下游使用产物或进入验证"]
    PAUSE["暂停本项，按原因补证、复核计划或进入恢复"]
    RECHECK["输入、资源、授权或上游结果变化时重查其影响"]
    END(["结束"])
    START -->|推进已分配的工作| TRIGGER
    START -. 检出影响或补齐前置 .-> RECHECK
    TRIGGER --> INPUTS
    INPUTS --> SOURCES
    SOURCES --> EXECUTION
    EXECUTION --> EXECUTION_1
    EXECUTION_1 -->|是| EXECUTION_2
    EXECUTION_1 -->|缺授权或前置| OUTPUTS
    EXECUTION_2 --> OUTPUTS
    OUTPUTS --> EXIT
    EXIT -->|可验证| READY
    EXIT -->|有就绪的下一项| EXECUTION_3
    EXIT -->|缺证据或操作失败| PAUSE
    EXECUTION_3 --> INPUTS
    RECHECK --> INPUTS
    READY --> END
    PAUSE --> END
```

#### 委派 Hook 的子流程

单代理路线在触发判断处继续主代理工作。只有重新选入多代理路线后，才按下图核对委派条件。[委派合同](../hooks/delegation.md)

```mermaid
flowchart TD
    START(["开始"])
    TRIGGER{"多代理路线有具体派发、续接、替换或实例变化？"}
    SKIP["本项无委派，沿当前获准分工继续"]
    INPUTS["读取计划、角色、实例状态、参数、能力和当前前置结果"]
    SOURCES["查能力、角色匹配、复用、替换、交接和模型规则"]
    EXECUTION["核对适用的委派条件和宿主能力"]
    EXECUTION_1["匹配角色，核对职责、执行要求和回传证据"]
    EXECUTION_2{"按真实实例、在途工作和派发记录判断复用或创建"}
    EXECUTION_3["确需首次创建或获准替换时核实模型和强度，禁止 Ultra"]
    EXECUTION_4["核对旧任务未决效果，交接必要材料，按回执和依赖整合结果"]
    OUTPUTS["记录子任务、角色、实例、状态和证据，替换时记原因与剩余工作"]
    EXIT{"回执可信且本项产物可供下游使用？"}
    READY["主代理按依赖集成，将产物交还原阶段"]
    WAIT["排队或等前置，结果不明时进入恢复"]
    RECHECK["指令、任务、实例或模型与强度变化时重查相关条件"]
    END(["结束"])
    START -->|判断当前是否适用委派| TRIGGER
    START -. 委派条件或相关证据变化 .-> RECHECK
    TRIGGER -->|适用| INPUTS
    TRIGGER -->|当前无获准委派| SKIP
    INPUTS --> SOURCES
    SOURCES --> EXECUTION
    EXECUTION --> EXECUTION_1
    EXECUTION_1 --> EXECUTION_2
    EXECUTION_2 -->|同角色实例可续接| EXECUTION_4
    EXECUTION_2 -->|符合创建或替换条件| EXECUTION_3
    EXECUTION_2 -->|排队或实例/前置不明| WAIT
    EXECUTION_3 --> EXECUTION_4
    EXECUTION_4 --> OUTPUTS
    OUTPUTS --> EXIT
    EXIT -->|是| READY
    EXIT -->|仍有依赖或未决效果| WAIT
    RECHECK --> TRIGGER
    READY --> END
    WAIT --> END
    SKIP --> END
```

#### 验证 Hook 的子流程

本图适用于单项结果、汇总验收及修复复验。多代理按需委派独立验证，主代理核对返回证据。单代理缺少所需独立性时记录阻断。[验证合同](../hooks/verification.md)

```mermaid
flowchart TD
    START(["开始"])
    TRIGGER["接收结果、汇总、需独立验证或修复完成"]
    INPUTS["输入验收条件、当前产物、执行证据和检查方法"]
    SOURCES["按需查独立验证角色和派发结果交接规则"]
    EXECUTION["按实际风险和变化核对验收"]
    EXECUTION_1["选检查并逐项核对要求、当前产物、证据时效和结果"]
    EXECUTION_2["需要独立验证时核实执行者及证据，多代理可按委派合同派发"]
    EXECUTION_3["缺陷先核对修复范围，并逐项记录通过、失败、跳过和受阻"]
    OUTPUTS["交出验收与证据对应关系、失败原因、缺项及影响"]
    EXIT{"必要验收均有当前证据，且所需独立性满足？"}
    READY["通过的结果供下游使用，最终验收通过后进入交付"]
    REPAIR["原范围内返回执行或委派，范围改变先回入口或规划"]
    PAUSE["缺证据或独立性时补齐条件，无法补齐则报告受阻"]
    RECHECK["产物、依赖、验收变化或修复完成后按交接仅复核受影响项目"]
    END(["结束"])
    START -->|接收结果或汇总验收| TRIGGER
    START -. 修复完成或验收证据变化 .-> RECHECK
    TRIGGER --> INPUTS
    INPUTS --> SOURCES
    SOURCES --> EXECUTION
    EXECUTION --> EXECUTION_1
    EXECUTION_1 -->|要求独立验证| EXECUTION_2
    EXECUTION_1 -->|无独立性要求| EXECUTION_3
    EXECUTION_2 --> EXECUTION_3
    EXECUTION_3 --> OUTPUTS
    OUTPUTS --> EXIT
    EXIT -->|是| READY
    EXIT -->|存在缺陷| REPAIR
    EXIT -->|证据过期、不足或独立性缺失| PAUSE
    RECHECK --> INPUTS
    READY --> END
    REPAIR --> END
    PAUSE --> END
```

#### 恢复 Hook 的子流程

在任意阶段按受影响工作项触发。恢复后重查目标阶段的进入条件。[恢复合同](../hooks/recovery.md)

```mermaid
flowchart TD
    START(["开始"])
    TRIGGER["中断、调用失败、状态异常、效果未知或新约束影响在途工作"]
    INPUTS["读取最后可信状态、任务、真实回执、可能受影响的产物和依赖"]
    SOURCES["按需查同角色复用、交接及计划调整规则"]
    EXECUTION["按真实效果确定可恢复的范围"]
    EXECUTION_1{"核实状态和已发生的效果，再判断可否恢复"}
    EXECUTION_2["核对修复边界，优先续接原执行者，查异常实例状态和可续接性"]
    EXECUTION_3["停止旧派发，按宿主能力暂停或取消受影响任务，未知效果记为未决"]
    EXECUTION_4["推进独立获准工作，必要时更新依赖或执行者，约束变化回入口"]
    OUTPUTS["交出可信恢复位置、有效产物、剩余工作和未决事项"]
    EXIT{"已证明受影响工作可以安全续接？"}
    READY["返回原位置或调整后已就绪的阶段"]
    PAUSE["暂停相关工作，报告具体阻断和所需条件"]
    RECHECK["状态变化、迟到回执或新事实出现时重查影响"]
    END(["结束"])
    START -->|收到恢复事件| TRIGGER
    START -. 迟到回执或新事实影响已知效果 .-> RECHECK
    TRIGGER --> INPUTS
    INPUTS --> SOURCES
    SOURCES --> EXECUTION
    EXECUTION --> EXECUTION_1
    EXECUTION_1 -->|在途任务因新约束失效| EXECUTION_3
    EXECUTION_1 -->|确认可恢复| EXECUTION_2
    EXECUTION_1 -->|效果不明，停止重放| EXECUTION_4
    EXECUTION_2 --> EXECUTION_4
    EXECUTION_3 --> EXECUTION_4
    EXECUTION_4 --> OUTPUTS
    OUTPUTS --> EXIT
    EXIT -->|是| READY
    EXIT -->|仍缺条件| PAUSE
    RECHECK --> INPUTS
    READY --> END
    PAUSE --> END
```

#### 交付 Hook 的子流程

报告受阻也走交付子流程。完成取决于必要验收和当前证据。[交付合同](../hooks/delivery.md)

```mermaid
flowchart TD
    START(["开始"])
    TRIGGER["准备结束任务、交付或报告受阻"]
    INPUTS["读取用户指令、验收、实际产物、验证和适用的委派结果"]
    SOURCES["查主代理验收和交付证据责任"]
    EXECUTION["核对交付的实际结果与证据"]
    EXECUTION_1["确认产物可用性，列实际产物、检查和影响验收的缺项"]
    EXECUTION_2["将实际效果与证据对应，超范围操作另按当前授权判断"]
    EXECUTION_3["输入或结果变化时回受影响的需求、任务或验证项并更新交付状态"]
    OUTPUTS["给出结果、验证状态和产物链接，或阻断与恢复条件"]
    EXIT{"必要交付物已通过适用验收？"}
    READY["完成任务"]
    PAUSE["报告受阻及缺少的条件"]
    RECHECK["交付物、验收要求或验证状态变化时重查受影响项"]
    RETURN["返回对应阶段，取得最新证据再进入交付"]
    END(["结束"])
    START -->|准备交付或报告受阻| TRIGGER
    START -. 交付或验收条件变化 .-> RECHECK
    TRIGGER --> INPUTS
    INPUTS --> SOURCES
    SOURCES --> EXECUTION
    EXECUTION --> EXECUTION_1
    EXECUTION_1 --> EXECUTION_2
    EXECUTION_2 -->|输入或结果变化| RECHECK
    EXECUTION_2 -->|当前证据可用| OUTPUTS
    RECHECK --> EXECUTION_3
    EXECUTION_3 --> RETURN
    OUTPUTS --> EXIT
    EXIT -->|是| READY
    EXIT -->|仍缺条件| PAUSE
    READY --> END
    PAUSE --> END
    RETURN --> END
```

## 阶段与适用 Hook

从路线选择器进入。主代理已识别满足用户要求或带来协调收益的分工，派发前核实各自的依赖、角色和宿主能力。

1. **MM01 — 需求确认** 按[入口 Hook](../hooks/entry.md)确认目标、用户约束、交付物和验收条件。任务边界足以选路和规划时退出。
2. **MM02 — 任务规划** 基于已确认的任务边界进入[规划 Hook](../hooks/planning.md)。逐项核对同页 Hook 子流程，明确适用条件、证据与回退位置，再确定近期工作、依赖、分工和验收办法。按工作项核对委派、主代理执行及独立验证的触发和证据，主代理负责跨任务决策与集成。

   主会话以 Ultra 启动时，包括此前使用其他档位、随后以 Ultra 开启新对话，进入本路线后必须按当前[主代理职责](../references/roles/main-agent.md)和[子代理角色定义](../references/delegation/delegation-policy.md#任务和角色匹配)制定计划。派发前逐项确定执行者、前置依赖、预期产物和验收条件。主代理负责关键决策、协调、集成和最终验收，按角色职责分配事实取证、实施、独立验证及另获授权的 Git 操作。优先复用同角色实例，新建或替换子代理前按[模型与推理强度规则](../references/delegation/delegation-policy.md#模型与推理强度)确认实际采用的推理强度为非 Ultra。
3. **MM03 — 任务执行** 按[委派 Hook](../hooks/delegation.md)核实依赖、角色、现有实例和宿主能力后派发或续接。按实际回执核对产物和未决影响，可用于下游时由主代理集成。主代理承担的工作按[主代理执行 Hook](../hooks/execution.md)核对进入与退出。
4. **MM04 — 结果验证** 按[验证 Hook](../hooks/verification.md)用当前产物和实际检查核对验收条件。必要验收均有当前证据时通过，失败或缺证据的项目进入流程控制。
5. **MM05 — 交付** 准备交付或报告阻断时进入[交付 Hook](../hooks/delivery.md)，核对实际产物和验证状态。通过适用验收后结束为完成，受阻时说明缺项。

## 变更与流程控制

先按[阶段进入与退出](README.md#阶段进入与退出)核对证据，再依据变化选择落点。

| 变化或当前状态 | Hook 与落点 |
| --- | --- |
| 目标、范围、授权、验收或代理约束改变 | 回到 MM01，按[入口 Hook](../hooks/entry.md)重查变化。分工约束或可用能力影响路线时，按[路线选择](coding.md)重新判断。涉及在途委派时，先按[恢复 Hook](../hooks/recovery.md)处理受影响的旧任务。沿用本路线时，回到 MM02 更新受影响的计划。切换后进入选定路线中满足条件的阶段。 |
| 任务依赖、分工或能力变化 | 回到 MM02，按[规划 Hook](../hooks/planning.md)更新受影响计划。现有分工仍可行且仅实例状态变化时，按[委派 Hook](../hooks/delegation.md)在相关阶段判断续接、等待或替换。派发前核对所需前置结果和相关旧实例的未决效果。 |
| 已有产物满足当前执行要求，或该项只需复核 | 当前产物、计划和适用的委派交付证据满足进入条件时，可从 MM02 直接进入 MM04。需要独立验证时，按[验证 Hook](../hooks/verification.md)核实独立性，涉及派发时同时应用[委派 Hook](../hooks/delegation.md)。 |
| 验证发现缺陷或交付物发生变化 | MM04 按[验证 Hook](../hooks/verification.md)核对修复范围。原范围内的修复回到 MM03，由职责匹配的执行者处理。涉及范围或计划变更时回到 MM01 或 MM02。修复后回到 MM04，沿用原有独立性要求复核受影响项。交付期间证据过期也回到 MM04，必要验收通过后再回 MM05。 |
| 中断、调用失败、子代理失联或结果不明 | 先按[恢复 Hook](../hooks/recovery.md)核对回执、在途操作和实际效果。新约束使在途工作失效时，按宿主能力暂停或取消，并保留无法核实的未决效果。条件恢复后回到原阶段或修订后计划的就绪阶段。续接子任务时按[委派 Hook](../hooks/delegation.md)优先复用同角色实例。需要调整分工时回到 MM02，无法恢复时在 MM05 报告具体阻断。 |

## 模式边界

任务数量、角色、开始时机、模型和推理强度随计划演进。后续工作优先派给同角色已有实例。替换仅按[委派合同](../hooks/delegation.md)核实的例外办理。主代理按[自身职责](../references/roles/main-agent.md#执行要求)推进工作，汇总实际证据并验收。

## 按条件触发的 Hooks

按当前动作查阅[Hook 触发目录](../hooks/README.md)，遇到中断或未知效果时读取[恢复 Hook](../hooks/recovery.md)。

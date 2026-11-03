# 规则上下文节点与分支映射

[English](node-mapping.md) | [简体中文](node-mapping_zh_cn.md)

本开发参考将稳定的 `rules_get_context` 节点和原始 `legacy_branch` 值映射到既有 Skill 政策。链接的 owner 仍为权威；本映射不新建政策、状态、权限或 child 放行。查询只返回材料，绝不执行分支。混合产出须拆成有界 slice 并分别分类。

每个分支记录触发条件、适用动作、通过证据和各自的失败边界。条件政策作为材料随闭包携带；只有其自身触发条件与授权适用时才发生作用。

## Node: contract

权威来源：[政策 owner](../../../../docs/skill/references/coding/layer-02-workflow-concepts/entry-and-context/contract_zh_cn.md#动作)。

入口动作：报告此有界节点的有源条件；查询本身不产生工作流效果。

### ready

- 触发: 请求结果、范围、约束、决定和验收条件均已知。
- 动作: 记录这些事实并区分观察与假设。
- 通过: Contract 四个维度和重要决定均明确。
- 失败: 必需输入缺失或冲突时暂停依赖该输入的 slice 并指出缺口。

### amend

- 触发: 经核实的事实或用户指令实质改变当前 Contract。
- 动作: 记录并分析变化，在既有授权内同步 Contract、计划和依赖决定。
- 通过: 受影响工作恢复前，修改后的目标、范围、约束和验收条件均明确。
- 失败: 无法确认变化或授权时，不放行受影响工作。

### blocked

- 触发: 重要 Contract 输入、决定或必要授权缺失或冲突。
- 动作: 报告确切缺口或冲突并暂停依赖它的 slice。
- 通过: 阻塞项及其对放行的影响明确。
- 失败: 不得假定答案或扩张授权以恢复工作。

## Node: mode

权威来源：[政策 owner](../../../../docs/skill/references/coding/layer-02-workflow-concepts/entry-and-context/mode_zh_cn.md#动作)。

入口动作：报告此有界节点的有源条件；查询本身不产生工作流效果。

### single-agent

- 触发: 父级记录确认 Single-Agent 且锁定数量为零。
- 动作: 核对记录的模式、数量、空 allocation 和必需入口能力。
- 通过: 有效的零 child 模式已记录，但尚未放行 slice。
- 失败: 模式、数量或能力证据缺失或不一致时阻塞依赖工作。

### multi-agent

- 触发: 父级记录确认 Multi-Agent 及锁定的正整数 child 数量。
- 动作: 核对数量、恰好对应数量的初始未绑定预留槽位和必需能力。
- 通过: 锁定模式与 allocation 结构有效，但尚未放行 child 或 slice。
- 失败: 槽位缺失、额外、不一致或必需能力缺失时阻塞依赖工作。

### blocked

- 触发: 无法确认所选模式、锁定数量、allocation 结构或入口能力。
- 动作: 保留当前记录并报告缺失或冲突的精确门禁证据。
- 通过: 依赖路线保持暂停且阻塞原因已记录。
- 失败: 不得推定新模式、初始化存储或创建 child 以绕过门禁。

## Node: context

权威来源：[政策 owner](../../../../docs/skill/references/coding/layer-02-workflow-concepts/entry-and-context/context_zh_cn.md#动作)。

入口动作：报告此有界节点的有源条件；查询本身不产生工作流效果。

### sufficient

- 触发: 当前权威上下文能够回答下一 slice 的有界问题。
- 动作: 使用前核对来源、范围、owner、新鲜度和相关 epoch。
- 通过: 所需最少事实对待决事项而言是当前且可用的。
- 失败: 材料过期、不完整或冲突时须刷新后才能用于依赖工作。

### request evidence

- 触发: 能够指出必要事实缺口且可通过获准途径请求。
- 动作: 指出并请求最小必要证据，同时暂停依赖放行。
- 通过: 请求和受影响决定明确，并将在取得证据后重过检查点。
- 失败: 不存在获准获取途径时，将依赖工作标为 blocked。

### blocked

- 触发: 必要上下文无法取得，或必要决定与授权冲突尚未解决。
- 动作: 报告确切不可用证据或冲突并暂停依赖工作。
- 通过: 阻塞项及其对下一 slice 的影响明确。
- 失败: 不得将未核实上下文或不可用的可选建议当作授权。

## Node: decision

权威来源：[政策 owner](../../../../docs/skill/references/coding/layer-02-workflow-concepts/decision-and-execution/decision_zh_cn.md#动作)。
获授权路线提供工作流路由建议时，查阅[工作流路由建议](../../../../docs/skill/references/coding/layer-01-fundamental-concepts/execution-planning/workflow-routing-advice_zh_cn.md#通用规范)。

入口动作：报告此有界节点的有源条件；查询本身不产生工作流效果。

### decided

- 触发: 当前事实和 Contract 支持一个有界方向。
- 动作: 记录决定、相关选项、约束、选定方向及边界。
- 通过: 一个获授权的下一 slice 及其返回边界明确。
- 失败: 重要事实改变方向时，继续前返回 Contract 与 Decision。

### evidence-on-demand

- 触发: 能够指出并请求待决事项所需的事实缺口。
- 动作: 请求有界证据并暂停依赖放行，之后重新经过检查点。
- 通过: 所需事实及受影响决定明确，尚未选出最终分支。
- 失败: 获取未获授权或必要决定与授权冲突仍未解决时使用 blocked。

### blocked

- 触发: 下一 slice 的必要决定、证据或授权不可用或冲突。
- 动作: 指出精确阻塞项并保持依赖 slice 未放行。
- 通过: 缺失输入和被阻塞效果已记录。
- 失败: 可选建议失败不能选定 Core 分支或产生授权。

## Node: slice

权威来源：[政策 owner](../../../../docs/skill/references/coding/layer-01-fundamental-concepts/execution-control/execution-control_zh_cn.md#interaction-slice)。

入口动作：报告此有界节点的有源条件；查询本身不产生工作流效果。

### released

- 触发: Contract 与决定授权一个具体有界 Interaction Slice。
- 动作: 记录目标、允许路径与变更以及返回条件。
- 通过: 仅该 slice 被放行且边界明确。
- 失败: 到达未放行边界或返回条件前须暂停。

### amend

- 触发: 重要事实要求改变拟议 slice 或其 Contract 边界。
- 动作: 返回 Contract 和决定以记录并评估变化。
- 通过: 仅在确认范围与授权后放行修改后的 slice。
- 失败: 该决定或授权未解决时不得执行变更范围。

### stop

- 触发: 到达返回条件、未解决阻塞或未放行边界。
- 动作: 停止依赖工作并报告当前进展与边界。
- 通过: 已停止效果及下一决定所需证据明确。
- 失败: 不得通过重新命名相同工作越过边界继续。

## Node: delegation

权威来源：[政策 owner](../../../../docs/skill/references/coding/layer-01-fundamental-concepts/delegation/delegation-state-record_zh_cn.md#记录结构)。
Multi-Agent allocation 状态适用时，查阅[角色分配](../../../../docs/skill/references/coding/layer-01-fundamental-concepts/delegation/delegation-child-role-allocation_zh_cn.md#通用规范)。
仅在实际创建新 child 时，查阅[child 创建](../../../../docs/skill/references/coding/layer-01-fundamental-concepts/delegation/delegation-child-creation_zh_cn.md#通用规范)。

入口动作：报告此有界节点的有源条件；查询本身不产生工作流效果。

### not applicable

- 触发: 选择 Single-Agent，或当前有界 slice 由 Root 执行且确无 child 创建、分配、复用、派发或恢复效果。
- 动作: 记录本 slice 不适用 delegation 的具体原因。
- 通过: 根据当前范围和状态确认不存在 child 效果。
- 失败: 必需 child 能力不可用时为 blocked，不能标为不适用。

### reserved

- 触发: 当前阶段存在有效预留 allocation 且 child 身份仍未绑定。
- 动作: 读取规范记录并保留分阶段的角色和 slice 条件。
- 通过: 当前预留有效，但不得推定角色已分配或 child 创建已放行。
- 失败: allocation 证据缺失或冲突时阻塞依赖的 child 效果；不得重置未知状态。

### bound

- 触发: 可信的当前会话 child 身份已经绑定到其原 allocation。
- 动作: 核对并保留该身份和规范 allocation 以供获授权的下一步使用。
- 通过: 可信绑定及其适用生命周期状态已确认。
- 失败: 身份不可信、缺失或冲突时阻塞依赖的复用或派发；描述本身不能创建 child。

### blocked

- 触发: 必需 child 能力、allocation、可信身份或生命周期决定不可用或冲突。
- 动作: 保留已确认的规范状态并报告被阻塞的具体 child 效果。
- 通过: 缺失前提和受影响效果明确。
- 失败: 不得重置未知状态、伪造绑定或替换 child 以绕过阻塞。

## Node: implementation

权威来源：[政策 owner](../../../../docs/skill/references/coding/layer-02-workflow-concepts/decision-and-execution/implementation_zh_cn.md#动作)。

入口动作：报告此有界节点的有源条件；查询本身不产生工作流效果。

### complete

- 触发: 已在授权范围内完成放行的实现 slice。
- 动作: 返回变更路径及聚焦的暂定检查或具体问题。
- 通过: 已实现获准 slice 并具备聚焦证据。
- 失败: 聚焦检查不是最终 Verification，未解决问题须明确报告。

### blocked

- 触发: 实现所需能力、路径、授权或重要输入不可用。
- 动作: 停止受影响工作并报告确切障碍和当前路径。
- 通过: 被阻塞部分与其余获授权工作可区分。
- 失败: 不得扩大范围或替换为未授权效果以继续。

### return for control

- 触发: 实现期间遇到返回条件、需求变化或重要边界。
- 动作: 暂停并向 Control 返回证据和拟议决定。
- 通过: 受影响实现保持暂停，直至当前适当决定和 slice 放行。
- 失败: 不得使用原放行执行已变化的边界。

## Node: control

权威来源：[政策 owner](../../../../docs/skill/references/coding/layer-01-fundamental-concepts/execution-control/execution-control_zh_cn.md#control-checkpoint)。

入口动作：报告此有界节点的有源条件；查询本身不产生工作流效果。

### continue

- 触发: 当前 Contract 与放行边界对下一有界工作仍有效。
- 动作: 仅放行下一个有界 slice 并记录当前进展信号。
- 通过: 该 slice 的范围、owner 和返回条件明确。
- 失败: 出现新的重要决定或未放行边界时须再次返回 Control。

### amend

- 触发: 当前证据表明恢复工作前必须改变 Contract 或边界。
- 动作: 在既有授权内同步并决定变化，之后才放行受影响工作。
- 通过: 修改后的 Contract 和下一个有界决定明确。
- 失败: 授权缺失或变化未解决时，受影响工作保持停止。

### stop

- 触发: 必要决定、能力、授权或边界条件阻止继续。
- 动作: 停止依赖工作并记录确切原因。
- 通过: 停止范围和下一步所需输入明确。
- 失败: 不得把未解决阻塞转成 Continue 放行。

### evidence-on-demand

- 触发: Control 需要可通过获准请求取得的明确缺失事实。
- 动作: 暂停放行，请求有界证据并返回 Control。
- 通过: 证据请求是中间状态，不是第四种最终授权结果。
- 失败: 证据无法取得或必要决定与授权冲突时停止受影响工作。

## Node: verification

权威来源：[政策 owner](../../../../docs/skill/references/coding/layer-02-workflow-concepts/verification-and-repair/verification_zh_cn.md#动作)。
按[报告动作](../../../../docs/skill/references/coding/layer-02-workflow-concepts/verification-and-repair/verification-reporting_zh_cn.md#动作)及其[通过条件](../../../../docs/skill/references/coding/layer-02-workflow-concepts/verification-and-repair/verification-reporting_zh_cn.md#通过条件)分类并报告结果。
按[独立性动作](../../../../docs/skill/references/coding/layer-02-workflow-concepts/verification-and-repair/verification-independence_zh_cn.md#动作)及其[通过条件](../../../../docs/skill/references/coding/layer-02-workflow-concepts/verification-and-repair/verification-independence_zh_cn.md#通过条件)分类并报告逻辑验证或独立验证；Contract 要求时必须满足真正独立的 Session。

入口动作：报告此有界节点的有源条件；查询本身不产生工作流效果。

### pass

- 触发: 精确当前状态的全部必需检查均有通过证据且满足所需独立性。
- 动作: 记录当前指纹、检查、结果类别和剩余风险。
- 通过: 当前验证覆盖范围内的每个必需验证项均有当前通过证据。
- 失败: 证据过期、检查失败或缺少必需独立性时不能通过。

### failure

- 触发: 必需的当前状态检查出现具体失败结果。
- 动作: 报告失败、受影响路径及其阻塞效果，供诊断使用。
- 通过: 失败项及其当前证据明确。
- 失败: 不得因其他检查通过而报告完成或隐藏失败。

### inconclusive

- 触发: 必需检查、证据或必需独立验证不可用、不完整或含糊。
- 动作: 报告不可用、假设和未解决证据及其阻塞效果。
- 通过: 限制及受影响验收项明确。
- 失败: 不得将同会话逻辑检查标为独立验证或推定通过。

### not applicable with reason

- 触发: 有事实证明某个验证项不属于当前授权范围。
- 动作: 记录该项及其不适用的事实原因。
- 通过: 不适用原因可审核，且不豁免其他必需检查。
- 失败: 适用性未知或证据不可用时为 inconclusive，不是不适用。

## Node: repair

权威来源：[政策 owner](../../../../docs/skill/references/coding/layer-02-workflow-concepts/verification-and-repair/repair_zh_cn.md#动作)。

入口动作：报告此有界节点的有源条件；查询本身不产生工作流效果。

### not applicable with reason

- 触发: 没有需要修复候选的适用失败证据。
- 动作: 记录当前证据及无需修复诊断的原因。
- 通过: 原因和未受影响的验证状态明确。
- 失败: 验证证据缺失或未知不能证明无需修复。

### repair

- 触发: 具体失败具有可识别的受影响路径和可能的最小修复候选。
- 动作: 描述失败、路径与最小候选，并按适用 owner 交接。
- 通过: 候选与证据明确，不预设修复授权。
- 失败: 需要决定的重要变化会暂停依赖修复；本检查点不授权也不执行修复。

### blocked

- 触发: 无法确认失败、受影响范围、必要决定或修复能力。
- 动作: 报告缺失的诊断输入或决定并暂停依赖修复。
- 通过: 阻塞项和未解决失败明确。
- 失败: 不得通过大范围清理或假定批准绕过缺失输入。

## Node: documentation

权威来源：[政策 owner](../../../../docs/skill/references/coding/layer-02-workflow-concepts/completion-and-effects/documentation_zh_cn.md#动作)。

入口动作：报告此有界节点的有源条件；查询本身不产生工作流效果。

### complete

- 触发: 获授权文档或注释已按适用的已验证状态更新。
- 动作: 确认双语镜像、当前文档 epoch、适用检查及任何所请求知识写入回执。
- 通过: 必需文档输出和检查均为当前，限制已报告。
- 失败: 必需写入失败、证据过期或内容影响的重验证未解决时不能完成。

### not applicable with reason

- 触发: 本 slice 不涉及文档、注释或所请求的可复用知识输出。
- 动作: 记录基于范围的具体原因。
- 通过: 原因明确，且不豁免适用的实现验证。
- 失败: 请求过但未完成的文档属于 incomplete，不是不适用。

### blocked

- 触发: 必需文档路径、能力、检查、知识写入或重要决定不可用。
- 动作: 报告具体被阻塞输出并保留当前证据。
- 通过: 缺失前提和未完成输出明确。
- 失败: 不得替换为未获准的文档范围或声称写入成功。

## Node: git

权威来源：[政策 owner](../../../../docs/skill/references/coding/layer-02-workflow-concepts/completion-and-effects/git_zh_cn.md#动作)。

入口动作：报告此有界节点的有源条件；查询本身不产生工作流效果。

### no Git effect

- 触发: 获授权 slice 未请求 Git 或外部仓库效果。
- 动作: 记录无需 Git 效果。
- 通过: 无效果结论与当前请求范围一致。
- 失败: 请求过但未执行的 Git 效果不能标为无效果。

### authorized effect

- 触发: 具体 Git 或外部效果已针对精确目标获授权。
- 动作: 确认精确仓库、分支、远端、操作、授权及当前已验证指纹后，仅执行该获授权操作，并按需记录或核验结果。
- 通过: 获授权操作已针对精确目标完成，记录最新适用 epoch，且与其已验证内容指纹一致。
- 失败: 目标含糊、冲突、内容过期或缺少授权时停止。

### blocked

- 触发: 请求的 Git 效果缺少明确目标、授权、当前验证或必需能力。
- 动作: 报告确切障碍并保持受影响操作未执行。
- 通过: 请求效果及阻塞前提明确。
- 失败: 不得包含无关变更或扩大操作以恢复。

## Node: acceptance

权威来源：[政策 owner](../../../../docs/skill/references/coding/layer-02-workflow-concepts/completion-and-effects/acceptance_zh_cn.md#动作)。

入口动作：报告此有界节点的有源条件；查询本身不产生工作流效果。

### complete

- 触发: 每个适用的最新 epoch 和 Contract 验收条件均具备当前必需证据。
- 动作: 报告各验收项、内容、文档和 Git 状态及剩余风险。
- 通过: 不存在未解决的必需项、能力、验证边界或授权。
- 失败: 证据过期或必需项未解决时不能声称完成。

### incomplete

- 触发: 已知适用或必需的工作、检查或修复仍待完成或尚未执行。
- 动作: 报告每个未完成项及当前证据，不声称完成。
- 通过: 剩余工作及其状态明确。
- 失败: 任何必需项未完成时不得称任务完成。

### blocked

- 触发: 实际授权、能力、关键证据或必要决定缺失使必需下一步无法继续。
- 动作: 报告具体缺失前提、受影响下一步及当前未完成状态。
- 通过: 阻塞项及其影响明确。
- 失败: 困难或耗时本身不是 blocked 原因，blocked 也不是 complete。

## Node: task_intent

权威来源：[政策 owner](../../../../docs/skill/SKILL_zh_cn.md#适用范围)。

入口动作：报告此有界节点的有源条件；查询本身不产生工作流效果。

### coding

- 触发: 权威任务事实表明涉及仓库或项目探索、实现、重构、调试、测试、文档、开发工具输出或非简单 Git 工作。
- 动作: 将当前任务分类为 Coding 并应用既有 Coding 范围。
- 通过: 分类有直接事实及其有界范围支持。
- 失败: 含 Coding 工作的混合任务仍为 Coding；未列出示例不能证明排除。

### not coding

- 触发: 直接权威事实证明任务不属于 Coding 范围。
- 动作: 记录非 Coding 分类的来源及有界原因。
- 通过: 当前证据明确支持范围排除。
- 失败: 未列举或任务事实未知不能证明 not coding。

### unclear

- 触发: 现有权威事实不足以确认任务是否属于 Coding 范围。
- 动作: 指出缺失的范围事实并保持依赖分类未决。
- 通过: 不确定性及其对下一决定的影响明确。
- 失败: 不得因缺少示例或证据不足推定 not coding。

## Node: output_class

权威来源：[政策 owner](../../../../docs/skill/references/coding/layer-01-fundamental-concepts/delegation/delegation-mode-confirmation_zh_cn.md#会话模式选择)。
角色职责和普通文档边界参见[Session 角色职责](../../../../docs/skill/references/coding/layer-01-fundamental-concepts/session-runtime/session-role-ownership_zh_cn.md#通用规范)。

入口动作：报告此有界节点的有源条件；查询本身不产生工作流效果。

### code_configuration

- 触发: 当前有界产出 slice 包含代码或配置。
- 动作: 将该 slice 分类为 code_configuration 并应用既有职责和门禁。
- 通过: 分类指出实际代码或配置产出。
- 失败: 不得用 ordinary documentation 或 other 分类掩盖代码。

### skill_instructions

- 触发: 当前有界产出 slice 变更 Skill 指令。
- 动作: 将该 slice 分类为 skill_instructions；任何委派仍须满足既有 child 门禁。
- 通过: Skill 指令产出及其负责角色明确。
- 失败: 该分类本身不授权创建 child 或改变政策。

### ordinary_documentation

- 触发: 当前有界产出 slice 是普通非 Skill 文档。
- 动作: 将该 slice 分类为 ordinary_documentation 并保留 Root 编写职责。
- 通过: 普通文档范围与任何代码或 Skill 指令 slice 分开。
- 失败: 不得将普通文档委派给 child 或用此类别掩盖代码。

### other

- 触发: 有界产出已知且不属于 code_configuration、skill_instructions 或 ordinary_documentation。
- 动作: 记录已知产出并将该 slice 分类为 other。
- 通过: 证据明确证明前三类均不适用。
- 失败: 未知产出不是 other，且该类不授予创建授权。

### unknown

- 触发: 证据不足以分类当前有界产出。
- 动作: 指出缺失的产出事实并保持分类未决。
- 通过: 不确定性明确，且未选择其他类别。
- 失败: 不得将 unknown 当作 other 或用其授权创建 child。

## Node: contract_change

权威来源：[政策 owner](../../../../docs/skill/references/coding/layer-02-workflow-concepts/entry-and-context/contract_zh_cn.md#动作)。

入口动作：报告此有界节点的有源条件；查询本身不产生工作流效果。

### unchanged

- 触发: 当前证据明确表明目标、范围、约束和验收四维均无实质变化。
- 动作: 依赖工作继续前记录四维比较。
- 通过: 四个 Contract 维度对当前 slice 仍有效。
- 失败: 某维度缺少证据不能证明其未变。

### amend

- 触发: 已确认实质变化且所需修改属于既有授权范围。
- 动作: 受影响工作恢复前同步 Contract、计划和 Decision。
- 通过: 修改后的四维及依赖决定明确。
- 失败: 新增效果缺少授权时，即使已修改也保持未放行。

### blocked

- 触发: 无法确认必要变化、其范围或所需授权。
- 动作: 指出确切未决变化或授权并暂停受影响工作。
- 通过: 阻塞项和受影响 Contract 维度明确。
- 失败: 不得将未知范围或授权当作 unchanged 或获授权修改。

## Node: verification_impact

权威来源：[政策 owner](../../../../docs/skill/references/coding/layer-02-workflow-concepts/verification-and-repair/verification-epoch_zh_cn.md#动作)。

入口动作：报告此有界节点的有源条件；查询本身不产生工作流效果。

### implementation/content

- 触发: 当前证据表明仅 implementation/content 维度发生变化。
- 动作: 推进该 epoch 并安排或执行适用的当前状态检查。
- 通过: 受影响内容的旧验证不再作为当前证据。
- 失败: 不得跳过内容验证，也不得无证据推定其他维度变化。

### documentation

- 触发: 当前证据表明仅 documentation 维度发生变化。
- 动作: 推进该 epoch 并运行适用文档检查。
- 通过: 已具备变更产出的当前文档证据。
- 失败: 执行内容、Contract 或验收也变化时，应分类为多个受影响维度。

### Git metadata

- 触发: 当前证据表明仅 Git metadata 发生变化。
- 动作: 推进 Git metadata epoch 并比较目标内容与已验证指纹。
- 通过: Git 状态指向最新适用的已验证内容和文档。
- 失败: 内容不一致时返回相应验证；仅元数据变化不推进内容 epoch。

### multiple

- 触发: 当前证据确认至少两个验证维度发生变化。
- 动作: 推进每个受影响 epoch 并安排其适用检查或 Verification。
- 通过: 每个受影响维度均按当前证据追踪。
- 失败: 不得对任何已变维度沿用过期证据或遗漏适用检查。

### none

- 触发: 当前正面证据确认没有任何验证维度变化。
- 动作: 记录比较，并保留已经适用的检查和证据要求。
- 通过: 零变化维度由事实支持，而非由于信息缺失。
- 失败: 影响未知不是 none，none 也不豁免既有必需检查。

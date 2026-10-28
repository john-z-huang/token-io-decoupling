# Coding 子代理职责选择

[English](child-role-selection.md) | [简体中文](child-role-selection_zh_cn.md)

本文档负责为拟创建的子代理选择一个受维护的职责，以及职责选择 Decisions 政策。它消费[Session 职责归属](session-role-ownership_zh_cn.md)中的职责、[Session 模型](session-model_zh_cn.md)和[委派状态记录](delegation-state-record_zh_cn.md)中的当前身份与 allocation，以及[委派数量门禁](delegation-mode-count-gate_zh_cn.md)中的容量；不分配预算、不创建子代理，也不授权任何影响。

## 通用规范

### 职责请求边界

只使用四种受维护职责：`Primary Output`、`Change Verification`、`Context Bootstrap/Refresh` 和 `Documentation/Comments & Git Operations`。根据已放行任务匹配职责。当前会话身份和 allocation 必须读取权威状态记录；当前会话中已预留或已创建的职责不能再分配给另一个子代理。职责分配 owner 要求职责唯一，且已创建职责即使子代理已完成、失败、中断、取消或不可用仍被占用。不要计入来自其他会话的继承代理。Fork 必须先通过新的模式/数量门禁，然后才能选择职责。

在本文 owner 中，Root 已在 Context 和 Decision 之后授权并界定了拟派子代理任务的目标/范围，即视为该 proposed task 已放行。这不同于后续绑定和放行该子代理的 Interaction Slice。须在放行其 Interaction Slice 之前，为这个已授权任务选择并预留职责；不得等待子代理专属切片放行，因为该切片需要先有已分配职责。

用户明确要求创建子代理时，跳过职责选择 Decisions。用户提供了明确职责时遵循该职责；用户明确要求创建但未指定职责时，只有在创建已经通过其他门禁确认且该职责仍可用时，才以 `Primary Output` 为缺省。此规则不绕过 Single-Agent 模式、当前会话职责门禁、已批准预算、用户权限、已放行切片或子代理创建能力。

若没有适用的用户明确职责指令，先按[决策上下文生成](decision-context-generation_zh_cn.md)流程，从带来源事实生成并审阅有界决策上下文。之后使用获准的职责建议能力，并传入已审阅上下文和当前状态事实。生成决策问题是可选步骤。职责选择只能使用经过核实的当前会话事实仍允许的选项。

若上下文生成失败或返回证据不足，不得伪造描述或哈希，也不得用不可用的上下文继续调用下游职责建议请求。若已核实事实足够，Root 仍可根据本 Skill 直接作出职责判断；否则保持判断未决且不得创建子代理。上下文生成失败后不得自动调用下游建议操作。上下文生成失败本身不能证明应当继续创建。

### 职责 Decisions 指令

为拟创建的子代理选择一个已提供职责，或选择 `insufficient_evidence`。只使用已放行任务目标、交付内容、依赖、验证要求、已提供的当前会话状态和已加载职责 owner。职责必须匹配子代理实际要执行的工作。不得推断未提供的仓库事实、权限、预算能力或用户意图。事实冲突、任务横跨多个职责但没有已放行边界、所需 owner 政策不可用，或没有适合的职责时，选择 `insufficient_evidence`。该选择供 Root 审阅，不预留名额或创建子代理。

### 职责选项说明

#### Primary Output

用于主要的已授权代码/配置实现，或编写/编辑本 Skill 指令和参考文档。子代理仍必须遵守已放行切片边界。普通非 Skill 文档与评论仍由 Root 负责，即使任务同时包含代码变更。

#### Change Verification

用于只读检查已放行改动是否符合其合同与证据。验证者必须具有真正独立的当前会话身份，且不得实现、修复、暂存或提交被审查的改动。若无合格独立验证者，报告这一限制；不得改名职责来冒充独立验证。

#### Context Bootstrap/Refresh

用于有界检索或刷新 Root 后续判断或已放行切片所需的项目上下文。返回带引证的源路径或稳定引用，并区分观察事实和缺失上下文。不得授权实现或代替 Root 作语义判断。

#### Documentation/Comments & Git Operations

仅用于明确放行、属于子代理职责且权限允许的非简单 Git 工作。普通文档和评论由 Root 负责；在完成必需放行门禁后，Primary Output 可以编写或编辑本 Skill 的指令和参考文档。该职责不授权 Git 影响，也不得扩大已批准路径或操作范围。

#### insufficient_evidence

当提供事实不足以确定合规职责、职责与已放行切片冲突、当前会话职责状态不确定，或所需政策/能力不可用时选择。Root 可以依据维护的政策和当前证据复核；API 结果本身绝不授权创建。

### 审阅与兜底

预留职责前，Root 必须核实当前模式与 Session 身份、职责唯一性、可用批准预算、用户指令、已授权的拟派任务、权限和宿主能力。Interaction Slice 只能在预留了分配职责后才放行。上下文生成失败、Decisions 失败或证据不足不会自动选出职责，也不阻断 Root 独立审阅。若 Root 依据已核实事实独立确认应继续创建，只有拟派工作符合 `Primary Output` 职责且该职责尚未预留或创建时，才可将其用作缺省；其他门禁仍须通过。若四种受维护职责均已占用，Root 必须阻止再创建子代理，不得申请扩额：增加名额不能释放职责或允许重复职责。仅当至少还有一种不同职责未占用、但容量不足时，才能申请预算。不得再次选择相同职责、静默超出预算或替换已创建子代理。权威门禁与字段见[委派数量门禁](delegation-mode-count-gate_zh_cn.md)、[委派模式重入](delegation-mode-reentry_zh_cn.md)、[委派状态记录](delegation-state-record_zh_cn.md)和[子代理职责分配](delegation-child-role-allocation_zh_cn.md)。

## Codex CLI / ChatGPT Desktop 特别优化指令

当前会话暴露该工具且外发数据已获准时，只能在审阅生成的决策上下文和当前会话职责事实后调用 `workflow_select_child_role`。传入已审阅上下文、其输入哈希和当前职责状态。使用建议前，将返回的 `fact_fingerprint`、`context_input_hash`、`source_policy_hashes` 和 `input_hash` 与当前证据核对。该工具无状态且仅提供建议；随后必须单独完成受 Root 门禁控制的名额预留和创建流程。

## Claude Code CLI / Claude Desktop 特别优化指令

当前没有适用于此概念的特别优化；遵循通用规范。

## 相关概念

- [Session 职责归属](session-role-ownership_zh_cn.md) — 负责受维护的职责说明。
- [Session 模型](session-model_zh_cn.md) — 负责 Session 身份和 affinity。
- [委派数量门禁](delegation-mode-count-gate_zh_cn.md) — 负责锁定预算和获批扩展。
- [委派模式重入](delegation-mode-reentry_zh_cn.md) — 负责 Fork 的新门禁。
- [委派状态记录](delegation-state-record_zh_cn.md) — 负责当前会话 allocation 状态。
- [Coding 子代理职责分配](delegation-child-role-allocation_zh_cn.md) — 负责在已批准名额中预留已选职责。
- [Coding 子代理创建](delegation-child-creation_zh_cn.md) — 负责子代理创建能力及前置条件。
- [决策上下文生成](decision-context-generation_zh_cn.md) — 负责有界决策上下文的生成与审阅。

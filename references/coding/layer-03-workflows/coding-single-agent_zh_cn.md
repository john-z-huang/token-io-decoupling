# Coding 工作流——单代理模式

[English](coding-single-agent.md) | [简体中文](coding-single-agent_zh_cn.md)

本路线由 Coding 工作流选择；只有模式检查点放行单代理 Coding 后才有效。执行前，该检查点组合[委派状态记录](../layer-01-fundamental-concepts/delegation-state-record_zh_cn.md)、[模式确认](../layer-01-fundamental-concepts/delegation-mode-confirmation_zh_cn.md)、[模式/数量门禁](../layer-01-fundamental-concepts/delegation-mode-count-gate_zh_cn.md)和[模式重新进入](../layer-01-fundamental-concepts/delegation-mode-reentry_zh_cn.md) reference。

## 模式 Contract

- 所有工作保留在当前 Session 中。将 Input-side Reasoning、Primary Output、文档和适用检查视为逻辑阶段，而不是独立代理。
- [委派状态记录](../layer-01-fundamental-concepts/delegation-state-record_zh_cn.md)负责根状态记录；[模式确认](../layer-01-fundamental-concepts/delegation-mode-confirmation_zh_cn.md)负责单代理模式确认；[模式/数量门禁](../layer-01-fundamental-concepts/delegation-mode-count-gate_zh_cn.md)负责数量锁定；[模式重新进入](../layer-01-fundamental-concepts/delegation-mode-reentry_zh_cn.md)负责重新进入条件。子代理派发和生命周期不适用于本路线。
- 保留下方检查点序列中的 Contract、上下文、决策、控制边界、验证边界、文档边界、Git 授权和完成检查。
- “不要创建子代理”或“不要使用浏览器”等任务级禁止事项在整个任务期间持续有效。

## 组合输入

本路线组合[共享协议](../../share/shared-protocols_zh_cn.md)、[委派状态记录](../layer-01-fundamental-concepts/delegation-state-record_zh_cn.md)、[模式确认](../layer-01-fundamental-concepts/delegation-mode-confirmation_zh_cn.md)、[模式/数量门禁](../layer-01-fundamental-concepts/delegation-mode-count-gate_zh_cn.md)、[模式重新进入](../layer-01-fundamental-concepts/delegation-mode-reentry_zh_cn.md)、[Session 模型](../layer-01-fundamental-concepts/session-model_zh_cn.md)、[Session 职责归属](../layer-01-fundamental-concepts/session-role-ownership_zh_cn.md)和[执行控制](../layer-01-fundamental-concepts/execution-control_zh_cn.md)。模式检查点已经验证任务记录；下方检查点列表是完整的路线组合。

## 当前 Session 中的职责边界

职责 ownership 见[Session 职责归属](../layer-01-fundamental-concepts/session-role-ownership_zh_cn.md)；本路线在一个 Session 中执行逻辑阶段，无法提供独立 verifier。

## 本路线的运行环境要求

使用[运行环境能力清单](../layer-02-workflow-concepts/environment-capability-inventory_zh_cn.md)提供的能力清单和共用运行规则。本路线将所有阶段保留在当前 Session，不创建独立 Session 或 Worker 返回路径。所需能力不可用时，停止切片并报告。

## 路线顺序检查清单

在当前 Session 中按编号顺序执行每一阶段。对每个链接的 owner，核对适用动作和通过条件，记录结果及证据；必需结果缺失时停止。条件动作不适用时，逐项记录 `Not applicable` 及原因；存在链接或早期摘要不等于已经完成检查。Coding 选择器已在进入路线前完成第 1–3 阶段：核查其放行证据，不重复运行门禁。

1. **Contract 与共用协议。** 确认 [Contract 检查点](../layer-02-workflow-concepts/contract_zh_cn.md)明确目标、`ACTIVE_CONSTRAINTS` 中的用户/运行环境/仓库/权限/安全硬约束、已授权影响、已定决策、未解决问题和验收条件。应用[共享协议](../../share/shared-protocols_zh_cn.md)：维护一份当前 Semantic Contract，区分已观察事实与假设，后续变化保持稳定前缀并以小幅增量修订；必需上下文缺失时停止依赖切片。不得把未解决的问题当作实现授权。
2. **运行环境与能力。** 确认[运行环境检查点](../layer-02-workflow-concepts/environment_zh_cn.md)依据明确元数据将环境归入唯一分支，工具和工作区信息只作辅助证据；不得用浏览器、GUI 或视觉内容识别运行环境。分类仍有歧义时，使用厂商 owner 的原文兜底问题并暂停。检查[运行环境能力清单](../layer-02-workflow-concepts/environment-capability-inventory_zh_cn.md)中的真实模型、Profile 所需的每项参数、工具、文件系统/权限范围及 Session 能力。按[运行环境与模型厂商支持](../layer-01-fundamental-concepts/runtime-provider-support_zh_cn.md)应用该分支的模型规则。把缺失或未知的要求记入 `unavailable_capabilities`；阻塞依赖工作，不得推断或替换能力。
3. **模式与任务记录。** 确认[模式检查点](../layer-02-workflow-concepts/mode_zh_cn.md)只放行 `Single-Agent Coding`。核对[模式确认](../layer-01-fundamental-concepts/delegation-mode-confirmation_zh_cn.md)、[数量门禁](../layer-01-fundamental-concepts/delegation-mode-count-gate_zh_cn.md)和[状态记录](../layer-01-fundamental-concepts/delegation-state-record_zh_cn.md)：`gate_status: released`、`child_count: 0`、`allocations: []`，且没有未解决的能力阻塞。依据[模式重新进入](../layer-01-fundamental-concepts/delegation-mode-reentry_zh_cn.md)保持本次会话模式/数量不变；后续冲突指令阻塞依赖工作，直到新会话。本路线不得创建、派生、发送消息、移交或模拟额外 Agent 或 Session。
4. **Session 与职责边界。** 核对 [Session 模型](../layer-01-fundamental-concepts/session-model_zh_cn.md)和[职责归属](../layer-01-fundamental-concepts/session-role-ownership_zh_cn.md)：当前 Session 承担 Input-side Reasoning、Primary Output、文档/Git 和允许的检查阶段；职责标签不产生独立验证。按 [Context Firewall](../layer-01-fundamental-concepts/session-context-firewall_zh_cn.md)渐进读取，限制原始项目状态。语义决策和最终验收仍由输入侧阶段负责。
5. **上下文。** 在 [Context 检查点](../layer-02-workflow-concepts/context_zh_cn.md)提出下一切片所需回答的最小问题，只读取回答该问题必需的源文件、元数据、历史或证据。复用上下文前核对范围、owner、源路径、新鲜度和 epoch；只刷新受影响的事实。不需要有界侦察或恢复时记录原因；摘要不能代替权威源、Contract 或验证。
6. **决策与两级规划。** 在 [Decision](../layer-02-workflow-concepts/decision_zh_cn.md)说明实质问题、事实、约束、选项、选定方向、舍弃方案、授权路径/修改和未发布边界。应用[决策门禁](../layer-01-fundamental-concepts/execution-decision-gate_zh_cn.md)：除非任务符合简单快速路径，否则先形成包含 Problem、Known facts、Assumptions and unknowns、Decision questions、Solution envelope、Risks、Acceptance 和 Stages/checkpoints 的简洁 Decision Brief；实质选择未定时只发布侦察。用[执行规划](../layer-01-fundamental-concepts/execution-planning_zh_cn.md)安排有界检查、实现和聚焦检查，并写明预期证据。放行一个切片前确认所选方向符合 Contract。
7. **Interaction Slice 与实现。** 按[执行控制](../layer-01-fundamental-concepts/execution-control_zh_cn.md)写明 `Objective`、`Authorized scope/mutations`、`Return conditions` 和 `Unreleased boundary`。在 [Implementation](../layer-02-workflow-concepts/implementation_zh_cn.md)重新读取放行内容，只查看必需文件，实施最小的授权改动，排除无关清理和外部影响，运行聚焦的临时检查，并返回修改路径、证据、问题及仍未发布的边界。临时检查不是最终验收。
8. **阶段反馈。** 不确定性需要有界、产出证据的阶段时，应用[执行阶段反馈](../layer-01-fundamental-concepts/execution-stage-feedback_zh_cn.md)。在实质性观察点只保留压缩后的状态、发现、改动范围、验证、问题和需求；常规读取、修改和重复检查留在获准阶段内。出现新的实质选择时先返回第 6 阶段。
9. **控制边界。** 在 [Control](../layer-02-workflow-concepts/control_zh_cn.md)记录 `Status`、`Findings`、`Changed`、`Verification`、`Issue`、`Need` 和 `Unreleased boundary`。检查接口、schema、兼容、安全、风险、不可逆操作、范围或外部影响是否改变；明确选择 Continue、Amend、Stop 或 Evidence-on-Demand。只有处于现有边界内才可继续；越界前先修订 Contract 和 Decision。其他获准切片重复第 5–9 阶段。
10. **最终状态验证。** 在 [Verification](../layer-02-workflow-concepts/verification_zh_cn.md)记录当前最终状态指纹和验收条件，针对该状态运行适用的整体与聚焦检查。应用[验证独立性](../layer-02-workflow-concepts/verification-independence_zh_cn.md)：同一 Session 的检查是逻辑验证，不能称为独立 Session。应用[验证报告](../layer-02-workflow-concepts/verification-reporting_zh_cn.md)：记录通过、失败、不可用和基于假设的检查、剩余风险、未解决项及其阻塞影响。应用[验证 epoch](../layer-02-workflow-concepts/verification-epoch_zh_cn.md)：分别跟踪实现/内容、文档和 Git 元数据；受影响维度不得复用旧证据。必需的独立性或证据不可用时，阻塞依赖的影响。
11. **仅在具体失败后修复。** 在 [Repair](../layer-02-workflow-concepts/repair_zh_cn.md)指出失败证据、受影响路径和最小候选修复。用[修复范围门禁](../layer-02-workflow-concepts/repair-scope-gate_zh_cn.md)先确认与 Contract/Decision 兼容，再授权执行；实质变化返回第 1 和第 6 阶段。在[修复执行](../layer-02-workflow-concepts/repair-execution_zh_cn.md)只应用授权的窄范围改动并运行聚焦检查。用[修复验证交接](../layer-02-workflow-concepts/repair-verification-handoff_zh_cn.md)记录新状态，依赖工作前重复第 10 阶段。没有失败时记录 Repair 不适用。
12. **文档。** 在 [Documentation](../layer-02-workflow-concepts/documentation_zh_cn.md)确认获准路径、读者、目的、源证据及适用的验证边界。只修改获准文档/注释；同步受维护的语言镜像。推进文档 epoch，执行适用的 Markdown、链接、空白、多语言和范围检查。若内容改变行为、Contract 或验收条件，返回实现/内容验证；否则保留有效的产品证据。记录未能运行的检查。
13. **Git 影响。** 在 [Git](../layer-02-workflow-concepts/git_zh_cn.md)确认准确仓库、worktree、分支/ref、远端、操作和授权。检查状态/历史，保留无关改动，确认暂存/提交内容与最新已验证的内容及文档指纹一致。索引/提交/分支/历史变化属于 Git 元数据变化；commit、push、Issue、PR 等影响分别确认授权。目标不明、冲突、权限缺失或内容未经验证时停止。没有 Git 工作时记录原因。
14. **验收。** 在 [Acceptance](../layer-02-workflow-concepts/acceptance_zh_cn.md)把每项 Contract 验收条件映射到最新实现/内容、文档和 Git 元数据 epoch 的当前证据。核对路径/影响是否在范围内；分别报告通过、失败、未运行、不可用、假设和用户授权项及剩余风险。只有必需事项和边界均已解决，才能报告 `COMPLETE`；说明本路线为 Single-Agent，并如实标注同一 Session 的检查。

## 验证限制

实质性修改的 Contract 或风险评估可能要求独立的 Change Verification Session。单代理模式不能创建或声称拥有独立 verifier Session，因此该路线无法提供独立验证。此时在当前 Session 中运行允许的最强检查，明确说明结果不是独立验证，并在必需边界未解决时不发布依赖该验证的外部 Git 影响。

对于保持行为不变的简单修改或仅文档修改，使用适用的快速路径，并执行：用 `rg` 检查修改文件引用的过期路径/名称；检查修改后的 Markdown 和本地链接目标；运行 `git diff --check`；运行 `python3 scripts/check-multilingual-docs.py`；手动确认每条修改后的规则仍与选定 Contract 和路线一致。记录每条命令或审查的结果及通过条件。

## 完成

执行根 Coding 完成门禁。最终报告必须说明这是单代理工作，区分临时检查和最终检查，说明不可用的独立验证，并把每个验收条件映射到当前证据。

## 相关概念

- [共享协议](../../share/shared-protocols_zh_cn.md)——定位共用 Session 约定。
- [Session 职责归属](../layer-01-fundamental-concepts/session-role-ownership_zh_cn.md)——定位各阶段职责。

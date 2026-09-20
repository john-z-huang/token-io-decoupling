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

## 已组合的检查点顺序

Coding 选择器已经将 Contract、Environment 和 Mode 检查点作为路线前门禁完成；本路线不得重复执行。遵循 Coding 工作流，并从[Context](../layer-02-workflow-concepts/context_zh_cn.md)开始组合[Decision](../layer-02-workflow-concepts/decision_zh_cn.md)、[Implementation](../layer-02-workflow-concepts/implementation_zh_cn.md)、[Control](../layer-02-workflow-concepts/control_zh_cn.md)、[Verification](../layer-02-workflow-concepts/verification_zh_cn.md)、[Verification independence](../layer-02-workflow-concepts/verification-independence_zh_cn.md)、[Verification reporting](../layer-02-workflow-concepts/verification-reporting_zh_cn.md)、[Verification epoch](../layer-02-workflow-concepts/verification-epoch_zh_cn.md)、[Repair](../layer-02-workflow-concepts/repair_zh_cn.md)、[Repair scope gate](../layer-02-workflow-concepts/repair-scope-gate_zh_cn.md)、[Repair execution](../layer-02-workflow-concepts/repair-execution_zh_cn.md)、[Repair verification handoff](../layer-02-workflow-concepts/repair-verification-handoff_zh_cn.md)、[Documentation](../layer-02-workflow-concepts/documentation_zh_cn.md)、[Git](../layer-02-workflow-concepts/git_zh_cn.md)和[Acceptance](../layer-02-workflow-concepts/acceptance_zh_cn.md)。单代理差异：仅在需要有界侦察或恢复时加载上下文；每个实质性方向前执行决策；每次只实现一个获批准切片并设置控制边界；针对当前最终状态指纹验证；只有具体失败时才修复，并针对新的 epoch 重新验证；然后在当前 Session 中进入文档、Git 和验收。

## 单 Session 执行规则

1. 在实质性工作前固定 `ACTIVE_CONSTRAINTS`（当前用户、运行环境、仓库、权限、安全和 Session 硬约束的简短清单）、Semantic Contract、验收条件和可能的 Decision Brief。简单快速路径的决策可以简短，但必须明确。
2. 项目事实不足时，将有界侦察作为逻辑阶段执行。事实和方向获批准前不要实现。
3. 每次只执行一个获批准的 Interaction Slice。只读取该切片需要的文件，只作获授权的修改，并运行用于指导修复的聚焦临时检查。
4. 每个实质性边界都记录状态、发现、修改范围、验证、问题、下一步和未发布边界。
5. 文档或依赖 Git 交付前，针对当前最终状态指纹或 epoch 执行最终检查。同一 Session 的检查不是独立验证。

## 验证限制

实质性修改的 Contract 或风险评估可能要求独立的 Change Verification Session。单代理模式不能创建或声称拥有独立 verifier Session，因此该路线无法提供独立验证。此时在当前 Session 中运行允许的最强检查，明确说明结果不是独立验证，并在必需边界未解决时不发布依赖该验证的外部 Git 影响。

对于保持行为不变的简单修改或仅文档修改，使用适用的快速路径，并执行：用 `rg` 检查修改文件引用的过期路径/名称；检查修改后的 Markdown 和本地链接目标；运行 `git diff --check`；运行 `python3 scripts/check-multilingual-docs.py`；手动确认每条修改后的规则仍与选定 Contract 和路线一致。记录每条命令或审查的结果及通过条件。

## 完成

执行根 Coding 完成门禁。最终报告必须说明这是单代理工作，区分临时检查和最终检查，说明不可用的独立验证，并把每个验收条件映射到当前证据。

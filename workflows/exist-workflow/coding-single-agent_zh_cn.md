# Coding 工作流——单代理模式

[English](coding-single-agent.md) | [简体中文](coding-single-agent_zh_cn.md)

先读取 [`../coding_zh_cn.md`](../coding_zh_cn.md)，再读取 `../../references/coding/agent-delegation-control_zh_cn.md` 获取权威委派状态。只有该文档记录单代理结果时，才使用此已组合工作流。

## 模式 Contract

- 所有工作保留在当前 Session 中。将 Input-side Reasoning、Primary Output、文档和适用检查视为逻辑阶段，而不是独立代理。
- 所有 Agent/Session 的创建、复用、例外和生命周期决策均遵循权威文档；本路线不重复这些规则。
- 保留下方检查点序列中的 Contract、上下文、决策、控制边界、验证边界、文档边界、Git 授权和完成检查。
- “不要创建子代理”或“不要使用浏览器”等任务级禁止事项在整个任务期间持续有效。

## 组合输入

本路线在执行检查点序列前组合独立的 Coding references：`shared-protocols`、`agent-delegation-control`、`session-model` 和 `execution-control`。policy 定义模式/委派规则；任务控制记录保存当前状态；其他 reference 提供共享原语、Session 语义和执行规划。下方检查点列表是完整的路线组合；检查点模块不会互相导入。

## 当前 Session 中的职责边界

- Input-side Reasoning 负责 Semantic Contract、实质性决策、授权、检查点结果和语义验收。
- Primary Output 负责获批准的实现和临时聚焦检查。
- Documentation/Comments & Git Operations 负责验证后的获批准文档或注释，以及明确发布下的非简单 Git 工作。
- 即使本路线只使用一个 Session，Contract 要求的独立 Change Verification 仍然有效；不得把同一 Session 的检查标记为独立验证。本路线无法提供独立 verifier。

## 本路线的运行环境要求

按照运行环境检查点产生的能力清单执行：

- 按权威文档要求，将各阶段保留在当前 Session 中。本路线不定义独立 Session 创建、Worker 返回路径或按角色绑定模型。
- 在本地 Codex 中，从 `~/.codex/AGENTS.md` 读取全局指令；同级的 `~/.codex/AGENTS.override.md` 优先，但仓库指令仍然负责仓库策略。修改这些指令、活动覆盖指令、Skill 或仓库指令后，必须启动新的 Codex 运行或 Session，再判断修改是否生效。
- 在 ChatGPT Work 中，只使用当前任务明确暴露的模型、推理控制、文件、连接器和执行工具。附件或连接器不代表拥有本地执行、仓库修改、凭据或跨线程控制能力。
- 在标准 ChatGPT 中，不要假设拥有 Shell、Python、Git、测试、沙箱、worktree、连接器或独立 Session。如果没有本地执行能力，不得声称已经运行测试、构建、Git 操作或文件系统校验。
- 如果当前切片需要的能力缺失或未知，停止该切片并报告；不得替换运行环境、模型、Session、工具、权限或认证路径。

## 已组合的检查点顺序

按以下顺序执行检查点；只有记录了原因的条件不适用检查点才能跳过：

1. [Contract](../checkpoint/contract_zh_cn.md)、[运行环境](../checkpoint/environment_zh_cn.md) 和 [执行模式](../checkpoint/mode_zh_cn.md)。
2. 只有需要有界侦察、可复用文件状态或恢复上下文时，才执行[上下文](../checkpoint/context_zh_cn.md)。
3. 每个实质性实现方向确定前执行[决策](../checkpoint/decision_zh_cn.md)。
4. 每次只对一个获批准切片执行[实现](../checkpoint/implementation_zh_cn.md)，在进入下一切片或发生实质性变化前执行[控制边界](../checkpoint/control_zh_cn.md)。
5. 针对当前最终状态指纹或 epoch 执行[验证](../checkpoint/verification_zh_cn.md)。
6. 只有出现具体失败时才执行[修复](../checkpoint/repair_zh_cn.md)，然后针对新状态重新验证。
7. 必需的验证决定完成后执行[文档](../checkpoint/documentation_zh_cn.md)。
8. 只有明确授权 Git 影响时才执行 [Git](../checkpoint/git_zh_cn.md)。
9. 报告完成前执行[验收](../checkpoint/acceptance_zh_cn.md)。

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

回到 [`../coding_zh_cn.md`](../coding_zh_cn.md) 执行根完成检查。最终报告必须说明这是单代理工作，区分临时检查和最终检查，说明不可用的独立验证，并把每个验收条件映射到当前证据。

# Coding 工作流——多代理模式

[English](coding-multi-agent.md) | [简体中文](coding-multi-agent_zh_cn.md)

先读取 [`../coding_zh_cn.md`](../coding_zh_cn.md)。只有用户明确要求多个代理，或 Input-side Agent 判断确有具体结构收益、强隔离或能力要求，且没有更高优先级限制禁止委派时，才使用此已组合工作流。

## 模式 Contract

- Worker 接收一个已发布的 Interaction Slice，只能通过父级控制的通道返回。Worker 不得创建递归执行层级，也不能把其他 Worker 的进度当作权限。
- 角色名称只描述职责。只有选定的运行环境和本模式条件证明存在具体结构收益或强隔离/能力要求时，才创建独立 Session。
- 如果用户禁止子代理、子任务、独立 Session 或并行委派，应停止本路线并使用单代理路线，不得模拟多代理行为。

## 职责边界

- 根父级负责 Semantic Contract、实质性决策、授权、检查点结果、Worker 生命周期和语义验收。
- Primary Output 负责获批准的实现和临时聚焦检查，不负责最终验收或非简单 Git 工作。
- Contract 要求时，Change Verification 负责最终变更结果验证。
- Documentation/Comments & Git Operations 负责验证后的获批准文档或注释，以及明确发布下的非简单 Git 工作。

## 本路线的运行环境要求

按照运行环境检查点产生的能力清单执行：

- 只有当前运行环境暴露了已发布切片所需的 Session、模型、参数、文件系统、工具、认证和父级控制返回能力时，才能继续本路线。
- Worker 必须只能向直接父级返回结果，不能创建或管理其他 Agent/Session，也不能联系任意线程。如果运行环境无法保证这些限制，不要派发 Worker。
- 在本地 Codex 中，从 `~/.codex/AGENTS.md` 读取全局指令；同级的 `~/.codex/AGENTS.override.md` 优先，但仓库指令仍然负责仓库策略。确实暴露独立 Session 创建和模型控制时，使用当前 Skill 的绑定：Primary Output 使用 `gpt-5.6-luna` 与 `reasoning_effort=xhigh`；Change Verification 使用 `gpt-5.6-luna` 与 `xhigh`；Documentation/Comments & Git Operations 使用 `gpt-5.6-luna` 与 `high`；Context Bootstrap/Refresh 使用 `gpt-5.6-luna` 与 `high`，只有确定性元数据、哈希或差异刷新可以使用 `medium`。
- 只有在重复失败或遇到阻塞时，才将 `reasoning_effort=max` 作为窄范围升级；随后回到正常档位。修改全局指令、活动覆盖指令、Skill 或仓库指令后，必须启动新的 Codex 运行或 Session，再判断修改是否生效。
- 在 ChatGPT Work 中，只使用当前任务明确暴露的模型身份、推理控制、独立 Session、连接器、文件和执行工具。这里没有固定模型绑定；连接器或附件也不代表拥有本地执行、仓库修改、凭据或跨线程控制能力。
- 在标准 ChatGPT 中，只有聊天明确暴露所需的独立 Session、委派路径、工具和验证能力时，才使用多代理 Coding。不要假设拥有 Shell、Python、Git、测试、沙箱、worktree、连接器或跨线程控制，也不得替换成其他运行环境或模型。
- 如果所需模型、参数、Session、返回路径、文件系统、工具、连接器或认证能力缺失或未知，应在该边界停止并报告阻塞能力。

## 已组合的检查点顺序

按以下顺序执行检查点；只有记录了原因的条件不适用检查点才能跳过：

1. [Contract](../checkpoint/contract_zh_cn.md)、[运行环境](../checkpoint/environment_zh_cn.md) 和 [执行模式](../checkpoint/mode_zh_cn.md)。
2. Worker 需要有界可复用状态或替换恢复时执行[上下文](../checkpoint/context_zh_cn.md)。
3. 发布实质性方向或派发前执行[决策](../checkpoint/decision_zh_cn.md)。
4. 每个已发布切片执行[实现](../checkpoint/implementation_zh_cn.md)，在实质性边界执行[控制边界](../checkpoint/control_zh_cn.md)。
5. 对实质性修改，在运行环境暴露该能力时，于新的独立 Change Verification Session 中执行[验证](../checkpoint/verification_zh_cn.md)。
6. 失败结果执行窄范围[修复](../checkpoint/repair_zh_cn.md)，然后针对新 epoch 重新验证。
7. 验证通过后执行[文档](../checkpoint/documentation_zh_cn.md)。
8. 只有明确授权影响时才执行 [Git](../checkpoint/git_zh_cn.md)。
9. 完成前执行[验收](../checkpoint/acceptance_zh_cn.md)。

## 上下文与派发

公共工作流已经建立共享协议、Session 规则、运行环境检查和执行控制规则。此外：

1. Worker 需要可复用状态、有界交接或替换恢复时，读取 [`../../references/coding/context-exchange_zh_cn.md`](../../references/coding/context-exchange_zh_cn.md)。
2. 派发启用 Worker 编写内容 memo 时，读取 [`../../references/coding/content-memo_zh_cn.md`](../../references/coding/content-memo_zh_cn.md)。
3. 只有满足复用条件时才使用 Context Bootstrap 或 Refresh。保持 capsule 只包含事实和路由信息；它不能替代 Contract、必需的源文档或独立验证。
4. 每个 Worker 使用独立的 context-exchange 子目录，并且只授予它所需的命名代码路径和上下文路径。

第一次实质性派发前，除非任务简单、局部、低风险、明显、可逆且可机械验证，否则先形成简洁的 Decision Brief。实质性事实不足时只发布有界侦察，随后在输入侧综合结果，再发布实现。

每个已发布任务包都说明：

```text
Owner: Primary Output | Documentation/Comments & Git Operations | Change Verification
Objective: ...
Authorized scope/mutations: ...
Return conditions: ...
Unreleased boundary: ...
```

不适用的段落写明 `Not applicable` 及原因，不要创建无操作 Worker。除非明确批准独立且不冲突的并行工作，否则一次只发布一个 Interaction Slice。在切片内使用 Progress Signals，在实质性边界使用控制边界检查点。

## 验证与修复

- 实质性修改达到实现检查点后，创建新的独立 Change Verification Session，提供最终状态指纹或 epoch 和验收条件，并要求整体及定向证据。
- 后续 Evidence-on-Demand 和修复后的 epoch 复用该验证者。每次最终状态指纹改变都必须重新独立评估；早期结论不能作为新状态的证据。
- 失败时只发布窄范围修复，并将新 epoch 发送给同一验证者。实质性问题未解决前，不开始验证后的文档或依赖验证的远程 Git 工作。
- 验证通过后，将文档/注释工作和 Git 工作作为独立的有界切片发布，并明确授权。

## 完成

回到 [`../coding_zh_cn.md`](../coding_zh_cn.md) 执行文档、Git 和最终验收。最终报告必须区分真实独立 Session 与同一 Session 的逻辑阶段，并把每个验收条件映射到当前证据。

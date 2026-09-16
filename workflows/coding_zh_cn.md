# Coding 工作流

[English](coding.md) | [简体中文](coding_zh_cn.md)

当仓库文本、开发工具输出、实现、测试、文档或 Git 状态是主要工作状态时，使用本工作流。本文件是 Coding 工作流的唯一索引，负责路线选择、运行环境检查点路由、检查点组合和最终完成检查。

## 入口要求

任务开始时：

1. 读取 [`../references/share/shared-protocols_zh_cn.md`](../references/share/shared-protocols_zh_cn.md)。
2. 在创建 Session 或判断运行环境前，读取 [`../references/coding/session-model_zh_cn.md`](../references/coding/session-model_zh_cn.md)。
3. 在实质性实现、调试、构建、测试或 Git 阶段发布前，读取 [`../references/coding/execution-control_zh_cn.md`](../references/coding/execution-control_zh_cn.md)。
4. 识别真实运行环境，并完成链接的运行环境检查点。
5. 只选择一条执行路线。如果任务符合已组合路线，读取该路线；否则组合下面列出的检查点。

## 运行环境

依赖运行环境的工作开始前，读取[运行环境检查点](checkpoint/environment_zh_cn.md)。该检查点只负责识别运行环境，以及记录当前界面实际暴露的能力。所选工作流再根据自己的要求解释这些能力；本索引不重复这两部分规则。

## 两个已组合好的工作流

当前在 `workflows/exist-workflow/` 下维护两个完整的 Coding 工作流：

- [单代理 Coding](exist-workflow/coding-single-agent_zh_cn.md)：用户禁止子代理、子任务、独立 Session 或并行委派时使用；没有具体结构收益需要拆分时也使用。
- [多代理 Coding](exist-workflow/coding-multi-agent_zh_cn.md)：只有用户明确要求多个代理，或 Input-side Agent 判断确有结构收益、强隔离或能力要求，且没有更高优先级限制禁止委派时使用。

读取本公共工作流后，如果任务符合其中一条路线，可以直接按照对应的完整文档执行。不要同时读取两条路线。如果后续事实使当前路线失效，应修改 Contract、停止当前切片，并明确选择另一条路线。

## 检查点索引

下面的独立检查点模块只在对应条件满足时读取。每个模块只定义一个动作边界，不负责路由到其他模块。

1. [Contract](checkpoint/contract_zh_cn.md) — 始终先固定目标、硬性约束、决策和验收条件。
2. [运行环境](checkpoint/environment_zh_cn.md) — 依赖环境的工作开始前确认真实运行环境和能力。
3. [执行模式](checkpoint/mode_zh_cn.md) — 在 Contract 和运行环境检查后只选择一条执行路线。
4. [上下文](checkpoint/context_zh_cn.md) — 需要有界侦察、可复用文件上下文或恢复上下文时使用。
5. [决策](checkpoint/decision_zh_cn.md) — 实质性实现前，或范围、架构、安全、兼容性因新事实改变时使用。
6. [实现](checkpoint/implementation_zh_cn.md) — 每个获批准的变更切片及其聚焦的临时检查使用。
7. [控制边界](checkpoint/control_zh_cn.md) — 到达实质性边界、准备发布下一切片或改变权限时使用。
8. [验证](checkpoint/verification_zh_cn.md) — 实现完成后，以及每次修复产生新的最终状态时使用。
9. [修复](checkpoint/repair_zh_cn.md) — 只在检查或验证失败后执行有界修复时使用。
10. [文档](checkpoint/documentation_zh_cn.md) — 验证决定完成后，写入获批准的文档或注释时使用。
11. [Git](checkpoint/git_zh_cn.md) — 只有用户或任务明确授权 Git 影响时使用。
12. [验收](checkpoint/acceptance_zh_cn.md) — 报告完成前始终把每个验收条件映射到当前证据。

## 如何组合检查点

当任务不符合已组合好的工作流时，按以下顺序组合检查点：

1. 始终执行 Contract、运行环境和执行模式检查点。
2. 只有需要超出当前有界切片的侦察、可复用文件状态或替换 Session 后恢复时，才执行上下文检查点。
3. 实质性实现前执行决策检查点。任务简单、局部、低风险、可逆且可机械验证时，决策内容可以简短，但仍需明确。
4. 每次只执行一个获批准的实现切片。在切片之间，以及权限或范围发生实质变化前，执行控制边界检查点。
5. 实现达到最终状态后执行验证。如果验证失败，对窄范围修复执行修复检查点，然后针对新的最终状态 epoch 重新验证。
6. 只有验证决定完成后才执行文档检查点；只有明确授权了准确的仓库、worktree、ref、远程和影响时才执行 Git 检查点。
7. 始终以验收检查点结束。所需能力、验证边界、授权或验收项目未解决时，不得报告 `COMPLETE`。

检查点不适用时，必须在该检查点记录原因，不能静默跳过。新事实改变实质性决策时，继续前先回到 Contract 和决策检查点。当前父级 Agent 负责发布决定和语义验收；所选路线决定这是逻辑阶段还是父级 Session。

## Reference 组合

Reference 模块彼此独立，不负责路由到其他模块。本工作流按如下方式组合它们：

- [`../references/share/shared-protocols_zh_cn.md`](../references/share/shared-protocols_zh_cn.md) — Semantic Contract 基线、父级权限、Worker 返回路径、Dispatch Preview、进度、按需取证和缓存感知的上下文组织。每个 Coding 任务都读取。
- [`../references/coding/session-model_zh_cn.md`](../references/coding/session-model_zh_cn.md) — Coding 职责、Session 拓扑、角色独立性、Context Firewall 和 Session 亲和性。在选择或改变 Session 模式前读取。
- [`../references/coding/execution-control_zh_cn.md`](../references/coding/execution-control_zh_cn.md) — 两级规划、Interaction Slice、发布检查点、验证边界、文档边界、Git 门禁和 Input-side 输出纪律。在实质性执行前读取。
- [`../references/coding/context-exchange_zh_cn.md`](../references/coding/context-exchange_zh_cn.md) — 文件上下文布局、所有权、传输、新鲜度、bootstrap 和替换交接。只有所选路线需要时读取。
- [`../references/coding/content-memo_zh_cn.md`](../references/coding/content-memo_zh_cn.md) — Worker memo 的语言、写入设置、内容边界和刷新行为。只有多代理路线启用 Worker 编写 memo 时读取。

可复用语义必须放在所属 reference 中；路线选择和跨模块读取顺序放在本文件或已组合好的工作流中。不要在 reference 模块之间添加交叉引用。

## 完成检查

只有验收检查点通过后才能返回 `COMPLETE`。最终报告必须区分已检查/通过与未运行/不可用，区分已授权影响与可能影响，区分观察到的事实与假设或运行环境/模型能力声明。除非明确授权，不得 commit、push、创建 Issue/PR、修改远程配置或产生其他外部影响。

# Decisions 建议

[English](decisions-advisory.md) | [简体中文](decisions-advisory_zh_cn.md)

本模块负责五个固定注册节点的有界语义建议如何可选地参与判断。它不拥有这些节点的政策，不选择或确认 Core 分支，不授权工作、不释放 Slice、不决定验证结果或任务验收。

## 通用规范

### 保持建议与判断和授权分离

支持的节点仅为 `task_intent`、`output_class`、`contract_change`、`verification_impact` 和 `control`，并且只使用各节点当前注册的合法选项和必需事实结构。响应必须恰好包含一个答案，节点名和类型须与请求匹配，值须属于该节点当前合法选项；否则丢弃结果并直接判断。不得根据 confidence 分数推断正确性，也不得发明 confidence 阈值。映射的 owner 始终是权威。建议只是 Agent 可以考虑的独立输入；Agent 必须核对直接 owner、验证硬约束并作出实际判断。不得用 API 答案替换 Core 分支，也不得用建议授权模式、数量、名额、创建、派发、Slice 放行、Control 转换、验证成功或验收。

只有在调用方独立核实允许向外部分享数据后，才能请求建议。仅发送所选问题所需的有界事实和当前 owner 上下文。调用方提供的身份、权限、来源、修订或批准声明均不是证明。模式与数量保持锁定；建议不能重新打开它们。

只发送所选节点要求的类型化事实、必要的当前 owner 标题，以及表达其固定选项问题所需的最少指令。不得发送整个仓库、Session transcript、原始日志、凭据或无关状态。规则上下文 owner 负责来源、语言、标题范围和当前 Hash。如果必要 owner 正文无法在受支持的请求预算内完整包含，应回到直接文档判断；不得静默截断后声称内容完整。

每个请求绑定到调用方提供的当前事实、所选节点、输入 Hash 和当前规则 Hash。服务不保留跨调用状态，也不建立调用方身份、权限、来源、顺序或验收。响应后，将回显指纹和 Hash 与当前输入及 owner 对照。输入或相关 owner 正文发生变化时，丢弃过期建议。建议不是 Core 结果，也不得作为语义判断缓存。

Control 节点的建议可以指出 `continue`、`amend`、`stop` 或 `evidence-on-demand`，但只有调用方单独作出的获授权决定才有实际效果。Evidence-on-Demand 返回直接证据/Context 审阅，再回到 Control；它不会释放 Slice。Verification-impact 建议只能提示覆盖维度，不能宣告检查通过，也不能免除变化 epoch 的重新验证。必需 owner 缺失或硬约束失败时，即使建议有利也必须阻塞。

建议关闭、未请求、不可用、拒绝、无效、超时或过期时，返回当前直接 owner 并据此作出判断。此回退不放松硬门禁。仅返回安全状态和许可的失败类别；不得暴露原始异常、请求详情、凭据或响应正文。

### 保持 API 选择加入且配置按调用读取

建议功能默认关闭。启用必须来自可信运行时配置并具有明确的出站数据授权；普通请求参数本身不能启用功能。普通/默认语义建议测试使用 Mock 且不发送网络请求。明确选择加入的真实测试仍须取得出站数据授权，并遵守适用运行时章节规定的同一调用时本地配置前置条件。任何真实请求路径都必须在实际调用时读取本地配置的凭据和端点值，并要求两者均存在且非空白；任一缺失或空白时，不得创建 client 或发送请求。供应商专属名称和 SDK 处理仅写在适用的运行时章节。不得打印或持久化配置值；合成值仅用于离线 Mock。

## Codex CLI / ChatGPT Desktop 特别优化指令

当前 Session 通过获准嵌入端使用受支持 advisor 时，只针对已注册决策问题，并在调用方审阅有界事实和直接 owner 后使用。除非可信配置明确启用且具有出站数据授权，否则保持关闭。每次真实调用时读取本地 `OPENAI_API_KEY` 和 `OPENAI_BASE_URL`；将两者显式传给 SDK，不使用默认值或调用方替代。任一值缺失或空白时，不得创建 SDK client。语义建议 Mock 测试保持离线。建议响应不证明桌面身份、权限或检查点完成。

## Claude Code CLI / Claude Desktop 特别优化指令

目前没有适用于 Claude 的厂商专属建议优化。遵循通用规范，并且只使用当前 Session 实际暴露且获准的能力。

## 相关概念

- [Workflow Routing Advice](workflow-routing-advice_zh_cn.md) — 拥有五个固定语义建议节点之外的任务级阶段建议。
- [工作流规则上下文](../workflow-navigation/rule-context_zh_cn.md) — 当前注册 owner 标题及来源/Hash 边界。
- [Session 角色归属](../session-runtime/session-role-ownership_zh_cn.md) — 角色责任边界。
- [Coding Execution Decision Gate](execution-decision-gate_zh_cn.md) — 决策和放行责任。
- [Coding Execution Control](../execution-control/execution-control_zh_cn.md) — Slice 和 Control 转换授权。
- [Coding Delegation State Record](../delegation/delegation-state-record_zh_cn.md) — 当前 Root 状态和 Epoch 基础。

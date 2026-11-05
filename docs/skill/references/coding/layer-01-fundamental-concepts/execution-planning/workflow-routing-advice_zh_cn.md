# 工作流路由建议

[English](workflow-routing-advice.md) | [简体中文](workflow-routing-advice_zh_cn.md)

本文档定义在已获授权的 Coding 路线内定位当前检查点的可选任务级建议。它不拥有路线政策、就绪判断、模式选择、权限或执行权。

## 通用规范

### 建议与判断和授权分离

仅根据已审阅的任务事实和已锁定路线，建议当前阶段或模块。Coding 工作流和选定路线仍是阶段顺序、检查点动作、证据、分支及验收的权威来源。建议不会通过检查点、改变已锁定模式或子代理数量、授予权限、创建或派发 Agent，也不会调用其他工具。

当当前路线和规则可用时，可在本地映射显式阶段。自动阶段选择是可选的；只有在必要来源事实、当前规则上下文、能力和出站数据授权均可用时，才可使用语义判断。若事实或规则缺失、过期、超出预算或相互矛盾，应回到当前路线 owner 直接判断。不得把缺失证据转成假定阶段。

行动前应根据当前路线和任务状态复核建议阶段。哈希仅用于检测内容变化，不认证来源或证明权限。相关事实、路线或规则变化后，应刷新建议。可选建议能力不可用时，应记录该结果。仅当任务适用一条独立获授权的 Native/直接路径时才可继续；若选定路径所需能力缺失，应在其 owner 定义的边界停止，不得静默回退。

### 路线边界

阶段与模块的对应关系由当前 Single-Agent 或 Multi-Agent 路线拥有。只有模式和数量已锁定后，建议才可指出匹配模块。Multi-Agent 执行提醒不能替代角色、任务授权、memo、Slice 和子代理生命周期 owner。验证、修复、文档、Git 与验收仍由各自直接 owner 管理。

## Codex CLI / ChatGPT Desktop 特别优化指令

当当前会话实际暴露并授权该能力时，`decide_decoupling_workflow` 接收 `payload.request` 下的有界请求。Schema 要求 `mode_locked: true` 和规范的 `mode_count`，以及其他全部必填字段和有界调用方证据；`stage` 为 `auto` 或受支持的显式阶段。`source_facts_hash` 必须与所提供事实匹配。应填写完整的当前 Schema，包括任务标识和摘要、语言、能力及约束记录、来源事实引用，以及适用时的出站数据声明；本节摘要不是完整 payload 字段清单。完成相关有界规则检查后，显式阶段在本地解析。只有存在来源事实、允许出站数据且配置能力允许时，`auto` 才可发出一次 Decisions 请求。工具会重新加载相关上下文并复核哈希，再返回简要建议。

只有 `available` 是建议；`insufficient_evidence`、`blocked` 和 `stale` 需要直接审查，或刷新事实和规则。返回哈希不覆盖完整 Layer-04 路线，也不能证明路线未变；行动前须直接读取当前选定路线。结果不会重复输出完整规则。调用无状态，不执行工作流动作。API 错误经过限界处理，不暴露凭据或原始服务错误。运行时、模型和推理力度绑定见 [Runtime and Model Provider Support](../session-runtime/runtime-provider-support_zh_cn.md)。

## Claude Code CLI / Claude Desktop 特别优化指令

本项目 MCP Server 仅支持本地 Codex CLI。Claude 通用 MCP 能力不代表该 Server 支持直接连接；本 owner 目前没有 Claude 专用直接工具优化。应依据当前会话实际暴露并授权的能力遵循通用规范；否则将可选建议标记为不可用，并直接使用权威路线。

## 相关概念

- [Coding Execution Decision Gate](execution-decision-gate_zh_cn.md) — 拥有执行决策前置条件。
- [Task Assignment](task-assignment_zh_cn.md) — 拥有执行者选择。
- [Workflow Rule Context](../workflow-navigation/rule-context_zh_cn.md) — 拥有有界规则读取和完整性。

# Decoupling 工作流路由工具

[English](WORKFLOW_ROUTING.md) | [简体中文](WORKFLOW_ROUTING_zh_cn.md)

本文档负责 MCP 工作流工具 `decide_decoupling_workflow` 的公开契约：有界请求、路由行为、结果解释、哈希和失败边界。该工具只提供导航建议；链接的工作流文档及能力/权限门禁仍具权威性。

## 目的与路由选择

调用时使用 `payload.request`。请求包含已锁定的 Coding 模式与数量、一个当前工作流阶段或 `auto`，以及调用方提供的能力、约束和证据事实。工具不会判断检查点是否通过，不会更改模式或数量，不会授予权限、创建代理、派发任务或调用其他工具。

显式阶段会在加载并检查相关当前规则上下文后，于本地选择对应路由；不发起 API 请求，也不需要外发许可。`auto` 可以请求一次有界 Decisions 选项，但前提是提供了来源事实、请求允许外发数据，并且 Decisions 已启用且服务器配置允许外发数据。请求中的许可断言本身不能证明调用方有权披露数据。

## 请求契约

外层信封为 `{ "payload": { "request": { ... } } }`。严格请求字段如下：

| 字段 | 契约 |
| --- | --- |
| `task_id` | 必填，非空白，1–160 个字符。 |
| `task_summary` | 必填非空白文本，最多 1,200 个字符。 |
| `stage` | 必填：`auto`、`entry_readiness`、`session_readiness`、`work_definition`、`execution`、`verification_repair`、`documentation` 或 `delivery_acceptance`。 |
| `language` | `en` 或 `zh_cn`；默认 `en`。 |
| `mode_locked` | 必填严格布尔值。必须为 `true` 才能获得路由结果。 |
| `mode_count` | Core 的规范 `ModeCount` 对象：`mode` 为 `Single-Agent Coding` 或 `Multi-Agent Coding`；`child_count` 是非负整数，Single-Agent 必须恰为 `0`，Multi-Agent 至少为 `1`。 |
| `capabilities` | 最多 7 条且 ID 唯一，每条包含 `capability_id`、`status` 和 `source_ref`。ID 为 `rule_context`、`implementation`、`verification`、`documentation`、`git`、`child_creation` 和 `dispatch`；状态为 `available`、`unavailable` 或 `unknown`。 |
| `hard_constraints` | 最多 8 条且 ID 唯一，每条包含 `constraint_id`、`source_ref` 和 `statement`。 |
| `source_facts` | 最多 8 条且 ID 唯一，每条包含 `fact_id`、`source_ref` 和 `statement`。每条事实是带来源指针的有界文本；指针由调用方提供，不构成来源认证。 |
| `source_facts_hash` | 必填 64 位小写十六进制 SHA-256，须与规范化的 `source_facts` 列表一致。 |
| `outbound_data_permitted` | 必填严格布尔值。`auto` 发起 API 请求时必须为 `true`。 |

事实和约束 ID 为 1–96 个字符，必须以 ASCII 字母或数字开头，其余字符可为字母、数字、`.`、`_`、`:` 或 `-`。来源引用为 1–256 个字符。statement 必须非空白且最多 1,200 个字符。完整规范请求最多 32,000 个 UTF-8 JSON 字节；超限会被拒绝，不会截断。

路由映射遵循当前工作流 owner 定义的七个模块：

| 阶段 | Single-Agent | Multi-Agent |
| --- | --- | --- |
| `entry_readiness` | SM01 | MM01 |
| `session_readiness` | SM02 | MM02 |
| `work_definition` | SM03 | MM03 |
| `execution` | SM04 | MM04 |
| `verification_repair` | SM05 | MM05 |
| `documentation` | SM06 | MM06 |
| `delivery_acceptance` | SM07 | MM07 |

原生路由引用指向匹配语言和模式的路由。Multi-Agent 执行阶段可能包含职责与权限门禁、任务授权与 memo 条件、以及子代理生命周期前先放行 Slice 的条件提醒。验证、文档和交付阶段可能返回适用的条件检查，包括仅在验证发现问题后修复、变更 epoch 后重新验证，以及仅在既有授权下执行 Git。这些提醒不能替代路由 owner，也不授权任何操作。

## 哈希与规则上下文

`source_facts_hash` 对输入顺序的事实 `model_dump(mode="json")` 列表进行 UTF-8 规范 JSON 与 SHA-256 运算；规范 JSON 使用 `ensure_ascii=false`、对象键排序和紧凑分隔符。`input_hash` 使用相同的规范 JSON 与 SHA-256，对完整规范化请求计算，但只排除 `source_facts_hash`。这些哈希只检测内容变化；不认证来源、不证明事实，也不建立权限。

显式阶段会加载该阶段的有界规则包，检查完整性与预算，再次加载并比较哈希后才返回建议。`auto` 首先加载 task intent、mode 和 decision 规则的选择上下文；Decisions 请求包含有界调用方事实和当前规则片段。请求后会重新加载并检查上下文，再加载和检查所选阶段的上下文。规则文本总量和 Decisions 输入分别限制为 42,000 个字符。响应返回规则与索引哈希、精简规则证据及缺失事实引用，不重复完整规则文本。上下文过期或不可用时，须刷新后再使用。

## 结果与复核

每个结果都包含 `advisory_only: true`、`status`、`reason`、`source_facts_hash` 和 `input_hash`。模式已锁定时还会提供 `native_route` 引用。选定阶段可能包含 `module_id` 和 `conditional_checks`。结果还可能包括 `rule_hash`、`index_sha256`、`rule_evidence`、`missing_facts` 和 `capability_evidence`；API 结果也可能附带 `failure_class`、`provider_error_code`、`recovery`、固定模型 ID 与 token 使用量。证据是精简引用和哈希，不能替代阅读当前路由 owner。

| 状态 | 含义 |
| --- | --- |
| `available` | 已提供阶段或模块建议；这不是就绪结果，也不授予权限。 |
| `insufficient_evidence` | 当前事实或必需规则上下文不足以支持安全建议。复核列出的缺失事实。 |
| `blocked` | 前置条件、配置、请求或服务方检查失败；不得视为已给出建议。 |
| `stale` | 操作期间规则上下文发生变化；刷新当前规则并重新计算后再使用结果。 |

`reason` 的具体值为 `explicit_stage_advice`、`stage_selected`、`mode_not_locked`、`source_facts_missing`、`outbound_data_not_permitted`、`decisions_disabled`、`rules_unavailable`、`rule_context_incomplete`、`rule_context_budget_exceeded`、`request_exceeds_supported_bound`、`missing_credentials`、`provider_error`、`timeout`、`refusal`、`invalid_response`、`incomplete_response`、`unsupported_model`、`insufficient_evidence` 和 `stale_rule_context`。服务方错误会归类为有界错误码；结果不暴露原始服务方错误或凭据值。采取操作前，应根据当前证据重新核验哈希、能力、路由、事实和权限，并继续遵循现有路由及检查点 owner。

## API 与副作用边界

只有 `auto` 能发起 Decisions 请求。请求前，服务器从进程环境读取非空白的 `OPENAI_API_KEY` 和 `OPENAI_BASE_URL`，并将二者显式传给客户端。固定使用 `gpt-6-luna`，关闭自动重试。拒绝、不完整或无效的选项、返回模型错误、缺少配置、服务方失败、缺少外发许可、Decisions 配置禁用、规则不完整或规则哈希变化，都不能产生 `available` 建议。不使用 API 后备路径或模型替换。

该工具无状态：不写入工作流状态，不执行 Git、文件、代理创建或派发操作。工具发现不能证明身份或授予权限。原生路由仍负责阶段顺序、检查点操作、分支条件、证据和验收。

## 相关概念

- [MCP workspace 开发指南](DEVELOPMENT_zh_cn.md) — 负责 workspace 工具与安装。
- [MCP 可执行程序与注册指南](TOOLS_REGISTRATION_zh_cn.md) — 负责当前可执行程序清单和 Codex 注册。
- [Single-Agent Coding 工作流](../docs/skill/references/coding/layer-04-workflows/coding-single-agent_zh_cn.md) — 负责 Single-Agent 路由。
- [Multi-Agent Coding 工作流](../docs/skill/references/coding/layer-04-workflows/coding-multi-agent_zh_cn.md) — 负责 Multi-Agent 路由。
- [任务执行主体分配](../docs/skill/references/coding/layer-01-fundamental-concepts/execution-planning/task-assignment_zh_cn.md) — 负责执行主体决策。

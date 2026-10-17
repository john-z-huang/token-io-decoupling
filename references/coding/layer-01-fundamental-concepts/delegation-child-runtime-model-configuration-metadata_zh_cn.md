# Coding 子代理运行时模型配置元数据

[English](delegation-child-runtime-model-configuration-metadata.md) | [简体中文](delegation-child-runtime-model-configuration-metadata_zh_cn.md)

本文档负责每个子代理的运行时模型配置元数据记录及其 Serena 项目 Memory 生命周期。记录仅包含运行环境分支、请求与生效的模型/推理参数、核验证据和记录状态。不负责任务状态、项目发现、权限、授权、子代理创建、派发格式或生命周期决策。

## 通用规范

### 目的、时点与归属

模型和 reasoning-effort 绑定核验仅允许作为创建子代理的一部分。父级必须在子代理创建操作中选择并设置该职责要求的模型与 effort，并应用受支持的运行时绑定。若创建操作无法设置或确认这些必需参数，则阻止创建。若创建操作已接受必需参数，但没有提供额外的运行时解析观察，可将该可选观察记录为未解决，任务工作仍可继续。子代理在启动或之后的任何时候都不得检查、读取或报告自己的模型或 effort。

子代理创建后，任何逐代理元数据记录均由父级持有，只作为信息性审计资料。记录可说明创建时的输入和当时可用证据，但不得作为启动、任务工作、派发、follow-up、修复、compaction、唤醒或恢复的门禁。父级在该子代理的后续操作中不得重新核验或要求确认模型/effort。元数据不授予任务范围、权限、授权或生命周期状态。

### 可选元数据记录

若父级在创建子代理时维护此记录，可使用稳定的运行和 allocation 标识将其保存于 Serena 项目 Memory：

~~~text
memory_name: agent-session-context/<run-id>/<allocation-id>
reference: mem:agent-session-context/<run-id>/<allocation-id>
~~~

记录由父级持有并负责所有写入。Memory 是可选审计存储，不是创建子代理或放行工作的前提。不得把 Memory 引用放入子代理提示，也不得要求子代理读取。若记录存在，父级可读回确认保存；元数据缺失或不可用绝不阻塞子代理。

~~~yaml
record_type: child-runtime-model-configuration
schema_version: 1
run_id: <委派运行标识>
allocation_id: <父级 allocation 标识>
runtime_branch: <创建时使用的受支持分支>
requested_model: <准确模型标识或受支持别名>
requested_reasoning_control: <参数名=值 或 not_supported>
effective_model: <解析值或 unresolved>
effective_reasoning_control: <解析值、not_supported 或 unresolved>
binding_evidence: <父级控制的创建配置或运行时证据；不得含秘密>
recorded_at: <时间戳>
record_status: informational | unavailable
~~~

模型和参数支持范围由[运行环境与模型厂商支持](runtime-provider-support_zh_cn.md)决定。不得根据职责名称或其他 allocation 推断设置。必需模型与 effort 必须由创建操作设置或确认；未解决元数据不能替代此要求。若创建操作已接受必需参数，但没有提供额外的运行时解析观察，可将该观察作为信息性元数据保留为 `unresolved` 并继续任务。这不授权之后要求子代理核验，也不阻塞工作。按适用的用户授权和数据保留规则处理审计记录。

## Codex CLI / ChatGPT Desktop 特别优化指令

对于 Local Codex，父级必须在创建操作中设置职责要求的模型与 effort，并应用显式 spawn 值及适用的 profile/运行时优先级。无法设置或确认必需参数时阻止创建。若操作已接受必需参数、但没有额外运行时解析观察，该观察可保持未解决。记录父级可访问的创建证据。不得要求子代理检查 `/agent`、`/status`、Memory 或其他来源并报告模型或 `model_reasoning_effort`。Serena Memory Hook 和压缩上下文不改变此边界。[OpenAI：子代理](https://learn.chatgpt.com/docs/agent-configuration/subagents)、[OpenAI：Hooks](https://learn.chatgpt.com/docs/hooks)、[Serena Memory 工具](LSP-MCP-Tools_zh_cn.md)。

## Claude Code CLI / Claude Desktop 特别优化指令

对于 Local Claude Code，父级必须通过创建操作设置职责要求的模型与 effort，并应用 `Agent` 调用参数、自定义子代理 frontmatter、环境覆盖和适用 Hook。无法设置或确认必需参数时阻止创建。若操作已接受必需参数、但没有额外运行时解析观察，该观察可保持未解决。只记录父级可访问的创建证据。不得要求子代理检查 `/tasks`、Session 字段、Memory 或其他来源并报告模型或 effort。后续 resume 或 `SessionStart` 事件不是重新核验这些设置的理由。[Anthropic：Hooks](https://code.claude.com/docs/en/hooks)、[Anthropic：子代理](https://code.claude.com/docs/en/sub-agents)、[Serena Memory 工具](LSP-MCP-Tools_zh_cn.md)。

## 相关概念

- [Coding Delegation State Record](delegation-state-record_zh_cn.md)——定位父级运行/allocation 标识和任务控制记录。
- [Coding Child Creation](delegation-child-creation_zh_cn.md)——定位创建时必需的模型/effort 设置；审计元数据为可选。
- [Coding Child Dispatch](delegation-child-dispatch_zh_cn.md)——定位派发边界：派发不读取或核验此元数据。
- [Coding Child Reuse and Replacement](delegation-child-reuse-replacement_zh_cn.md)——定位 follow-up 与恢复边界。
- [Coding Child Lifecycle](delegation-child-lifecycle_zh_cn.md)——定位子代理身份和生命周期状态。
- [Coding Session Model](session-model_zh_cn.md)——定位 Session 语义。
- [Runtime and Model Provider Support](runtime-provider-support_zh_cn.md)——定位运行时绑定和配置核验。
- [Serena LSP and MCP Tools](LSP-MCP-Tools_zh_cn.md)——定位 Serena Memory 工具能力和语义。

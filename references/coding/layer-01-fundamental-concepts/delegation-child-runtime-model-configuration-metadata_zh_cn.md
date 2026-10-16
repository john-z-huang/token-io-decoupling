# Coding 子代理运行时模型配置元数据

[English](delegation-child-runtime-model-configuration-metadata.md) | [简体中文](delegation-child-runtime-model-configuration-metadata_zh_cn.md)

本文档负责每个子代理的运行时模型配置元数据记录及其 Serena 项目 Memory 生命周期。记录仅包含运行环境分支、请求与生效的模型/推理参数、核验证据和记录状态。不负责任务状态、项目发现、权限、授权、子代理创建、派发格式或生命周期决策。

## 通用规范

### 目的与边界

为每个已分配的 Multi-Agent 子代理持久化一份模型配置元数据记录，使子代理在 compaction、中断或恢复后可以重新读取模型和推理参数，不依赖压缩后的对话历史。

元数据须与父级任务控制记录、任务提示词、内容 memo、交接记录和项目知识分开。不得保存任务目标、Contract、来源发现、进展、diff、权限授予、秘密或 transcript。父级任务控制记录仍是 mode、数量、allocation、Interaction Slice、范围、修改和生命周期的权威来源。元数据记录不授予这些权限。

### Memory 名称、归属与结构

父级为一次委派运行分配唯一的 `run_id`，并为每个预留子代理名额分配稳定的 `allocation_id`。使用以下准确的 Serena 项目 Memory 名称和引用：

~~~text
memory_name: agent-session-context/<run-id>/<allocation-id>
reference: mem:agent-session-context/<run-id>/<allocation-id>
~~~

这是具名的 Serena Memory，不是 workspace 中的 Markdown 文档。记录由父级持有并负责所有写入。创建子代理前，核实父级已暴露所需的 Serena Memory 工具，且子代理配置预期能访问同一项目 Memory 作用域。启动后，子代理必须读取准确的 Memory，以证明其可访问。Memory 不会自动跨 Session 共享。若启动前无法确定子代理的访问能力，只允许发送配置核验提示，并在子代理读取成功前阻塞任务工作。任一 Session 缺少所需读写工具时，阻塞依赖的子代理工作；不得回退到文件系统或其他 Memory。

为新 allocation 使用 Serena `list_memories` 检查名称；若 Memory 已存在，先读取并确认其 `run_id` 和 `allocation_id` 与本 allocation 完全一致后才能更新。不得覆盖冲突记录。通过 Serena `write_memory` 写入初始记录，`memory_name` 使用 `"agent-session-context/<run-id>/<allocation-id>"`，不包含 `mem:` 前缀。写入后立即用相同的 `memory_name` 调用 Serena `read_memory`，核实已保存的内容。父级任务控制记录只保存 `mem:` 引用，不复制元数据内容。

使用以下最小内容：

~~~yaml
record_type: child-runtime-model-configuration
schema_version: 1
run_id: <唯一的委派运行标识>
allocation_id: <父级稳定分配标识>
runtime_branch: <已核实的受支持分支>
requested_model: <准确模型标识或受支持别名>
requested_reasoning_control: <参数名=值 或 not_supported>
effective_model: <已核实的模型标识或受支持别名；否则为 unresolved>
effective_reasoning_control: <参数名=值、not_supported 或 unresolved>
binding_evidence: <配置来源或运行时观察；不得含秘密>
verified_at: <时间戳或 unresolved>
record_status: prepared | verified | blocked
~~~

模型和参数的支持范围由[运行环境与模型厂商支持](runtime-provider-support_zh_cn.md)决定。不得根据父级模型、职责名称、记忆中的上下文或其他 allocation 推断。只有解析所有适用的优先级和覆盖项，或通过实时运行时证据确认生效配置后，才能将记录标为 `verified`。若启动配置无法确定子代理的生效值，则保留 unresolved，直到子代理返回运行时观察；父级使用 Serena `write_memory` 更新 Memory，再使用 Serena `read_memory` 读回核实，然后才能放行任务工作。

### 启动、压缩与重新进入

在子代理的初始提示和每条 follow-up 中都包含准确的 `mem:agent-session-context/<run-id>/<allocation-id>` 引用。仅用于配置核验的启动提示可以要求子代理读取 Memory 并报告其可观察到的模型配置；记录尚未解决时不得放行任务工作。执行依赖模型配置门禁的工作前，子代理须用 Serena `read_memory` 读取不带 `mem:` 前缀的 Memory 名称，确认 `run_id`、`allocation_id` 和 `record_status: verified`。compaction、中断或恢复后，使用 Memory 中已核验的值；不得仅因压缩后的历史不再包含这些值就报告 `unknown`。只有记录属于其他 allocation，或有证据表明生效运行时绑定发生变化时，才报告冲突。子代理向父级报告冲突，不得写入或修复该记录。

compaction、中断、恢复或向同一子代理发送 follow-up 后，父级从任务控制记录读取引用，并在实际消息中再次提供。子代理继续任务或陈述配置前，须再次调用 Serena `read_memory`，并使用其中已核验的值，不得从压缩后的对话历史推断。先前加载的摘要或注入的 hook 上下文都不能证明本次已读取 Memory。

Memory 缺失、不可访问、尚未解决或与实时运行时证据冲突时，停止依赖工作。父级只有重新核实当前绑定后，才能更新同一 allocation 的 Memory；更新后必须读回并核实内容。只要 allocation 仍可能恢复或接收 follow-up，就保留该记录。没有用户明确授权时不得删除。

## Codex CLI / ChatGPT Desktop 特别优化指令

对于 Local Codex，记录子代理请求的准确 `model` 与 `model_reasoning_effort` 及其解析后的生效值。Codex 先解析显式 spawn 值，再解析 `[agents]` 默认值，最后使用父级值；匹配的自定义 Agent 文件中的 `model` 或 `model_reasoning_effort` 会覆盖该解析结果。若显式选择模型但没有指定 effort，应记录已核实的该模型默认 effort，不得假设沿用父级值。仅使用[运行环境与模型厂商支持](runtime-provider-support_zh_cn.md)允许的绑定。

仅使用父级和子代理当前 Session 实际暴露且获准调用的 Serena Memory 工具。Codex 子代理 Session 不会自动共享 Serena Memory；放行工作前须确认子代理可以读取同一项目的 Memory。已配置的 `SubagentStart` hook 可以通过 `hookSpecificOutput.additionalContext` 注入 `mem:` 引用，但该事件没有文档化的 reasoning-effort 字段，且 `continue: false` 不会阻止子代理创建。匹配 `source: "compact"` 的 `SessionStart` hook 可在压缩后向该 Session 的下一条请求添加上下文；它是可选能力，不能替代 `read_memory`，也不能证明子代理已读取记录。[OpenAI：子代理](https://learn.chatgpt.com/docs/agent-configuration/subagents)、[OpenAI：Hooks](https://learn.chatgpt.com/docs/hooks)、[Serena Memory 工具](LSP-MCP-Tools_zh_cn.md)。

## Claude Code CLI / Claude Desktop 特别优化指令

对于 Local Claude Code，记录准确的 `Agent` 调用 `model` 和 `effort` 参数，或自定义子代理 frontmatter 中的对应值，再解析最终绑定。调用的 model 通常优先于 frontmatter `model`、`CLAUDE_CODE_SUBAGENT_MODEL` 和父级模型，但已安装的 `agent.spawn` hook 可以替换调用值；别名可能解析到其他模型，或在受限时回退。frontmatter `effort` 会被调用的 `effort` 参数覆盖，而 `CLAUDE_CODE_EFFORT_LEVEL` 优先于两者。调用级 `effort` 参数要求 Claude Code v2.1.292 或更新版本。宿主支持时使用 `/tasks` 核验运行中子代理的模型与 effort（显示功能要求 v2.1.242 或更新版本）。仅使用[运行环境与模型厂商支持](runtime-provider-support_zh_cn.md)允许的绑定。

在父级与子代理 Session 中分别发现并核实 Serena Memory 工具；Claude Code 不会自动向其他 Session 共享项目 Serena Memory。放行任务工作前，要求子代理使用实际暴露的 Serena `read_memory` 工具读取此准确 Memory。已配置的 `SubagentStart` hook 可以通过 `hookSpecificOutput.additionalContext` 注入 `mem:` 引用；自动压缩移除之前的注入后，也可在后续调用时再次注入。但 hook 不能否决子代理创建，也不能替代 Memory 读取。`SessionStart` 在恢复期间可能没有 `model` 字段，使用前先确认字段存在。[Anthropic：Hooks](https://code.claude.com/docs/en/hooks)、[Anthropic：子代理](https://code.claude.com/docs/en/sub-agents)、[Serena Memory 工具](LSP-MCP-Tools_zh_cn.md)。

## 相关概念

- [Coding Delegation State Record](delegation-state-record_zh_cn.md)——定位父级运行、allocation 和 Memory 引用。
- [Coding Child Creation](delegation-child-creation_zh_cn.md)——定位创建前持久化和核验要求。
- [Coding Child Dispatch](delegation-child-dispatch_zh_cn.md)——定位提示词引用和子代理读取边界。
- [Coding Child Reuse and Replacement](delegation-child-reuse-replacement_zh_cn.md)——定位 follow-up 与恢复边界。
- [Coding Child Lifecycle](delegation-child-lifecycle_zh_cn.md)——定位子代理身份和生命周期状态。
- [Coding Session Model](session-model_zh_cn.md)——定位 Session 语义。
- [Runtime and Model Provider Support](runtime-provider-support_zh_cn.md)——定位运行时绑定和配置核验。
- [Serena LSP and MCP Tools](LSP-MCP-Tools_zh_cn.md)——定位 Serena Memory 工具能力和语义。

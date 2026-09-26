# Coding Session Context Firewall

[English](session-context-firewall.md) | [简体中文](session-context-firewall_zh_cn.md)

本文档负责 Context Firewall：原始状态进入限制、有界检查、事实返回边界和临时项目定位。不定义职责责任、Session 语义、文件化上下文传输或工作流验收。

## 通用规范

### 原始状态进入

在多 Session Coding 中，输入侧 Session 按[职责归属](session-role-ownership_zh_cn.md)要求读取派发前确认所需的有界、只读环境与代码证据，不进行开放式项目扫描。Primary Output 仅在父级确认和放行的范围内读取更多源代码/配置状态；Change Verification 消费最终状态证据；Documentation/Comments & Git Operations 消费 Git 状态和获准文档范围。各自只返回下一步决策需要的事实与准确来源。

原始状态摄入边界由潜在输出体积、状态敏感性和仓库影响决定，而不是命令名称。单 Session 没有跨 Session Firewall，但仍须渐进读取并压缩原始状态。

### 语义 ownership 和临时定位

Firewall 只限制原始状态进入，不转移语义责任；语义权威性遵循[职责归属](session-role-ownership_zh_cn.md)。临时 UI/项目定位只属于观察它的 Session，不提升为长期 Contract 状态。

## Codex CLI / ChatGPT Desktop 特别优化指令

Codex 的自定义 Agent profile 可以用只读 `sandbox_mode` 和指定 `mcp_servers` 收窄源码及工具访问范围；`developer_instructions` 可以要求有界来源指针，但不是权限边界。必须检查继承设置，因为自定义 Agent 中省略的字段可继承父级。这些设置不等同于 Claude 的 `tools`／`disallowedTools` frontmatter，也不代表 Claude Desktop Chat 的 connector Tool-access 模式。[OpenAI：自定义子代理](https://learn.chatgpt.com/docs/agent-configuration/subagents)。

### 有界本地工具与 Skill／MCP 按需披露

使用运行环境实际暴露的本地代码检索／文件读取工具定位符号和少量源代码区间，返回稳定路径与证据指针，而非完整构建日志或仓库递归列表。Codex 自定义 Agent 可以通过经审查的 `sandbox_mode: read-only` 和窄范围 `mcp_servers` 限定职责访问；省略的字段可能继承父级设置，父级实时权限覆盖还可能影响创建后的 Child。本地 Codex Skill 先暴露元数据，选中后才加载 `SKILL.md`，references 则按需读取；只选择当前 Slice 所需的概念 owner。CLI／IDE／Desktop Codex 宿主可共享 MCP 配置，通过 `/mcp` 核实连接；不能把插件或 Chat 视图工具访问当成额外 Codex Child 或权限授权。[OpenAI：Skills 渐进式披露](https://learn.chatgpt.com/docs/build-skills)、[OpenAI：MCP 宿主配置](https://learn.chatgpt.com/docs/extend/mcp)、[OpenAI：自定义 Agent](https://learn.chatgpt.com/docs/agent-configuration/subagents)。

## Claude Code CLI / Claude Desktop 特别优化指令

### 原生有界读取与 MCP 按需发现

本地 Claude Code 中，仓库定位优先使用定向的 `Glob`/`Grep` 与少量 `Read` 范围，然后只向父级返回路径、行号来源和压缩事实；不得把完整递归目录或构建日志灌入父级。配置 MCP 工具后，可利用 Claude Code 的 **MCP Tool Search** 在实际需要时发现相关工具，而不是强制把全部 MCP Schema 提前加载到 Session。Tool Search 依赖运行环境和 Provider（第三方代理端点不一定支持），声称延迟加载节省之前须核实其已生效。Desktop Chat 可通过获准的桌面扩展/本地 MCP Server 访问本机资源；远程连接器访问远端服务；两者均须核对具体工具权限，不推断本地 shell、无限制文件系统或独立 Agent。

官方依据：[Claude Code MCP Tool Search](https://code.claude.com/docs/en/mcp)、[Desktop 连接器边界](https://support.claude.com/en/articles/11725091-when-to-use-desktop-and-web-connectors)、[本地 MCP 扩展](https://support.claude.com/en/articles/10949351-getting-started-with-local-mcp-servers-on-claude-desktop)。

Claude Code 的项目／用户自定义 subagent 可将内联 `mcpServers` 限于子代理，避免无关工具说明占用父级上下文；插件附带的 Agent 定义不一定遵循此字段。普通 Desktop Chat 的 connector Tool access `On demand` 仅是可选上下文加载优化，不代表 Worker 隔离或访问授权。[Anthropic：子代理 MCP 范围](https://code.claude.com/docs/en/sub-agents)、[Anthropic：连接器工具访问](https://support.claude.com/en/articles/13730515-manage-claude-s-tool-access)。

## 相关概念

- [Coding Session Model](session-model_zh_cn.md) — 定位 Session 语义和 Affinity。
- [Coding Session Role Ownership](session-role-ownership_zh_cn.md) — 定位职责责任归属。
- [Coding Context Exchange](context-exchange_zh_cn.md) — 定位文件化上下文传输。
- [Coding Delegation State Record](delegation-state-record_zh_cn.md) — 定位任务控制状态归属。
- [Coding Execution Control](execution-control_zh_cn.md) — 定位有界阶段和 slice 归属。

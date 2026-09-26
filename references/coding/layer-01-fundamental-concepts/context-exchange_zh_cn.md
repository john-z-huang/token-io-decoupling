# Coding Context Exchange

[English](context-exchange.md) | [简体中文](context-exchange_zh_cn.md)

本模块只定义已分配 Coding Worker 的传输 capsule：其内容限制、freshness/invalidation 检查和权威 source 规则。不定义工作区布局、目录 ownership、capability 边界、handoff 记录、任务含义、Agent 拓扑、执行规划或验收。

## 通用规范

### 传输 capsule

只传递接收 Worker 当前所需的上下文。优先把原文档以定向只读方式暴露给它；无法暴露时，父级或文件系统层可以创建父级准备的只读目录，并把点名文档机械复制到 `CONTEXT_ROOT/<worker-context-id>/imports/<source-context-id>/`；Worker 可以读取导入内容，但不得重写。父级必须在具体 handoff 或依赖关系中点名来源文档，权威 source 仍然优先且具有约束力。只有两种文件系统方式都不安全时，才使用精简的父级中转 handoff。

可复用 capsule 可以包含中性事实、准确路径和 source pointer、hash、freshness/invalidation 数据以及窄范围证据指针。不得包含实现推理、Contract 结论、私有 chain-of-thought、秘密、完整 diff、完整日志或大段源码副本。接收 Worker 先读 capsule，再只读自身需要的点名 source 路径；权威源文件仍具有约束力。

对于 `CONTEXT_ROOT/context-bootstrap/` 下的 capsule，使用：

```text
MANIFEST.md        快照身份、hash、freshness 规则
project-context.md 中性项目事实和 source pointer
policy-context.md  policy-routing pointer 和权威 section
```

Freshness 对照 `HEAD`/tree、tracked-delta fingerprint、列出的 source hash、相关未跟踪状态以及当前 task/scope 检查。实质字段变化时，只刷新受影响 section 后再依赖 capsule；否则直接读取点名的权威 source。Capsule 永远不能替代最终状态的独立验证。

## Codex CLI / ChatGPT Desktop 特别优化指令

获准接收的 Codex Worker 需要外部来源时，优先提供具名 MCP 来源或精确只读文件指针；CLI、IDE 与 Desktop Codex 可以共享当前宿主的 MCP 配置，但项目级 MCP server 依赖该项目配置已受信任。父级 ChatGPT Work 插件连接或 Chat 附件不会自动暴露给本地 spawned Codex Child。必须核实接收 Worker 确实能读取来源，保留原始路径和新鲜度数据；直接访问缺失时使用父级准备的只读 import，不能仅为加载 capsule 就扩大 MCP／工具权限。[OpenAI：MCP 客户端与信任](https://learn.chatgpt.com/docs/extend/mcp)、[OpenAI：配置信任](https://learn.chatgpt.com/docs/config-file/config-basic)。

## Claude Code CLI / Claude Desktop 特别优化指令



仅在已放行 Slice 确实需要连接源时，才为 Claude Code 子代理配置窄范围 `mcpServers`；权威性仍来自原文件或工具结果，只传具名来源指针，不复制无关工具输出。Claude Desktop 的本地 Desktop Extension 可访问明确授权的本地文件／应用；远程 MCP connector 经 Anthropic 云端执行，不得推断它可以访问私有 localhost 或仅 VPN 可达的文件。接收方没有获授权的连接器或路径时，按通用规则使用父级准备的只读交接文档；不能满足则阻塞，不能擅自扩大连接器权限。[Anthropic：子代理 MCP 范围](https://code.claude.com/docs/en/sub-agents)、[Anthropic：桌面与远程连接器](https://support.claude.com/en/articles/11725091-when-to-use-desktop-and-web-connectors)、[Anthropic：远程 MCP](https://support.claude.com/en/articles/11175166-get-started-with-custom-connectors-using-remote-mcp)。

## 相关概念

- [Coding Context Exchange Workspace Boundary](context-exchange-workspace-boundary_zh_cn.md) — 定位工作区和 capability 边界。
- [Coding Context Exchange Handoff](context-exchange-handoff_zh_cn.md) — 定位 handoff 记录归属。
- [Coding Session Context Firewall](session-context-firewall_zh_cn.md) — 定位原始状态进入边界。
- [Coding Child Dispatch](delegation-child-dispatch_zh_cn.md) — 定位 named-path 派发边界。

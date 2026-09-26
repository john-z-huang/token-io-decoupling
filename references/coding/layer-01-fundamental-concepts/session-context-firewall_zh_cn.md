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

目前没有针对该厂商的特别优化指令；遵循上述通用规范。

## Claude Code CLI / Claude Desktop 特别优化指令

目前没有针对该厂商的特别优化指令；遵循上述通用规范。

### 原生有界读取与 MCP 按需发现

本地 Claude Code 中，仓库定位优先使用定向的 `Glob`/`Grep` 与少量 `Read` 范围，然后只向父级返回路径、行号来源和压缩事实；不得把完整递归目录或构建日志灌入父级。配置 MCP 工具后，可利用 Claude Code 的 **MCP Tool Search** 在实际需要时发现相关工具，而不是强制把全部 MCP Schema 提前加载到 Session。Tool Search 依赖运行环境和 Provider（第三方代理端点不一定支持），声称延迟加载节省之前须核实其已生效。Desktop Chat 可通过获准的桌面扩展/本地 MCP Server 访问本机资源；远程连接器访问远端服务；两者均须核对具体工具权限，不推断本地 shell、无限制文件系统或独立 Agent。

官方依据：[Claude Code MCP Tool Search](https://code.claude.com/docs/en/mcp)、[Desktop 连接器边界](https://support.claude.com/en/articles/11725091-when-to-use-desktop-and-web-connectors)、[本地 MCP 扩展](https://support.claude.com/en/articles/10949351-getting-started-with-local-mcp-servers-on-claude-desktop)。

## 相关概念

- [Coding Session Model](session-model_zh_cn.md) — 定位 Session 语义和 Affinity。
- [Coding Session Role Ownership](session-role-ownership_zh_cn.md) — 定位职责责任归属。
- [Coding Context Exchange](context-exchange_zh_cn.md) — 定位文件化上下文传输。
- [Coding Delegation State Record](delegation-state-record_zh_cn.md) — 定位任务控制状态归属。
- [Coding Execution Control](execution-control_zh_cn.md) — 定位有界阶段和 slice 归属。

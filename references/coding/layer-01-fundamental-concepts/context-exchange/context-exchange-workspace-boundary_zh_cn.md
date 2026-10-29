# Coding Context Exchange 工作区边界

[English](context-exchange-workspace-boundary.md) | [简体中文](context-exchange-workspace-boundary_zh_cn.md)

本文档定义以 Serena 项目 Memory 持久化的 Agent 上下文记录的逻辑命名和授权，不定义代码工作区文件系统权限、capsule 内容、新鲜度或 handoff 授权。

## 通用规范

### Memory 名称与逻辑归属

上下文记录使用 Serena 项目 Memory 名称。默认项目数据目录下，名称映射到 `.serena/memories/`，斜杠分段创建子目录，Serena 自动补 `.md`；配置覆盖时遵循配置。保留原记录布局作为名称：`context-exchange/INDEX`；`context-exchange/workers/<worker-context-id>/INDEX`；`context-exchange/workers/<worker-context-id>/content-memo`；以及 `context-exchange/context-bootstrap/MANIFEST`、`.../project-context`、`.../policy-context`。其他 handoff/import 记录沿用原 basename 和子目录意图映射。

Memory 名称只表示逻辑归属。Serena 不为 Memory 记录提供 Worker 级可见性隔离、只读 ACL 或 OS/RW/RO/DENY 强制。工具可能向任何获准 Session 暴露已列出的 Memory。Agent 必须遵守已放行任务对可读写名称的指令，但命名空间和 Serena 项目级模式都不会在技术上强制该规则。不得声称这些记录受目录、`.gitignore`、worktree 或文件系统权限保护。

代码与权威仓库文件访问仍受各自单独批准的文件系统/工具边界约束。Memory capsule 可保存精简事实、准确权威来源指针、hash、新鲜度和范围；不得把来源全文作为权威副本存入 Memory。父级实时 mode/count/allocation/epoch 状态仍归其原 owner，不写入这些 Memory。秘密、完整 transcript 和私有推理仍禁止。

Serena Memory 工具不可用时，报告限制并阻塞依赖读取或写入该上下文记录的工作。不得回退为文件副本。独立工作可以继续。

## Codex CLI / ChatGPT Desktop 特别优化指令

只使用当前 Session 实际暴露且获准的 Serena Memory 工具。依赖记录前先列出并读取具名记录；只写已放行任务授权的名称，并确认写入结果。Codex 文件系统沙箱或 worktree 设置仍约束源文件，但不构成也不代表 Worker 级 Memory 隔离。

## Claude Code CLI / Claude Desktop 特别优化指令

仅当当前 Agent Session 暴露且授权相关 MCP 工具时使用 Serena Memory。Claude Code MCP Tool Search 可能延迟工具定义，因此先发现并核实实际工具。Claude auto memory、worktree 隔离和文件系统规则均不提供 Serena Memory 隔离。能力不可用时按通用报告/阻塞规则处理。

## 相关概念

- [Coding Context Exchange](context-exchange_zh_cn.md) — 定位 capsule 内容与新鲜度规则。
- [Coding Context Exchange Handoff](context-exchange-handoff_zh_cn.md) — 定位 handoff 记录内容。
- [Coding Session Context Firewall](../session-runtime/session-context-firewall_zh_cn.md) — 定位有界输入规则。
- [Coding Child Dispatch](../delegation/delegation-child-dispatch_zh_cn.md) — 定位任务授权。

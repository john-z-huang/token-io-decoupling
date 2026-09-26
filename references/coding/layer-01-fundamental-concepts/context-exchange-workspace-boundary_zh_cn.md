# Coding Context Exchange 工作区边界

[English](context-exchange-workspace-boundary.md) | [简体中文](context-exchange-workspace-boundary_zh_cn.md)

本文档负责文件化上下文工作区布局、目录 ownership、filesystem capability 边界、worktree 隔离和 OS 级隔离要求。不定义 capsule 内容、freshness、handoff 记录或子 Agent 复用/替换授权。

## 通用规范

### 工作区 ownership

- 设置 `CONTEXT_ROOT=<primary-worktree>/.token-io-decoupling/context/`。父 Agent 独占维护 `CONTEXT_ROOT/INDEX.md`，将每个已分配或历史 Context ID 映射到目录，并记录最小 routing 状态。规范布局是 `CONTEXT_ROOT/INDEX.md`、`CONTEXT_ROOT/<worker-context-id>/`、由父级准备的只读导入目录 `CONTEXT_ROOT/<worker-context-id>/imports/<source-context-id>/`，以及分配 bootstrap 时的 `CONTEXT_ROOT/context-bootstrap/`。
- 已分配 Worker 使用文件化交换或启用文件化 memo 前，父 Agent 为其准备 `CONTEXT_ROOT/<worker-context-id>/` 并提供准确路径。对于具体 handoff 或依赖关系，父级创建并点名相关的 `imports/<source-context-id>/` 目录和来源文档。Imports 为只读目录，不是 Worker 可写的 generated context；Worker 只能在自己的 context 目录内写入其他获准内容，除非父级点名特定文档，否则不得访问其他 Worker 目录。
- 同一任务的 Worker 通常共享 primary worktree。只有不兼容快照/环境、无法重定向的验证写入、不同权限/安全边界或明确隔离审计等具体需求，才能使用额外 worktree。Worktree 隔离本身不是权限边界。
- 仓库 `.gitignore` 必须忽略 `.token-io-decoupling`。该根目录是运行时协调状态，不是产品产物；不得自动删除。

### Capability 边界

宿主支持 filesystem capability 时，应在执行前配置最小权限：

- **RW**：仅 Worker 已放行的代码路径和自己 context 目录中允许写入的内容；不包括 `imports/`，verifier 只能写入点名的验证资产。
- **RO**：仅当前 slice 所需源路径，以及其他 Worker 被明确点名的文档或 imports。
- **DENY**：根 `INDEX.md`、未点名的 imports、其他 Worker 目录和所有其他未列出的路径。

多个 Worker 共用一个 OS identity 时，普通 Unix ownership 不能形成可靠隔离；应使用真实 sandbox、container/mount namespace、path allowlist 或等价能力。宿主不能强制所需边界时，Worker 必须停止。

## Codex CLI / ChatGPT Desktop 特别优化指令

目前没有针对该厂商的特别优化指令；遵循上述通用规范。

## Claude Code CLI / Claude Desktop 特别优化指令

当前任务放行 worktree 隔离或工具限制时，Claude Code 可使用 `EnterWorktree`/`ExitWorktree` 或自定义 Agent 的 `isolation: worktree`，并使用 `tools`/`disallowedTools` 限定工具范围。这些控制本身不能强制执行具名文件系统路径权限；必需的路径边界无法落实时阻塞依赖切片，其余情况使用普通共享 worktree 和默认工具。

## 相关概念

- [Coding Context Exchange](context-exchange_zh_cn.md) — 定位 capsule 和 freshness 归属。
- [Coding Context Exchange Handoff](context-exchange-handoff_zh_cn.md) — 定位 handoff 记录归属。
- [Coding Session Context Firewall](session-context-firewall_zh_cn.md) — 定位原始状态进入归属。
- [Coding Child Dispatch](delegation-child-dispatch_zh_cn.md) — 定位 named-path 派发边界。

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

当前 Codex 的自定义子代理可配置 `sandbox_mode` 和各自 MCP；运行环境支持且启用 Hooks 时，`PreToolUse` 可检查受支持的 `Bash`、`apply_patch` 和 MCP 调用。必须覆盖实际暴露的可写路径，并测试越界写入被拒绝；不能把 `workspace-write`、worktree 或 `AGENTS.md` 当成完整文件系统策略。Codex 的部分专用工具路径可能绕过 Hooks；若影响所需边界，必须通过操作系统／文件系统／容器权限强制保护，否则阻塞依赖 Slice。Claude 的 `permissions.deny` 语法不能照搬至 Codex。[OpenAI：子代理配置](https://learn.chatgpt.com/docs/agent-configuration/subagents)、[OpenAI：Hooks 覆盖](https://learn.chatgpt.com/docs/hooks)。

## Claude Code CLI / Claude Desktop 特别优化指令

当前任务放行 worktree 隔离或工具限制时，Claude Code 可使用 `EnterWorktree`/`ExitWorktree` 或自定义 Agent 的 `isolation: worktree`，并使用 `tools`/`disallowedTools` 限定工具范围。这些控制本身不能强制执行具名文件系统路径权限；必需的路径边界无法落实时阻塞依赖切片，其余情况使用普通共享 worktree 和默认工具。

### Claude Code Worktree 与路径约束

确有额外 checkout 隔离需要时，获准的自定义 Agent 可使用 `isolation: worktree`；必须核验实际目录，且父级维护的 Context 根目录及具名 imports 仍符合已批准的访问策略。Claude Code 的 worktree/isolation 只隔离 checkout，**不是** OS 沙箱，也不保证 Worker 只能访问自己的路径。可用时应组合真实的文件系统沙箱/容器/路径白名单，以及经过审查、匹配相关 `Read`/`Write`/`Edit`/shell 或 MCP 文件系统操作的 `PreToolUse` 守卫；校验规范化路径与 shell 可能导致的间接写入，而不是简单比较字面前缀。`PreToolUse` 不能拦截全部上下文进入方式（如文件 mention），不能声称仅靠 Hook 就满足严格的 RO/RW/DENY 边界。必需的约束无法实施时，按通用能力规则阻塞对应 Slice，不能把 `disallowedTools` 或 worktree 当成安全沙箱。

官方依据：[子代理 Worktree 隔离](https://code.claude.com/docs/en/sub-agents)、[PreToolUse 覆盖和限制](https://code.claude.com/docs/en/hooks)。

获准且可用时，组合 Claude Code 的 `permissions.deny` 与确定性的 `PreToolUse`，覆盖**所有实际可写工具路径**，包括 Shell 间接写入与 MCP 文件系统工具；依赖前必须测试一次真正被拒绝的跨 Worker 写入。`PostToolUse` 太晚，不能阻止已执行操作；`SubagentStart` 不能否决创建。本地 Desktop Extension 拥有自己的操作系统／文件权限，不能凭已安装就断言符合 Worker 的 RW/RO/DENY。[Anthropic：权限](https://code.claude.com/docs/en/permissions)、[Anthropic：Hooks](https://code.claude.com/docs/en/hooks)、[Anthropic：本地 MCP](https://support.claude.com/en/articles/10949351-getting-started-with-local-mcp-servers-on-claude-desktop)。

## 相关概念

- [Coding Context Exchange](context-exchange_zh_cn.md) — 定位 capsule 和 freshness 归属。
- [Coding Context Exchange Handoff](context-exchange-handoff_zh_cn.md) — 定位 handoff 记录归属。
- [Coding Session Context Firewall](session-context-firewall_zh_cn.md) — 定位原始状态进入归属。
- [Coding Child Dispatch](delegation-child-dispatch_zh_cn.md) — 定位 named-path 派发边界。

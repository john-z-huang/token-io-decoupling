# Coding Context Exchange

本模块只定义已分配 Coding Worker 的文件化上下文传输：工作区布局、ownership、capability 边界、freshness 和 handoff。不定义任务含义、Agent 拓扑、执行规划或验收。

## 传输 capsule

只传递接收 Worker 当前所需的上下文。优先把原文档以定向只读方式暴露给它；无法暴露时，文件系统/工具层可以把点名文档机械复制到接收方的 `imports/<source-context-id>/`，不得由 LLM 为传输重写正文。只有两种文件系统方式都不安全时，才使用精简的父级中转 handoff。

可复用 capsule 可以包含中性事实、准确路径和 source pointer、hash、freshness/invalidation 数据以及窄范围证据指针。不得包含实现推理、Contract 结论、私有 chain-of-thought、秘密、完整 diff、完整日志或大段源码副本。接收 Worker 先读 capsule，再只读自身需要的点名 source 路径；权威源文件仍具有约束力。

对于 `CONTEXT_ROOT/context-bootstrap/` 下的 capsule，使用：

```text
MANIFEST.md        快照身份、hash、freshness 规则
project-context.md 中性项目事实和 source pointer
policy-context.md  policy-routing pointer 和权威 section
```

Freshness 对照 `HEAD`/tree、tracked-delta fingerprint、列出的 source hash、相关未跟踪状态以及当前 task/scope 检查。实质字段变化时，只刷新受影响 section 后再依赖 capsule；否则直接读取点名的权威 source。Capsule 永远不能替代最终状态的独立验证。

## 工作区 ownership

- 设置 `CONTEXT_ROOT=<primary-worktree>/.token-io-decoupling/context/`。父 Agent 独占维护 `CONTEXT_ROOT/INDEX.md`，将每个已分配或历史 Context ID 映射到目录，并记录最小 routing 状态。规范布局是 `CONTEXT_ROOT/INDEX.md`、`CONTEXT_ROOT/<worker-context-id>/`，以及分配 bootstrap 时的 `CONTEXT_ROOT/context-bootstrap/`。
- 已分配 Worker 使用文件化交换前，父 Agent 为其准备 `CONTEXT_ROOT/<worker-context-id>/` 并提供准确路径。Worker 只能在该目录内写入；除非父 Agent 为具体 handoff 或依赖关系点名文档，否则不得访问其他 Worker 目录。
- 同一任务的 Worker 通常共享 primary worktree。只有不兼容快照/环境、无法重定向的验证写入、不同权限/安全边界或明确隔离审计等具体需求，才能使用额外 worktree。Worktree 隔离本身不是权限边界。
- 获准的接手 Agent 使用新的 Context ID 和目录。它只能读取父 Agent 明确暴露的前任文档，永远不得写入前任目录。
- 仓库 `.gitignore` 必须忽略 `/.token-io-decoupling/`。该根目录是运行时协调状态，不是产品产物；不得自动删除。

## Capability 边界

宿主支持 filesystem capability 时，应在执行前配置最小权限：

- **RW**：仅 Worker 已放行的代码路径和自己的 context 目录；verifier 只能写入点名的验证资产。
- **RO**：仅当前 slice 所需源路径，以及其他 Worker 被明确点名的文档。
- **DENY**：根 `INDEX.md`、其他 Worker 目录和所有未列出的路径。

多个 Worker 共用一个 OS identity 时，普通 Unix ownership 不能形成可靠隔离；应使用真实 sandbox、container/mount namespace、path allowlist 或等价能力。宿主不能强制所需边界时，Worker 必须停止。

## 文档与 handoff

每个 Worker-local `INDEX.md` 只记录 task、scope、status、最近一次实质更新、各文档用途以及 blocker/handoff 目标。只有能提供不同复用价值时才增加专项文档。上下文文件只在状态、证据或 handoff 实质变化时更新，不要每条命令都写记录。

获准的替换 handoff 应记录已完成状态、失败方案与证据、当前修改和验证状态、blocker 以及下一步最有价值的动作。父 Agent 更新根索引，只暴露点名的前任文档。前任不可用时，只记录事实支持的最小恢复说明，不能重建完整 transcript。

# 任务计划 Memory 生命周期

[English](task-plan-memory-lifecycle.md) | [简体中文](task-plan-memory-lifecycle_zh_cn.md)

本文档负责共享任务计划的创建、更新、访问和归档生命周期，默认适用于有 Issue 或无 Issue 的 Coding 工作。不负责规划方法、执行授权、父级实时调度状态或权威仓库文档。

## 通用规范

### 默认任务计划

所有现有及未来 Coding 路线都必须在实施前及执行全过程消费本 owner，无需用户额外要求计划或进入专用规划模式。遵守用户明确禁止持久化或更高优先级的写入限制：记录该例外，在获授权上下文内保持有界规划；工具缺失、权限不明或写入失败不得静默当作例外。若用户要求持久化计划而限制阻止持久化，则停止依赖工作并报告冲突。

有 Issue 时，先读取 Issue 和相关讨论，结合当前项目事实分析要求，在实施前综合改动方案。无 Issue 时，对用户明确提出的问题和当前项目事实采用相同流程。初始分析完成前，可用简明的临时计划记录目标、已知事实和待解问题，但不得声称已释放实现方向。实施或依赖派发前，必须持久化并读回具体计划。分析期间发现的新事实也必须先记录，再汇报或用于下一项依赖动作。

### 名称、存储和初始证据

优先复用用户为同一任务指定的 active plan；否则使用 `plans/PLAN-[short-english-summary]`，可包含已核实的 Issue 编号。名称不含 `.md`。默认对应归档名为 `archive-plans/PLAN-[short-english-summary]`；用户自定名称的归档映射须在现有任务授权内明确后才可归档。默认项目数据目录下，活动文件为 `<project-root>/.serena/memories/plans/PLAN-[short-english-summary].md`。遵从项目配置的数据目录覆盖及 Memory 工具映射，不硬编码第二套目录或创建文件替代品。

确认准确项目/worktree 绑定和有效的记忆维护说明。创建或更新前列出 Memory，并读取已存在的匹配计划。仅复用同一进行中任务的计划；保留无关计划，碰撞时选择不同名称。写入精简计划，再读回比对意图，之后才继续依赖工作。必需 Memory 能力缺失、必需内容不可访问或写入/读回失败时，阻塞依赖工作；报告准确操作并保留最后确认的计划。

### 计划内容

维护一份精简共享计划，包含目标和验收条件、Issue 或用户请求来源、约束和非目标、已核实项目事实与准确来源指针、所选方向和未解问题、有界步骤/依赖/验证方法、已完成/当前/剩余工作，以及实际检查/阻塞/剩余风险。区分事实、假设、提议和已接受决定。使用精简增量和有用的当前证据，不存 transcript、完整 diff、日志或私有推理。替换过时结论时保留有用决定及其证据。

### 先更新，再汇报或执行依赖动作

所有参与 Agent，包括父级和验证者，在进入/恢复任务以及依赖内容前读取同一份当前计划。取得新的实质性项目事实或任务进度变化后，先持久化精简事实/状态、来源与下一步，再读回受影响条目，之后才汇报进度、交接或执行依赖该更新的动作。例行且未变化的工具输出无需重复记录。汇报可引用计划，但不能替代更新。

用户需求变化时，先把新指令及来源记录为待分析。再分析其对范围、依赖、验收和方案的影响，持久化并读回分析及修订计划。之后父级才可授权受影响改动或派发。子上下文收到变化时，只在获准贡献范围内记录并返回父级；子 Agent 不能修订 Contract 或释放工作。只有不依赖待处理变化时，才可继续不受影响的已授权工作。

### 共享访问与更新协调

父级在每次受影响派发中提供准确项目根目录、Memory 名称、相关来源范围和允许贡献。核实每个 Agent 能在该项目使用必需 Memory 读取/更新操作；共享名称不证明跨 Session 可访问。必需访问不可用时，停止依赖分配并报告，不得静默用未经核验的代写或文件替代该 Agent 的写入。

共享计划更新须串行。父级协调同一时刻一个写者；每个写者在变更前立即重读最新条目，只修改自己获准的事实/状态，保留其他贡献，并在释放写入轮次前读回变更。不得假定 Memory 工具提供原子比较交换或锁。发生冲突或写入结果不明时，暂停受影响汇报/动作，重读并在父级既有授权内协调，不得盲目覆盖或重试过时全文。

计划是共享任务上下文，不是父级实时 mode/count/allocation/epoch 记录、执行 memo 或授权来源；不得存储这些实时调度状态。计划读写不授予其他 Memory、源文件、原始同级上下文或新效果的访问权。遵守 Context Firewall 和各角色已释放范围；提议通过父级返回。验证者只可更新具名计划贡献，对实现和 Git 仍保持只读。执行 memo 标志为 false 不豁免共享任务计划更新。

### 完成与归档

任务未完成或阻塞时保持计划活动。在所有适用 Acceptance 条件通过后，记录最终证据和剩余限制，确认匹配归档目标不存在，再仅归档本次已完成任务的计划。读回归档并列出 Memory，确认预期内容及活动名称已不存在。归档/写入/读回失败阻塞完成。归档碰撞时保留已有归档并报告。已有归档在指令层面不可变：不得编辑、删除、重命名或替换；工具可见不会技术性强制该规则。不得归档无关或未完成计划。

## Codex CLI / ChatGPT Desktop 特别优化指令

使用实际暴露且获准的 Serena MCP 操作：`list_memories`、`read_memory`、`write_memory` 或 `edit_memory`，以及完成时的 `rename_memory`。当前观察到的 Codex 工具接口中，创建接收 `{memory_name, content}`，读取接收 `{memory_name}`，重命名接收 `{old_name, new_name}`；准确参数以当前工具 schema 为准。操作前确认项目激活。这是具体的 MCP 任务计划机制；原生 `/plan`、本地回忆和聊天压缩不能持久化或更新该共享记录。当前 Session 的 Memory 调用成功只是运行时证据，不证明另一 Agent 或 Desktop Session 暴露相同工具；每个分配的 Agent 都须核实。[Codex MCP](https://learn.chatgpt.com/docs/extend/mcp)。

## Claude Code CLI / Claude Desktop 特别优化指令

对应能力是已连接且实际向该 Agent 暴露的同一个 Serena MCP Memory 服务。通过当前 MCP 工具发现机制找到工具，再按发现的 schema 和准确项目/名称调用其 `list_memories`/`read_memory`、`write_memory` 或 `edit_memory`，以及 `rename_memory`。工具发现、审批和可用性可能与 Codex 不同，不假定暴露前缀或继承连接相同。原生 Plan mode、todo 状态和自动记忆不能替代该共享任务计划。必需 Serena 操作缺失或有效权限拒绝时，阻塞依赖持久化/分配。Claude Desktop 同样遵守实际暴露规则，绝不通过 GUI 导航建立访问。[Claude Code MCP 工具可用性](https://code.claude.com/docs/en/mcp#tool-availability)。

## 相关概念

- [执行规划](execution-planning_zh_cn.md) — 规划方法与侦察顺序。
- [Serena LSP 与 MCP 工具](../session-runtime/LSP-MCP-Tools_zh_cn.md) — 项目绑定与 Memory 能力。
- [Session Context Firewall](../session-runtime/session-context-firewall_zh_cn.md) — 有界上下文进入。
- [委派 Worker 边界](../delegation/delegation-worker-boundary_zh_cn.md) — 已释放子级范围。

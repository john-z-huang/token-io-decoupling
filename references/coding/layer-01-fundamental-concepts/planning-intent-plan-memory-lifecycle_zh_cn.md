# 规划意图下的计划 Memory 生命周期

[English](planning-intent-plan-memory-lifecycle.md) | [简体中文](planning-intent-plan-memory-lifecycle_zh_cn.md)

当用户指令明确把规划、探索、制定/输出/更新计划作为任务目标时，本文档定义以 Serena 项目 Memory 持久化精简任务计划及管理其生命周期的规则。专用规划模式是可选方式；偶然提及规划、探索或计划不触发本生命周期。普通两级执行提纲和实时任务记录备注不是 Memory 计划文档；本文档不定义规划方法、决策、执行授权或权威仓库文档。

## 通用规范

### 范围与触发条件

由用户意图触发：指令必须将规划、探索、制定/输出/更新计划作为任务目标；偶然提及规划、探索或计划不算。专用规划模式可用于起草计划，但不是触发条件。普通两级执行提纲和实时任务记录备注不会触发 Memory 计划的创建或归档。

### 名称与存储

活动计划使用 `plans/PLAN-[short-english-summary]`，归档计划使用 `archive-plans/PLAN-[short-english-summary]`。Memory 名称不包含 `.md`。Serena 将名称映射到其配置的项目数据目录；默认实际文件分别为 `<project-root>/.serena/memories/plans/PLAN-[short-english-summary].md` 和 `<project-root>/.serena/memories/archive-plans/PLAN-[short-english-summary].md`。遵循项目数据目录的配置覆盖。

创建或更新计划前，先使用 `list_memories` 和 `read_memory` 检查是否已有该名称，并读取现有内容。仅当活动计划对应同一项仍在进行或未完成的任务时才更新；否则选择不同的简短英文摘要，避免名称冲突。使用 `write_memory` 或 `edit_memory` 保存精简综合计划，然后使用 `read_memory` 核验实际内容。归档前检查目标归档名称不存在。若已存在，保留该不可变归档，报告名称冲突，不得重命名、替换或覆盖。

### 归档与不可变性

满足用户意图触发条件时，为同一任务创建或更新活动计划；只要该任务仍在进行或未完成，就将计划保留在 `plans/`。验收时仅归档属于当前已完成任务的活动计划 Memory；不得归档无关活动计划。仅在该任务完成后，使用 `rename_memory` 将计划移动到对应的 `archive-plans/` 名称，然后通过 `list_memories` 和 `read_memory` 确认活动名称已不存在、归档条目存在且内容符合预期。已有归档计划在指令层面不可变：不得编辑、删除、重命名或替换。Serena 不会在技术上强制这种不可变性；使用实际暴露的 Memory 工具时必须遵守该规则。

### 内容与边界

只保存精简综合计划及有用的阶段/证据提纲。不得保存秘密、transcript、私有推理或父级实时 mode/count/allocation/epoch 状态。规划方法和侦察顺序归 [Coding Execution Planning](execution-planning_zh_cn.md)；项目知识、Memory 能力及来源/上下文边界归 [Serena LSP 与 MCP 工具](LSP-MCP-Tools_zh_cn.md) 和 [Coding Session Context Firewall](session-context-firewall_zh_cn.md)。持久化必须使用 Serena Memory；必需 Memory 工具不可用时不得回退到文件存储。

## Codex CLI / ChatGPT Desktop 特别优化指令

用户意图触发本生命周期时，仅当当前 Session 实际暴露且获准调用 Serena Memory 工具，才使用 `list_memories`、`read_memory`、`write_memory`、`edit_memory` 和（适用时）`rename_memory` 持久化精简综合计划：写入前先列出并读取，随后写入或编辑活动名称并读回核验。Codex `/plan` 是可选的起草方式；其 transcript 不能代替计划 Memory。必需 Memory 工具或权限不可用时，报告限制并阻塞依赖持久化；不得回退到文件。工具可见不等于获准修改源码或 Memory。[OpenAI：Mastering Codex remote for engineering](https://developers.openai.com/blog/mastering-codex-remote-for-engineering)。

## Claude Code CLI / Claude Desktop 特别优化指令

Claude Code `plan` permission mode 会读取文件并进行只读探索，但不会编辑源文件。用户意图触发本生命周期时，只有当前 Session 暴露 Serena MCP Memory 工具且有效权限允许各项调用，才可持久化计划。Claude Code `plan` mode 是可选起草方式，不是触发条件。核验实际工具与权限；不可用时报告限制并阻塞依赖持久化。不得绕过权限控制或回退到文件。Claude Desktop Agent 遵循相同的实际工具和权限规则。

官方参考：[Claude Code 权限与 permission mode](https://code.claude.com/docs/en/permissions)。

## 相关概念

- [Coding Execution Planning](execution-planning_zh_cn.md) — 定位规划方法和侦察顺序。
- [Serena LSP 与 MCP 工具](LSP-MCP-Tools_zh_cn.md) — 定位 Memory 操作及项目边界。
- [Coding Session Context Firewall](session-context-firewall_zh_cn.md) — 定位有界上下文输入。

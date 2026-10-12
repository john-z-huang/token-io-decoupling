# Serena LSP 与 MCP 工具

[English](LSP-MCP-Tools.md) | [简体中文](LSP-MCP-Tools_zh_cn.md)

本文档定义 Coding Agent 如何通过 Serena MCP 使用当前语言服务器结构化浏览代码，以及如何读写可复用的 Agent 项目知识。它不定义权威仓库文档的存储或父级实时 mode/count/allocation/epoch 状态；Worker memo 与上下文交换记录按各自 owner 使用项目 Memory。

## 通用规范

### 激活项目并结构化浏览代码

查询代码前，使用准确的项目根目录激活 Serena。该根目录应是 Serena 需要识别的项目目录，而不是随意选择的嵌套源码目录。确认目标项目已激活，且相关语言的语言服务器可用。Worktree 或 monorepo 子项目可能需要单独激活其自身根目录。

首次浏览不熟悉的代码文件时，先调用 `get_symbols_overview`。随后按需使用范围最小的符号操作：

- 使用 `find_symbol` 定位类、函数、方法或其他代码实体；只有需要理解实现时才请求其 body。
- 已知调用位置时，使用 `find_declaration` 查找声明。
- 使用 `find_referencing_symbols` 查找某个符号的调用者或其他引用。
- 使用 `find_implementations` 查找接口或抽象符号的实现。

尽可能把每次查询限制在已知文件或目录，限制结果大小和匹配数量，并保留准确路径与符号名作为来源指针。`search_for_pattern` 仅用于发现候选文件或文本匹配；把代码关系或候选符号作为结构证据前，先用语言服务器核实。单独的文本匹配不能证明声明、引用、实现或调用关系。

Serena、相关语言服务器或所需 LSP 操作不可用，或无法提供所需语义支持时，说明限制，并回退到定向文本搜索和路径范围较小的文件读取。不得把回退结果称为 LSP 证据。读取范围须保持在获准的项目与任务边界内。

### 读取和写入可复用项目 Memory

需要可复用的 Agent 项目知识时，先调用 `list_memories`，根据返回的名称识别相关笔记；再调用 `read_memory` 读取相关内容，然后再依赖其中的信息。Serena 提供有效的 memory-maintenance 名称时，遵循对应指引。使用 `write_memory` 保存稳定且不显而易见、能帮助后续任务的项目知识，以及用户明确要求跨会话保留的笔记。Memory 应简洁、基于事实，并在适当时链接到权威来源路径。

Serena 项目数据目录默认为 `.serena`；项目 Memory 位于 `.serena/memories/` 下。Memory 名称 `architecture/services` 会映射到 `.serena/memories/architecture/services.md`：斜杠分段会创建主题子目录，Serena 会自动添加 `.md` 扩展名。项目配置更改数据目录时，遵循配置值。只有用户明确要求跨项目 Memory 时才使用 `global/` 名称前缀。若要将现有 Skill 的文档名称和子目录意图保留为 Memory，就用对应文件名去掉 `.md` 后作为名称，并以斜杠表示子目录层级。

只有 Serena 表示 onboarding 尚未完成时才执行 onboarding。调用 onboarding 工具前，先询问用户是否继续；用户未授权时，不执行 onboarding，继续其他工作。获得授权后，遵循工具返回的指引，并在写入 onboarding 笔记前用 `read_memory` 读取其提供的有效 memory-maintenance 名称。Serena 的 `ensure_memory_maintenance_memory` 可能优先选择已配置的 `global/memory_maintenance`；否则使用或创建项目级 `memory_maintenance`。读取该配置的指引不等于获准写入跨项目 Memory：只有用户明确要求时才写入 `global/`。之后只检查生成持久笔记所需的项目材料，并通过 `write_memory` 写入。

Memory 保存可复用的 Agent 上下文，不能替代权威仓库文档。不得把 README、规范性规范或其他事实来源文档迁入 Memory 作为替代品。不得在 Memory 中保存秘密、完整 transcript、私有推理或父级实时 mode/count/allocation/epoch 状态。Worker execution memo、Context Exchange capsule/index/handoff 等 Agent-facing 记录按 [Worker Content Memo](content-memo_zh_cn.md)、[Coding Context Exchange](context-exchange_zh_cn.md)、[Coding Context Exchange Workspace Boundary](context-exchange-workspace-boundary_zh_cn.md)、[Coding Context Exchange Handoff](context-exchange-handoff_zh_cn.md) 及在授权持久化上下文记录时的 [Session Context Firewall](session-context-firewall_zh_cn.md) owner 规则持久化为项目 Memory。Memory 名称仅表达逻辑归属；Serena/工具可见性不强制 Worker 级访问隔离、只读 ACL 或 OS/RW/RO/DENY 边界。源码和权威仓库文件仍遵守其单独批准的访问边界。

## Codex CLI / ChatGPT Desktop 特别优化指令

### 在 Codex 中调用 Serena MCP

在 Codex Session 中，只能通过该 Session 实际暴露且获准使用的 Serena MCP 工具调用 Serena。下表列出当前 Codex Session 实际暴露的 24 个 Serena 工具；这是当前观测结果，不保证其他 Session 具备相同工具，工具存在也不代表获准调用。按当前暴露的准确名称及必需参数调用。缺少 LSP 查询操作时，报告限制，并仅使用获准且有界的文本搜索/读取回退，不得声称获得 LSP 证据。必需记录所需的 `list_memories`、`read_memory` 或 `write_memory` 缺失时，报告 Memory 能力不可用并阻塞依赖工作；不得回退为文件存储。


| 工具 | 类别 | 具体作用 |
| --- | --- | --- |
| `mcp__serena__activate_project` | 项目与 LSP 查询 | 激活选定的项目上下文。 |
| `mcp__serena__delete_memory` | Memory 修改 | 删除具名 Memory；仅在任务明确指示且获准时调用。 |
| `mcp__serena__edit_memory` | Memory 修改 | 编辑现有具名 Memory。 |
| `mcp__serena__find_declaration` | 代码/LSP 查询 | 从已知使用位置查找声明。 |
| `mcp__serena__find_implementations` | 代码/LSP 查询 | 查找符号或接口的实现。 |
| `mcp__serena__find_referencing_symbols` | 代码/LSP 查询 | 查找引用指定符号的符号。 |
| `mcp__serena__find_symbol` | 代码/LSP 查询 | 定位符号；按需返回其 body。 |
| `mcp__serena__get_current_config` | 运行时/工作流 | 返回当前 Serena 配置。 |
| `mcp__serena__get_diagnostics_for_file` | 代码/LSP 查询 | 获取文件的语言服务器诊断。 |
| `mcp__serena__get_symbols_overview` | 代码/LSP 查询 | 概览代码文件中的符号。 |
| `mcp__serena__initial_instructions` | 运行时/工作流 | 提供 Serena 初始使用说明。 |
| `mcp__serena__insert_after_symbol` | 源码修改 | 在指定符号后插入内容。 |
| `mcp__serena__insert_before_symbol` | 源码修改 | 在指定符号前插入内容。 |
| `mcp__serena__list_memories` | Memory 读取 | 列出可用的 Memory 名称。 |
| `mcp__serena__onboarding` | 运行时/工作流 | 仅在 onboarding 尚未完成且用户已授权时执行项目 onboarding。 |
| `mcp__serena__open_dashboard` | 运行时/工作流 | 打开 Serena Web dashboard。 |
| `mcp__serena__read_memory` | Memory 读取 | 读取具名 Memory。 |
| `mcp__serena__rename_memory` | Memory 修改 | 重命名具名 Memory。 |
| `mcp__serena__rename_symbol` | 源码修改 | 重命名代码符号。 |
| `mcp__serena__replace_in_files` | 源码修改 | 替换文件中的文本，并支持 dry-run。 |
| `mcp__serena__replace_symbol_body` | 源码修改 | 仅替换已检索并理解的符号 body。 |
| `mcp__serena__safe_delete_symbol` | 源码修改 | 符号无引用时删除；否则返回引用。 |
| `mcp__serena__search_for_pattern` | 代码/文本发现 | 搜索候选文本或文件；结构性结论须用 LSP 查询核实。 |
| `mcp__serena__write_memory` | Memory 修改 | 创建或写入具名 Memory。 |

源码和 Memory 修改必须处于任务获准范围内；工具暴露不等于授权。尤其是 `delete_memory`，仅在获得明确指示和授权后调用。本表说明工具能力类别，不代表笼统批准修改项目文件或 Memory。
`activate_project` 会确认项目激活情况，并可能返回可用语言服务器和项目 Memory 名称。这些输出可帮助识别能力，但不能证明每项 LSP 操作或每个 Memory 都可用。Serena 工具可用也不会扩大 Session 的文件系统权限或任务读写范围。

### 在 Codex 中使用 Memory

项目 Memory 使用实际暴露的 Serena Memory 工具；Codex 本地 memory 和 chat 压缩不能代替 `list_memories`、`read_memory` 或用户明确授权的 `write_memory`。onboarding 未完成时，调用 `mcp__serena__onboarding` 前先询问用户。Memory 的作用域由 Serena 项目配置决定，不会自动在 Codex Session、子 Agent 或其他运行环境之间共享。

## Claude Code CLI / Claude Desktop 特别优化指令

Claude Code 支持 MCP server；其 MCP Tool Search 默认延迟加载工具定义，并在需要时发现工具。需要 Serena 时，先在当前 Session 中发现并核验实际 Serena server 和工具名；部分配置会改为预先加载工具定义。之后只使用当前 Session 实际暴露且获准的 Serena 工具，并遵循上述项目根目录、查询结果范围、Memory 和 onboarding 规则。安装对应语言插件后，Claude Code Code Intelligence 也能提供独立的语言服务器导航和诊断；该功能与 Serena MCP 不同，也不代表当前 Session 已暴露 Serena 工具或 Memory。Claude Desktop Agent 仅能在其 Session 实际暴露相关 MCP 工具时使用 Serena。两个运行环境都不应假设 Serena Memory 会与其他 Session 或产品共享。


## 相关概念

- [运行环境与模型厂商支持](runtime-provider-support_zh_cn.md) — 定位运行环境和模型能力绑定。
- [Session Context Firewall](session-context-firewall_zh_cn.md) — 定位有界项目状态输入规则。
- [Worker Content Memo](content-memo_zh_cn.md) — 定位 Worker 执行状态的归属。
- [Coding Context Exchange](context-exchange_zh_cn.md) — 定位 capsule 和权威来源规则。
- [Coding Context Exchange Workspace Boundary](context-exchange-workspace-boundary_zh_cn.md) — 定位 Memory 逻辑命名与授权。

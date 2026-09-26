# Coding 运行环境与模型厂商支持

[English](runtime-provider-support.md) | [简体中文](runtime-provider-support_zh_cn.md)

本文档负责受支持的运行环境分支、识别各分支的证据，以及分支特定的模型控制和 Profile 绑定。不选择任务模式，不创建 Session，也不将模型名称单独视为运行环境的证明。

## 通用规范

### 受支持的运行环境分支

- **本地 Codex**：任务暴露本地文件系统/Shell 或 worktree 能力以及 Codex Agent 工具。
- **本地 Claude Code**：任务明确暴露 Claude Code Session，以及本地文件系统/Shell 或 worktree 能力。
- **ChatGPT Work**：任务暴露 Work Session、连接器或文件能力，但不代表拥有本地执行能力。
- **标准 ChatGPT**：除非明确暴露，否则不假设拥有本地执行或独立 Session 能力。

如果现有元数据无法区分这些分支，使用以下原问题兜底：`无法根据当前元数据确定当前运行环境。请在下一条指令中明确说明当前运行环境是“本地 Codex”“本地 Claude Code”“ChatGPT Work”还是“标准 ChatGPT”，然后继续。`

## Codex CLI / ChatGPT Desktop 特别优化指令

- 在本地 Codex 中使用当前暴露的模型/Session 控制；修改全局指令、覆盖指令、Skill 或仓库指令后重新启动。

### 本地 Codex 独立 Session 模型 Profile

本地 Codex 上分配独立职责时，使用以下必需绑定；这不是对整个产品可用性的声明：

| 职责 | 模型 | Reasoning 参数 |
| --- | --- | --- |
| Primary Output | `gpt-6-luna` | `medium` |
| Change Verification | `gpt-6-luna` | `medium` |
| Documentation/Comments & Git Operations | `gpt-6-luna` | `medium` |
| Context Bootstrap/Refresh | `gpt-6-luna` | `medium`；确定性刷新可用 `low` |

能力清单必须核验每项已分配绑定实际暴露的模型身份和 reasoning 参数。必需绑定缺失或未知时，将其记录到 `unavailable_capabilities`，并阻塞依赖的切片或路线。只有具体复杂性或重复失败/阻塞足以支持时，才将受影响切片局部提高至 `high`，随后恢复常规档位。只有 `high` 不足且重复失败/阻塞仍持续时，才升级到 `max`，之后恢复常规档位。

### Codex 指令加载对应关系

Codex 原生读取指令层级中的 `AGENTS.md`；不得为 Codex 创建冗余 `CLAUDE.md` 副本，也不要求 Claude Code 的 `@AGENTS.md` 导入机制。已获准的指令变更后，必须确认运行中 Session 实际加载了最新指令，无法确认则重新启动；子代理状态界面不代表指令已更新。[OpenAI：AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md)。

### Desktop 界面与宿主能力清单

当前 ChatGPT Desktop 整合了 **Chat**、**Work** 和 **Codex**。声称具备本地 Codex Session 前，必须识别实际界面：Codex 视图可提供项目／worktree 对话与开发者工具；Chat 是对话界面；Work 可以运行自己的云端子代理流程，但它属于不同运行环境，不能因此视为本地 Codex Child 或具有本地 Shell。Codex quick chat 也不自动成为绑定项目的主执行 Session。移动端 Remote 的仓库与 worktree 仍位于连接的宿主，而不是手机。依据实际工具与审批检查能力，不能仅凭桌面窗口推断。[OpenAI：桌面体验](https://learn.chatgpt.com/docs/use-chatgpt)、[OpenAI：子代理可用性](https://learn.chatgpt.com/docs/agent-configuration/subagents)、[OpenAI：worktree 宿主](https://learn.chatgpt.com/docs/environments/git-worktrees)。

### 实际生效的本地配置

Codex CLI、IDE 与 ChatGPT Desktop 中的 Codex 可以共享当前宿主的 `~/.codex/config.toml` 和受信任项目的 `.codex/config.toml`；不受信任的项目不会加载项目级 config、rules 和 hooks。按照命令行覆盖、项目、profile、用户及系统层解析当前设置；子代理还继承父级当前回合的实时权限／sandbox 覆盖。声称完整加载较大的指令文件前，检查 `AGENTS.override.md`、嵌套指令优先级与 `project_doc_max_bytes`。上述能力检查不修改本 Skill 固定的职责模型绑定。[OpenAI：配置优先级](https://learn.chatgpt.com/docs/config-file/config-basic)、[OpenAI：指令发现](https://learn.chatgpt.com/docs/agent-configuration/agents-md)、[OpenAI：子代理覆盖设置](https://learn.chatgpt.com/docs/agent-configuration/subagents)。

## Claude Code CLI / Claude Desktop 特别优化指令

### 本地 Claude Code 模型选择

只使用 `sonnet` 和 `haiku` 别名，或已核实属于 `claude-sonnet-*` 和 `claude-haiku-*` 系列的模型标识符。使用当前 Session 或启动 Agent 前，确认实际生效的模型属于这两个系列。不得使用 `claude-opus-*`、Opus 别名或任何高于或不属于 Sonnet/Haiku 系列的模型启动 Agent。不得用未解析的默认模型、继承模型或回退模型代替这项检查。

- **单代理 Coding：**所有逻辑阶段保持使用一个当前模型。实质性编码、决策、修复或验证使用 Sonnet；简单、有界且可机械检查的工作可以使用 Haiku。如果当前模型不符合要求或不足以完成任务，且无法切换到允许的模型，则阻塞依赖工作，不得继续使用该模型。
- **多代理 Coding，仅在模式和能力门禁放行后：**Primary Output、Change Verification、Documentation/Comments & Git Operations 和 Context Bootstrap 分配 Sonnet。只有确定性的 Context Refresh 才分配 Haiku；需要语义判断的刷新使用 Sonnet。启动前确认每个 Agent 实际生效的模型。这些绑定不授权创建独立 Session 或改变已锁定的子代理数量。

Claude Code 仅在所选 Sonnet 版本暴露相应档位时应用以下 effort 绑定。Haiku 不支持 effort 参数；不得为 Haiku 设置或声称存在该参数。

| 职责 | 模型 | Effort 档位 |
| --- | --- | --- |
| Primary Output | `sonnet` | `medium` |
| Change Verification | `sonnet` | `medium` |
| Documentation/Comments & Git Operations | `sonnet` | `medium` |
| Context Bootstrap/Refresh | `sonnet` | `medium`；确定性刷新可用 `low` |
| 仅确定性 Context Refresh | `haiku` | 不支持；省略 effort |

单代理 Coding 的实质工作使用 Sonnet 的 `medium`，受影响切片按下述规则升级。仅使用 Haiku 的单代理任务必须简单、有界且可机械检查；Haiku 没有 effort 控制。使用绑定前核验实际生效的模型和 effort，包括组织上限或继承设置。只有具体复杂性或重复失败/阻塞足以支持时，才将受影响的 Sonnet 切片提高至 `high`，随后恢复 `medium`。只有 `high` 不足且重复失败/阻塞仍持续，并且当前 Sonnet 模型暴露 `max` 时，才使用 `max`，随后恢复 `medium`。此 Profile 不选择 `xhigh` 或 `ultracode`。必需模型或受支持的 effort 绑定缺失或无法核实时，将其记录到 `unavailable_capabilities` 并阻塞依赖的切片或路线；不得切换到 Opus 或更高系列。

修改 `CLAUDE.md`、本 Skill 或 Agent 定义后，若当前会话无法证实已加载新指令，则启动新的 Claude Code 会话；`/tasks` 和 `/agents` 不能作为已加载的证据。

### Claude Desktop 运行界面与连接器门禁

Claude Desktop **不是**能力完全一致的单一 Coding 运行环境。在 **Code 标签页**，必须核实所选 Session 确实为具有所需 shell/文件系统和 Agent 工具的本地 Claude Code Session，才应用本模型配置；云端/远程 Code Session 应独立盘点能力。Code 标签页和本地 Claude Code CLI 可以共用适用的项目指令、设置、MCP 配置和 Hooks，但仍须核对实际 Session。Desktop **Chat** 对话或 **Cowork** 任务不会仅因运行在同一桌面应用中，就自动变为 Claude Code Agent Session。不得假定这些界面具有 Claude Code 的 `Agent`、`SendMessage`、`/tasks`、本地 shell 或 Hooks。

Desktop Chat 需要工具时，云端服务优先使用已授权的**远程连接器**；本机资源可使用已核实的**桌面扩展/本地 MCP Server**，并核对具体工具的读写权限。连接器只提供数据与操作，不等于独立 Coding Session、父级可控 Agent 身份或已锁定的子代理预算。缺少必需 Coding 能力时记录缺失项，仅阻塞依赖路线或 Slice，不将 Chat/Cowork 冒充本地 Claude Code。

Desktop Code 本地 Session 可通过模型下拉菜单选择/核对模型、侧边栏恢复 Session，并使用共用设置中的权限规则；Desktop 不提供 CLI `--allowedTools`/`--disallowedTools` 的逐 Session 等价界面。Desktop Code 可加载 `claude_desktop_config.json` 中的本地 MCP 定义，但独立 CLI **不会**自动读取该文件；必须核实或导入预期 Server，不能假定两边的 Server 列表完全相同。这些 UI 操作也不是 Desktop Chat 中的 CLI 参数。

官方依据：[Desktop Code 标签页](https://code.claude.com/docs/en/desktop)、[Desktop 本地 MCP](https://support.claude.com/en/articles/10949351-getting-started-with-local-mcp-servers-on-claude-desktop)、[桌面与远程连接器](https://support.claude.com/en/articles/11725091-when-to-use-desktop-and-web-connectors)。

### Claude Code 指令加载

Claude Code 通过 `CLAUDE.md` 加载项目指令；仓库权威规范位于 `AGENTS.md` 时，可以在获准的 `CLAUDE.md` 中用 `@AGENTS.md` 导入，而不是复制一份长期策略。通过 `/context` 查看已加载的 memory／指令文件；该界面和 `CLAUDE.md` 都不是父级实时 mode/count 记录。Desktop 远程 MCP connector 经 Anthropic 云端执行，并非从桌面本机 localhost 发起，因此须核对真实网络可达性和权限。[Anthropic：memory](https://code.claude.com/docs/en/memory)、[Anthropic：远程 MCP](https://support.claude.com/en/articles/11175166-get-started-with-custom-connectors-using-remote-mcp)。

## 相关概念

- [Coding Session Model](session-model_zh_cn.md) — 定位单代理和多代理 Session 映射。
- [Coding Session Role Ownership](session-role-ownership_zh_cn.md) — 定位职责责任。
- [Coding Delegation Mode Confirmation](delegation-mode-confirmation_zh_cn.md) — 定位定时模式选择。
- [Coding Child Creation](delegation-child-creation_zh_cn.md) — 定位运行环境中的子代理创建控制。
- [Coding Child Reuse and Replacement](delegation-child-reuse-replacement_zh_cn.md) — 定位子代理跟进控制。
- [Coding Delegation State Record](delegation-state-record_zh_cn.md) — 定位父级规范记录。
- [Coding Child Lifecycle](delegation-child-lifecycle_zh_cn.md) — 定位运行时状态观察。
- [Coding Context Exchange Workspace Boundary](context-exchange-workspace-boundary_zh_cn.md) — 定位 worktree 和工具范围控制。

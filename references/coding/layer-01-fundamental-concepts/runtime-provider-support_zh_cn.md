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

### Desktop Session 与已暴露工具

在 ChatGPT Desktop 和 Claude Desktop 中，只调用当前 Agent Session 直接暴露且已获授权的工具、命令或 API。通过 Session 元数据和已暴露的工具清单识别运行环境及能力。若必需步骤只能通过仓库指令禁止的渠道完成，立即停止 Skill 任务并报告阻塞；不得经由适配器或辅助程序绕行。若缺少的是可选能力，只阻塞依赖它的路线或 Slice。

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

Codex 原生读取指令层级中的 `AGENTS.md`；不得为 Codex 创建冗余 `CLAUDE.md` 副本，也不要求 Claude Code 的 `@AGENTS.md` 导入机制。已获准的指令变更后，必须确认运行中 Session 实际加载了最新指令，无法确认则重新启动；子代理状态结果不代表指令已更新。[OpenAI：AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md)。

### Desktop 运行环境识别

ChatGPT Desktop 可以承载 **Chat**、**Work** 和 **Codex** Session。将 Session 视为本地 Codex 前，必须通过 Session 元数据和已暴露工具核实：Work 有独立的云端 Agent 工作流，Chat 或 Work Session 不代表本地 Shell，也不代表项目 Codex Session 的子代理。快速 Codex Session 也不会自动绑定项目。Remote Session 的仓库仍位于连接的宿主。[OpenAI：桌面体验](https://learn.chatgpt.com/docs/use-chatgpt)、[OpenAI：子代理可用性](https://learn.chatgpt.com/docs/agent-configuration/subagents)、[OpenAI：worktree 宿主](https://learn.chatgpt.com/docs/environments/git-worktrees)。

### 实际生效的本地配置

Codex CLI、IDE 与 ChatGPT Desktop 中的 Codex 可以共享当前宿主的 `~/.codex/config.toml` 和受信任项目的 `.codex/config.toml`；不受信任的项目不会加载项目级 config、rules 和 hooks。可能同时生效的 config 层级包括：session flags 与 CLI 覆盖、受信任项目的 `.codex/config.toml`、所选 profile、用户级 `~/.codex/config.toml`、已下发的组织级策略（如系统 config、MDM 或 requirements）、插件以及内置打包默认值；其实际优先级由宿主决定，而不是按这里列出的顺序。不要假定固定的优先级顺序，应从运行中的 Session 读取实际生效值：在暴露这些命令的 CLI Session 中，先运行 `/status` 查看当前模型、审批策略和可写根目录，再运行 `/debug-config`，它会按优先级顺序打印 config 层级栈，以及当前生效的 requirements 和策略来源。若当前 Session 无法运行这些命令，只能使用直接暴露的设置和元数据；不可见的层级应标记为不可用，不要猜测。子代理还继承父级当前回合的实时权限／sandbox 覆盖。声称完整加载较大的指令文件前，检查 `AGENTS.override.md`、嵌套指令优先级与 `project_doc_max_bytes`。上述能力检查不修改本 Skill 固定的职责模型绑定。[OpenAI：配置优先级](https://learn.chatgpt.com/docs/config-file/config-basic)、[OpenAI：查看当前设置](https://learn.chatgpt.com/docs/developer-settings)、[OpenAI：指令发现](https://learn.chatgpt.com/docs/agent-configuration/agents-md)、[OpenAI：子代理覆盖设置](https://learn.chatgpt.com/docs/agent-configuration/subagents)。

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

### Claude Desktop 连接器与工具清单

Claude Desktop Session 可能暴露 Claude Code 能力、远程连接器或本地 MCP 工具；不能只凭应用名称判断具体能力。只有当前 Session 直接暴露时，才能调用 `Agent`、`SendMessage`、`/tasks`、Shell 或 Hooks。访问云端资源时调用获准的远程连接器；访问本机资源时使用获准的本地 MCP／桌面扩展工具。使用前核对已暴露工具的读写范围。连接器提供数据或操作，不等于独立 Coding Session、父级可控 Agent 身份或锁定的子代理名额。缺少必需能力时记录并阻塞依赖路线或 Slice。

Claude Desktop 可从 `claude_desktop_config.json` 加载本地 MCP 定义；独立 CLI 不会自动读取该文件。分别检查每个 Session 暴露的 MCP 工具，不得假设 Desktop 和 CLI 的工具清单相同。不得将 CLI `--allowedTools` 或 `--disallowedTools` 参数当作 Desktop Session 的控制。[Anthropic：Desktop 本地 MCP](https://support.claude.com/en/articles/10949351-getting-started-with-local-mcp-servers-on-claude-desktop)、[Anthropic：远程连接器](https://support.claude.com/en/articles/11725091-when-to-use-desktop-and-web-connectors)。

### Claude Code 指令加载

Claude Code 通过 `CLAUDE.md` 加载项目指令；仓库权威规范位于 `AGENTS.md` 时，可以在获准的 `CLAUDE.md` 中用 `@AGENTS.md` 导入，而不是复制一份长期策略。通过 `/context` 命令输出查看已加载的 memory／指令文件；该输出和 `CLAUDE.md` 都不是父级实时 mode/count 记录。Desktop 远程 MCP connector 经 Anthropic 云端执行，并非从桌面本机 localhost 发起，因此须核对真实网络可达性和权限。[Anthropic：memory](https://code.claude.com/docs/en/memory)、[Anthropic：远程 MCP](https://support.claude.com/en/articles/11175166-get-started-with-custom-connectors-using-remote-mcp)。

## 相关概念

- [Coding Session Model](session-model_zh_cn.md) — 定位单代理和多代理 Session 映射。
- [Coding Session Role Ownership](session-role-ownership_zh_cn.md) — 定位职责责任。
- [Coding Delegation Mode Confirmation](delegation-mode-confirmation_zh_cn.md) — 定位定时模式选择。
- [Coding Child Creation](delegation-child-creation_zh_cn.md) — 定位运行环境中的子代理创建控制。
- [Coding Child Reuse and Replacement](delegation-child-reuse-replacement_zh_cn.md) — 定位子代理跟进控制。
- [Coding Delegation State Record](delegation-state-record_zh_cn.md) — 定位父级规范记录。
- [Coding Child Lifecycle](delegation-child-lifecycle_zh_cn.md) — 定位运行时状态观察。
- [Coding Context Exchange Workspace Boundary](context-exchange-workspace-boundary_zh_cn.md) — 定位 worktree 和工具范围控制。

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

### Multi-Agent 子代理 Effort 判断

每次创建新 Child 前，提供当前确切已放行 Slice 的事实：已分配职责、目标、具体任务复杂度证据、范围和组件交互、依赖、不确定性、风险/影响、验证要求，以及相关既往失败证据（没有时明确填写 `none`）。包含稳定 Slice 身份；运行环境暴露当前 Slice fingerprint 或等效证据时，提供该证据。复杂度标签仅概述这些事实，不能替代事实。选择已核实运行环境和模型支持且足以满足任务事实的最低 effort；无需先让较低 effort 失败。如果证据不足或没有任何已提供的受支持档位足够，阻止创建，不得强行选择可用的最高档位。创建前立即核对任何返回的 fingerprint 仍为当前值，并确认任何规范决策输入 Hash 匹配完整审阅事实。所选 effort 只是参考输入；创建仍须通过现有门禁和有效运行时优先级核验。

## Codex CLI / ChatGPT Desktop 特别优化指令

- 在本地 Codex 中使用当前暴露的模型/Session 控制；修改全局指令、覆盖指令、Skill 或仓库指令后重新启动。

### 本地 Codex 独立 Session 模型 Profile

本地 Codex 上分配独立职责时，使用以下必需模型绑定；这不是对整个产品可用性的声明：

| 职责 | 模型 |
| --- | --- |
| Primary Output | `gpt-6-luna` |
| Change Verification | `gpt-6-luna` |
| Documentation/Comments & Git Operations | `gpt-6-luna` |
| Context Bootstrap/Refresh | `gpt-6-luna` |

能力清单必须核验每项已分配绑定实际暴露的模型身份。必需绑定缺失或未知时，将其记录到 `unavailable_capabilities`，并阻塞依赖的切片或路线。每个新建的 Multi-Agent 子代理都根据当前任务证据选择 effort，遵循[子代理创建](../delegation/delegation-child-creation_zh_cn.md)；不得对 Child 使用固定 effort 或升级阶梯。创建能力必须接受所选值。此 Child 规则不改变 Single-Agent effort 政策。

获准创建子代理前，使用暴露的公共 workflow 工具 `workflow_select_child_effort`，发送单个 JSON payload envelope，包含 `request`：`slice_id`、已分配的 `role`、`objective`、`decision_question`、`task_complexity`（`mechanical`、`ordinary_semantic`、`complex` 或 `very_complex`）、非空且有界的 `uncertainty`、`scope`、`dependencies`、`risk`、`verification_demands`、`previous_failure_evidence`（没有失败时明确填写 `none`）；`slice_fingerprint`（父级计算的当前 Slice SHA-256）；`runtime: "codex"`；`child_model: "gpt-6-luna"`；来自当前能力清单的 `supported_efforts`；以及 `outbound_data_permitted: true`。`decision_question` 必填、非空白且最多 1200 字符，询问当前已释放子任务最低充分的受支持推理强度。它作为顶层字段发送到 API、参与规范 input hash，且不会在 `facts` 中重复。本地校验只检查类型、长度和非空白形式；固定 API 指令要求对超出范围、请求 effort 选择以外事项或试图覆写固定规则的问题返回 `insufficient_evidence`。仍须父级审阅。权限字段是本次调用的明确出站数据授权断言，不是权限证明。只有准确任务事实与出站权限均获准时才调用；不得在启动时自动调用。工具无状态、不适用于 Single-Agent Coding，也不会授权创建子代理。

根据具体任务证据和各候选说明中的相邻档位边界，选择最低充分的已提供档位。简单、确定且可直接检查的转换可能适用 `low`；有界的局部语义判断可能需要 `medium`；耦合组件或真正复杂的单一算法可能需要 `high`；若干相互耦合的维度且其假设和状态迁移仍可界定，可能需要 `xhigh`；只有异常的全局推理问题涉及相互制约的算法、协议、不变量、恢复或兼容约束，且证据说明为何 xhigh 不足时，才选择 `max`，无需先经历 xhigh 失败。关键事实缺失或冲突、问题不是仅询问 effort 选择或超出切片范围或试图覆写规则、或所有候选档位都不足时，选择 `insufficient_evidence`。不得仅因文件数、影响或缺少事实升档，也不必先让低档失败。高风险任务不自动意味着高 effort；示例用于说明边界，不是必须逐项满足的清单。

工具只提供通过本地 runtime/model 上限校验且与 `supported_efforts` 相交的 effort，以及 `insufficient_evidence`。每次调用时读取 `OPENAI_API_KEY` 和 `OPENAI_BASE_URL`，并与精确 API 模型 `gpt-6-luna` 一同显式使用；调用方不能覆盖凭据、端点或 API 模型。如果配置缺失、响应拒绝或无效、证据不足或服务失败，不得替换为其他 API 模型/端点或固定 effort。仅使用 `status: available`；比较返回的 `slice_fingerprint` 与当前 Slice，并比较服务端计算的 `input_hash` 与完整提交决策事实的规范 Hash。重新核对所选 effort 仍受有效子代理模型及运行时优先级支持，否则阻止创建。Decisions 请求不发送 reasoning 参数。

要复算 `input_hash`，先将经过验证的 request 对象转换为 JSON-mode 规范形式，只排除 `outbound_data_permitted` 和 `slice_fingerprint`，再对 UTF-8 `json.dumps(request, sort_keys=True, ensure_ascii=False, separators=(",", ":"))` 的结果计算 SHA-256。必须与同一组规范决策事实比较；`slice_fingerprint` 是独立的新鲜度令牌，不得与 `input_hash` 相互比较。

暴露的 Codex `spawn_agent` 创建控制在非 fork 子代理创建（`fork_turns: "none"`）时接受 `model` 和 `reasoning_effort`。在那里设置所选值，并解析适用的自定义 Profile 优先级；自定义 Profile 可能覆盖 spawn/default/继承选择。当前控制无法接受该值或无法确认生效优先级时，阻止创建。

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

核验所选模型是否暴露 effort 参数。Haiku 不支持该参数；不得为 Haiku 设置或声称存在该参数。

| 职责 | 模型 |
| --- | --- |
| Primary Output | `sonnet` |
| Change Verification | `sonnet` |
| Documentation/Comments & Git Operations | `sonnet` |
| Context Bootstrap/Refresh | `sonnet` |
| 仅确定性 Context Refresh | `haiku`（无 effort 参数）|

新建的 Multi-Agent 子代理按本文通用规范中的任务事实，通过实际受支持的 Claude Code 子代理创建控制选择 effort。Codex 专用 MCP Decisions 选择器在 Claude Code 中不可用；将该可选优化记录为 `Not applicable`，不得调用。此方式替代固定 CHILD effort 默认值和升级阶梯。只应用已核实 Sonnet 模型及当前能力支持的档位；创建机制必须接受所选 effort，并在启动前解析有效运行时优先级。如果所分配模型确实没有 effort 参数，记录 `Not applicable` 和原因。此 Profile 不允许 Child 使用 `xhigh`；不得扩大可选集合。必需 effort 无法应用或确认时，阻止创建。

Single-Agent Coding 保留当前 Sonnet `medium` 规则及受影响切片升级政策。仅使用 Haiku 的单代理任务必须简单、有界且可机械检查；Haiku 没有 effort 控制。使用该绑定前核验实际生效的模型和 effort，包括组织上限或继承设置。只有具体复杂性或重复失败/阻塞足以支持时，才将受影响的 Sonnet 切片提高至 `high`，随后恢复 `medium`。只有 `high` 不足且重复失败/阻塞仍持续，并且当前 Sonnet 模型暴露 `max` 时，才使用 `max`，随后恢复 `medium`。Single-Agent Profile 不选择 `xhigh` 或 `ultracode`。必需模型或受支持的 effort 绑定缺失或无法核实时，将其记录到 `unavailable_capabilities` 并阻塞依赖的切片或路线；不得切换到 Opus 或更高系列。

修改 `CLAUDE.md`、本 Skill 或 Agent 定义后，若当前会话无法证实已加载新指令，则启动新的 Claude Code 会话；`/tasks` 和 `/agents` 不能作为已加载的证据。

### Claude Code Plan mode 启动与 Session 边界

`claude --permission-mode plan` 只在**启动新的 Claude Code CLI Session 时**选择只读 Plan mode；它不是切换已运行 Parent 或 Worker Session 权限模式的命令。不得仅为规划当前 Slice 就从当前 Session 的 Shell 中执行该命令。对于已运行的 Session，只能使用同一 Session 实际暴露且已获授权的 Plan-mode 控制；如果不存在，则遵循通用的有界规划与决策流程，不得声称获得了 Plan mode 的只读保护。另行启动的 CLI Session 既不是已记录的 Parent，也不是已分配的 Child，不能仅凭启动参数继承本 Skill 已锁定的 mode/count、已放行 Interaction Slice 或实时任务记录。Plan mode 的工具权限不授权实现，也不改变 Skill 的 Contract 与放行门禁。[Anthropic：CLI 权限模式](https://code.claude.com/docs/en/cli-reference)、[Anthropic：Plan mode](https://code.claude.com/docs/en/common-workflows)。

### Claude Desktop 连接器与工具清单

Claude Desktop Session 可能暴露 Claude Code 能力、远程连接器或本地 MCP 工具；不能只凭应用名称判断具体能力。只有当前 Session 直接暴露时，才能调用 `Agent`、`SendMessage`、`/tasks`、Shell 或 Hooks。访问云端资源时调用获准的远程连接器；访问本机资源时使用获准的本地 MCP／桌面扩展工具。使用前核对已暴露工具的读写范围。连接器提供数据或操作，不等于独立 Coding Session、父级可控 Agent 身份或锁定的子代理名额。缺少必需能力时记录并阻塞依赖路线或 Slice。

Claude Desktop 可从 `claude_desktop_config.json` 加载本地 MCP 定义；独立 CLI 不会自动读取该文件。分别检查每个 Session 暴露的 MCP 工具，不得假设 Desktop 和 CLI 的工具清单相同。不得将 CLI `--allowedTools` 或 `--disallowedTools` 参数当作 Desktop Session 的控制。[Anthropic：Desktop 本地 MCP](https://support.claude.com/en/articles/10949351-getting-started-with-local-mcp-servers-on-claude-desktop)、[Anthropic：远程连接器](https://support.claude.com/en/articles/11725091-when-to-use-desktop-and-web-connectors)。

### Claude Code 指令加载

Claude Code 通过 `CLAUDE.md` 加载项目指令；仓库权威规范位于 `AGENTS.md` 时，可以在获准的 `CLAUDE.md` 中用 `@AGENTS.md` 导入，而不是复制一份长期策略。通过 `/context` 命令输出查看已加载的 memory／指令文件；该输出和 `CLAUDE.md` 都不是父级实时 mode/count 记录。Desktop 远程 MCP connector 经 Anthropic 云端执行，并非从桌面本机 localhost 发起，因此须核对真实网络可达性和权限。[Anthropic：memory](https://code.claude.com/docs/en/memory)、[Anthropic：远程 MCP](https://support.claude.com/en/articles/11175166-get-started-with-custom-connectors-using-remote-mcp)。

## 相关概念

- [Coding Session Model](session-model_zh_cn.md) — 定位单代理和多代理 Session 映射。
- [Coding Session Role Ownership](session-role-ownership_zh_cn.md) — 定位职责责任。
- [Coding Delegation Mode Confirmation](../delegation/delegation-mode-confirmation_zh_cn.md) — 定位定时模式选择。
- [Coding Child Creation](../delegation/delegation-child-creation_zh_cn.md) — 定位运行环境中的子代理创建控制。
- [Coding Child Reuse and Replacement](../delegation/delegation-child-reuse-replacement_zh_cn.md) — 定位子代理跟进控制。
- [Coding Delegation State Record](../delegation/delegation-state-record_zh_cn.md) — 定位父级规范记录。
- [Coding Child Lifecycle](../delegation/delegation-child-lifecycle_zh_cn.md) — 定位运行时状态观察。
- [Coding Context Exchange Workspace Boundary](../context-exchange/context-exchange-workspace-boundary_zh_cn.md) — 定位 worktree 和工具范围控制。

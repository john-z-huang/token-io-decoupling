# Coding 子 Agent 创建

[English](delegation-child-creation.md) | [简体中文](delegation-child-creation_zh_cn.md)

本文档负责 Multi-Agent 子代理创建的唯一能力入口。它消费已放行的模式/数量门禁、已预留且分配职责的名额、符合条件的输出类型，以及已放行的具体 Interaction Slice；不重新确认 mode/count，不分配职责，不决定 replacement 或生命周期政策。创建成功后只回写实际 Agent 身份和初始 lifecycle，且不得新增名额。

## 通用规范

### 创建能力

创建子代理前，按[运行环境与模型供应商支持](../session-runtime/runtime-provider-support_zh_cn.md)中的适用路径执行。仅当已分配的运行环境/模型支持 effort 控制时，才根据确切的已放行任务事实选择 effort。选择时必须包括已分配职责、目标、具体复杂度证据、范围/交互、依赖、不确定性、风险、验证要求和既往失败证据（没有时写 `none`）；仅有复杂度标签不足以支持选择。选择已核实支持且足以满足任务的最低 effort，无需先让较低档位失败。证据不足、没有任何已提供档位足够，或创建控制无法接受/确认所选 effort 时，阻止创建。若适用运行时 profile 明确不提供 effort（例如原生 Haiku profile），记录 `Not applicable` 并说明原因，不得虚构设置。创建前立即重新核对当前 Slice 证据，并按运行时 owner 的要求分别比较任何实际返回的规范决策输入 Hash 和 Slice fingerprint；运行时路径未返回的 Hash 或 fingerprint 无需强求。此核验仅限创建。若操作接受必需参数但没有额外运行时解析观察，可直接继续，无需额外观察。不得要求子代理自行检查或报告其模型、effort。

必须使用运行环境真实且由父级控制的子代理机制。创建前必须具有已放行的 Multi-Agent 门禁、锁定的正整数数量、已分配职责且尚未绑定子代理的预留名额，以及本次 `slice_status: released` 的 Interaction Slice（明确目标、路径/修改、返回条件和 memo 派发开关）。在已放行任务快照中包含锁定的[会话审计可见性](../session-runtime/session-audit-visibility_zh_cn.md)配置，使 Worker 能遵循消息可见性和摘要频率。输出必须是实际代码/配置实现，或本 Skill 指令/参考文档的编写编辑。普通非 Skill 文档（包括伴随代码修改的文档）由根父级编写，不得触发子代理创建。不得在会话开始时或仅因选择 Multi-Agent 就初始化子代理。预留名额或模式放行本身不授权创建子代理。不得将 peer chat 或无法跟踪的通用任务当作持久子代理。必须具备子代理身份、父级控制的返回/继续路径、有界等待和可观察生命周期。创建后把实际身份与生命周期绑定到同一 allocation；不得将该名额释放给另一个子代理。能力缺失或无法核实时阻塞创建，不更改模式或数量。

## Codex CLI / ChatGPT Desktop 特别优化指令

本地 Codex 使用当前暴露的 MultiAgentV1/V2 spawn 操作；模型与能力绑定遵循[运行环境与模型厂商支持](../session-runtime/runtime-provider-support_zh_cn.md)。

对于 Codex 自定义子代理，获准的 `.codex/agents/<name>.toml` 可设置 `name`、`description`、`developer_instructions`、`model`、`model_reasoning_effort`、`sandbox_mode` 和 `mcp_servers`。通过暴露的父级 spawn 操作设置按任务选择的 effort，并解析适用自定义 Profile 优先级；自定义文件可能覆盖 spawn/default/继承值。无法接受所选档位或无法确认有效优先级时，阻止创建。若操作接受所选档位且没有额外的运行时解析观察，无需额外观察即可继续。不得要求子代理检查或报告这些设置。注册 Profile 不是创建或分配新子代理；宿主全局并发上限不等于本次会话锁定数量。Claude 的 `.claude/agents/*.md` frontmatter 不能作为 Codex 配置格式。[OpenAI：自定义子代理](https://learn.chatgpt.com/docs/agent-configuration/subagents)。

### 原生子代理 Profile 与继承权限

当前本地 Codex 暴露内置 `default`、`worker` 和 `explorer` Profile；获准的 `.codex/agents/` 或 `~/.codex/agents/` 自定义 Profile 可以细化已放行职责。创建 Child 前核验 `agents.enabled` 与实际 spawn 能力。在 spawn 操作中设置已核实模型和按任务选择的 effort，并解析适用自定义文件和运行时优先级；控制无法接受或确认所选值时阻止创建。继承的 `sandbox_mode`／`mcp_servers`／`skills.config` 属于独立权限边界，仍须检查。父级实时 `/permissions` 或 CLI sandbox 覆盖可能被重新应用到子代理；不能把 TOML 中的只读默认值当成已强制生效的证明。宿主的 `agents.max_concurrent_threads_per_session` 限制的是**同时打开的线程数**，不是会话已锁定的 Child 总数。[OpenAI：子代理 Profile、优先级与权限](https://learn.chatgpt.com/docs/agent-configuration/subagents)。

## Claude Code CLI / Claude Desktop 特别优化指令

本地 Claude Code 在数量和 allocation 放行后使用内建 `Agent` 工具，显式指定 `subagent_type`（`general-purpose` 或已命名自定义子代理）、职责要求的模型、受支持时按任务选择的 effort、有界任务提示和返回条件。模型与 effort 绑定遵循[运行环境与模型供应商支持](../session-runtime/runtime-provider-support_zh_cn.md)；创建操作无法设置或确认所选档位时，阻止创建。若操作已接受所选档位，无需额外运行时解析观察即可继续。不得要求子代理检查或报告自身设置。内建 Explore/Plan Agent 不返回可复用 Agent ID，不得作为持久子代理。

Claude Code v2.1.292 及之后版本的非 fork `Agent` 调用接受逐次 `effort`；在那里设置所选值。`CLAUDE_CODE_EFFORT_LEVEL` 优先于调用参数和自定义 Agent frontmatter，因此启动前解析该环境值。旧版宿主没有逐次控制时，只有在定义修改已获准范围内，才使用现成且获准的 `.claude/agents/<name>.md` 或 `~/.claude/agents/<name>.md` 定义配置 `effort`；否则若无法确认必需选择则阻止创建。Haiku 没有 effort 参数。优先使用工具白名单中排除 `Agent` 和 peer 消息的具名可复用子代理，防止递归委派。[Anthropic：子代理和 effort 档位](https://code.claude.com/docs/en/sub-agents#choose-an-effort-level)。

### 原生子代理定义与创建门禁

同一获准职责需要跨 Slice 复用时，优先使用经过审查的项目级或个人级 `.claude/agents/`、`~/.claude/agents/` 自定义 Agent；使用 `name`/`description` 表达选择条件，以显式 `tools`/`disallowedTools` 与 `maxTurns` 限制工具和执行轮次。从 Worker 允许的工具中排除 `Agent`（或显式禁止），并排除 peer messaging；当前 Claude Code 的子代理在未限制时可能继续创建嵌套 Agent。仅使用 `skills` 预加载该职责必需的参考内容，不预加载整个 Skill 或无关概念。插件自带 Agent 的 `hooks`、`mcpServers` 和 `permissionMode` frontmatter 会被忽略；需要这些控制时使用获准的项目/个人 Agent 或 Session 设置。

实际 `Agent` 调用仍须等待已放行的具体 Slice 和未绑定的预留名额。`SubagentStart` Hook 可以注入上下文，**不能阻止创建**，不可替代创建前门禁。Claude Desktop 只有在当前 Session 直接暴露并授权内建 `Agent` 工具时才能调用；否则将其记录为不可用并阻塞依赖的 Slice。依据创建时控制和 Runtime owner 解析实际模型，不得仅凭应用身份推断工具是否可用。

官方依据：[自定义子代理与 frontmatter](https://code.claude.com/docs/en/sub-agents)、[SubagentStart Hook](https://code.claude.com/docs/en/hooks)。

已审查的项目／用户自定义 subagent 若支持 `background` 和 `isolation: worktree`，两者仅控制**已经获准名额**的执行方式。后台子代理的交互式权限／工具可能受限：已放行任务需要这些能力时，应使用可用的前台调用，不可默默省略要求。Worktree 隔离的是仓库副本，不是父级 Context 根目录中的逐 Worker 路径权限。[Anthropic：subagents](https://code.claude.com/docs/en/sub-agents)。

## 相关概念

- [Coding Child Lifecycle](delegation-child-lifecycle_zh_cn.md) — 定位子 Agent 状态归属。
- [Coding Child Role Allocation](delegation-child-role-allocation_zh_cn.md) — 定位名额和职责分配。
- [Coding Child Dispatch](delegation-child-dispatch_zh_cn.md) — 定位实际派发边界。
- [Coding Child Reuse and Replacement](delegation-child-reuse-replacement_zh_cn.md) — 定位获准的复用和替换。
- [Coding Session Model](../session-runtime/session-model_zh_cn.md) — 定位 role 和 Session 归属。
- [Coding Context Exchange](../context-exchange/context-exchange_zh_cn.md) — 定位必要的上下文传输归属。
- [Coding Session 审计可见性](../session-runtime/session-audit-visibility_zh_cn.md) — 定位会话审计配置。

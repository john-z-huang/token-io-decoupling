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
- 在 ChatGPT Work 中只使用明确暴露的模型、Session、文件、连接器和执行工具。
- 在标准 ChatGPT 中不假设拥有本地执行、Git、worktree 或独立 Session。

### 本地 Codex 独立 Session 模型 Profile

本地 Codex 上分配独立职责时，使用以下必需绑定；这不是对整个产品可用性的声明：

| 职责 | 模型 | Reasoning 参数 |
| --- | --- | --- |
| Primary Output | `gpt-6-luna` | `medium` |
| Change Verification | `gpt-6-luna` | `medium` |
| Documentation/Comments & Git Operations | `gpt-6-luna` | `medium` |
| Context Bootstrap/Refresh | `gpt-6-luna` | `medium`；确定性刷新可用 `low` |

能力清单必须核验每项已分配绑定实际暴露的模型身份和 reasoning 参数。必需绑定缺失或未知时，将其记录到 `unavailable_capabilities`，并阻塞依赖的切片或路线。只有具体复杂性或重复失败/阻塞足以支持时，才将受影响切片局部提高至 `high`，随后恢复常规档位。只有 `high` 不足且重复失败/阻塞仍持续时，才升级到 `max`，之后恢复常规档位。

## Claude Code CLI / Claude Desktop 特别优化指令

- 在本地 Claude Code 中，记录当前 Session 暴露的确切模型标识符或别名，并且只使用其实际暴露的参数控制。应用下方的 Claude Code 模型选择规则；不得推断模型或假设存在 reasoning 控制。

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

### 运行环境工具对应关系

厂商专属操作按下表执行；工作流概念继续共用。

| Skill 使用的 Codex 专有控制 | Claude Code 对应能力 | Claude Code 的执行要求 |
| --- | --- | --- |
| 15 秒模式问题所需的非阻断定时用户输入工具 | 未查到 Claude Code 原生 `AskUserQuestion` 超时或等价异步回复工具 | 以普通进度文字发出模式问题，保持当前 turn 活跃并计时 15 秒，检查宿主在截止前提供的回复。不得调用会阻断的 `AskUserQuestion`。若宿主在活跃 turn 中无法提供回复，记录该限制并在 15 秒后采用默认值，不得无限等待。 |
| 父级任务面板/任务控制记录 | 没有与 Codex 父级任务面板相同的持久能力；`/tasks` 只短暂展示子代理运行状态 | 在父级会话中维护结构化模式/数量和切片记录，每次路线放行前读回；不得将 `/tasks` 当作规范记录。 |
| `MultiAgentV1/V2` 子代理创建 | 内建 `Agent` 工具 | 数量和 allocation 放行后，调用 `Agent`，显式指定 `subagent_type`（`general-purpose` 或已命名自定义子代理）、实质职责用 `model: sonnet`，仅确定性刷新用 `model: haiku`，并给出有界任务提示。可用时在 `/tasks` 核验实际模型；被禁模型可能回退到继承模型。Explore/Plan 不返回可复用 Agent ID，不得作为持久子代理。 |
| Codex 为每个子代理指定 reasoning 参数 | 自定义子代理 frontmatter 的 `effort`，或由子代理继承已显式设置的会话 `/effort`；通用 `Agent` 调用没有逐次 effort 参数 | 需要 Sonnet 职责专属 effort 时，使用获准的 `.claude/agents/<name>.md` 或 `~/.claude/agents/<name>.md` 定义，填写 `name`、`description`、`model: sonnet`、`effort: medium` 及适当的工具白名单。无需自定义定义时，先设置并核验 Sonnet 会话 effort，再启动子代理。Haiku 省略 effort。必需的实际 effort 无法核实时阻塞该绑定。 |
| Codex 发送/等待/状态生命周期 | 向返回的 Agent ID 使用 `SendMessage`、`Agent` 结果以及可用时的 `/tasks` | 在父级记录中保存返回的 ID，以有界运行时等待取得结果；用 `SendMessage` 继续同一子代理。再次调用 `Agent` 会创建新子代理并消耗另一个名额。`/tasks` 不再显示后，仍在父级记录保留完成/错误状态。 |
| Codex 独立子 Session/任务界面 | Claude Code 子代理在父会话中拥有独立上下文；没有完全相同的独立 Codex 任务界面 | 把子代理视为已分配的子级上下文，只向父级返回；准确报告实际隔离和验证独立性。不得以 agent team 或 peer channel 替代。 |
| Codex worktree 和工具范围控制 | Claude Code `EnterWorktree`/`ExitWorktree` 或自定义代理 `isolation: worktree`，以及 `tools`/`disallowedTools` | 仅在当前任务明确放行 worktree 隔离或工具限制时使用。这些控制本身不能强制执行具名文件系统路径权限；必需的路径边界无法落实时阻塞依赖切片。其余情况使用普通共享 worktree 和 Claude Code 默认工具。 |
| Codex 在策略修改后重启 | 没有完全相同的热重载保证 | 修改 `CLAUDE.md`、Skill 或 Agent 定义后，若当前会话无法证实已加载新指令，则启动新的 Claude Code 会话；不要假定 `/tasks` 或 `/agents` 会重载。 |

需要可复用的 Claude Code 子代理时，优先使用禁止 `Agent` 和 peer 消息工具的命名自定义子代理，以维持禁止递归创建的规则。自定义定义不在获准修改范围内时，只有在能核验实际 effort 和工具边界时，才使用内建 `general-purpose` 类型、显式模型和有界提示；否则阻塞该子代理职责。Codex 专有界面便利功能若无 Claude Code 对应项，而父级记录和结果已提供所需证据，则 Claude Code 不必考虑该界面功能。

## 相关概念

- [Coding Session Model](session-model_zh_cn.md) — 定位单代理和多代理 Session 映射。
- [Coding Session Role Ownership](session-role-ownership_zh_cn.md) — 定位职责责任。

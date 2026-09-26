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

## 相关概念

- [Coding Session Model](session-model_zh_cn.md) — 定位单代理和多代理 Session 映射。
- [Coding Session Role Ownership](session-role-ownership_zh_cn.md) — 定位职责责任。
- [Coding Delegation Mode Confirmation](delegation-mode-confirmation_zh_cn.md) — 定位定时模式选择。
- [Coding Child Creation](delegation-child-creation_zh_cn.md) — 定位运行环境中的子代理创建控制。
- [Coding Child Reuse and Replacement](delegation-child-reuse-replacement_zh_cn.md) — 定位子代理跟进控制。
- [Coding Delegation State Record](delegation-state-record_zh_cn.md) — 定位父级规范记录。
- [Coding Child Lifecycle](delegation-child-lifecycle_zh_cn.md) — 定位运行时状态观察。
- [Coding Context Exchange Workspace Boundary](context-exchange-workspace-boundary_zh_cn.md) — 定位 worktree 和工具范围控制。

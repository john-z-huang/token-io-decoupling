# Coding 运行环境与模型厂商支持

[English](runtime-provider-support.md) | [简体中文](runtime-provider-support_zh_cn.md)

本文档负责受支持的运行环境分支、识别各分支的证据，以及分支特定的模型控制和 Profile 绑定。不选择任务模式，不创建 Session，也不将模型名称单独视为运行环境的证明。

## 受支持的运行环境分支

- **本地 Codex**：任务暴露本地文件系统/Shell 或 worktree 能力以及 Codex Agent 工具。
- **本地 Claude Code**：任务明确暴露 Claude Code Session，以及本地文件系统/Shell 或 worktree 能力。
- **ChatGPT Work**：任务暴露 Work Session、连接器或文件能力，但不代表拥有本地执行能力。
- **标准 ChatGPT**：除非明确暴露，否则不假设拥有本地执行或独立 Session 能力。

如果现有元数据无法区分这些分支，使用以下原问题兜底：`无法根据当前元数据确定当前运行环境。请在下一条指令中明确说明当前运行环境是“本地 Codex”“本地 Claude Code”“ChatGPT Work”还是“标准 ChatGPT”，然后继续。`

## 按分支使用能力

- 在本地 Codex 中使用当前暴露的模型/Session 控制；修改全局指令、覆盖指令、Skill 或仓库指令后重新启动。
- 在本地 Claude Code 中，记录当前 Session 暴露的确切 Claude 模型标识符或别名，并且只使用其实际暴露的参数控制。当前 Session 承担所有逻辑阶段时，使用该当前模型。不得推断模型或假设存在 reasoning 控制。本支持文档不声明 Claude Code 独立 Session 职责 Profile。
- 在 ChatGPT Work 中只使用明确暴露的模型、Session、文件、连接器和执行工具。
- 在标准 ChatGPT 中不假设拥有本地执行、Git、worktree 或独立 Session。

## 本地 Codex 独立 Session 模型 Profile

本地 Codex 上分配独立职责时，使用以下必需绑定；这不是对整个产品可用性的声明：

| 职责 | 模型 | Reasoning 参数 |
| --- | --- | --- |
| Primary Output | `gpt-6-luna` | `medium` |
| Change Verification | `gpt-6-luna` | `medium` |
| Documentation/Comments & Git Operations | `gpt-6-luna` | `medium` |
| Context Bootstrap/Refresh | `gpt-6-luna` | `medium`；确定性刷新可用 `low` |

能力清单必须核验每项已分配绑定实际暴露的模型身份和 reasoning 参数。必需绑定缺失或未知时，将其记录到 `unavailable_capabilities`，并阻塞依赖的切片或路线。只有具体复杂性或重复失败/阻塞足以支持时，才将受影响切片局部提高至 `high`，随后恢复常规档位。只有 `high` 不足且重复失败/阻塞仍持续时，才升级到 `max`，之后恢复常规档位。

## 相关概念

- [Coding Session Model](session-model_zh_cn.md) — 定位单代理和多代理 Session 映射。
- [Coding Session Role Ownership](session-role-ownership_zh_cn.md) — 定位职责责任。

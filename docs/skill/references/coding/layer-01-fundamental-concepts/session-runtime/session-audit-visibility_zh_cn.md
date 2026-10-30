# Coding 会话审计可见性

[English](session-audit-visibility.md) | [简体中文](session-audit-visibility_zh_cn.md)

本文档定义会话审计可见性预设、推理摘要频率和 Worker 日志可见性。它负责配置值及其可见性语义；适用的工作流决策节点负责提问、计时、恢复、迁移和记录解决流程。

## 通用规范

### 配置值

根父级负责会话配置。用户可选择 `audit_mode`、`root_reasoning_cadence` 和 `worker_reasoning_cadence`；每个字段分别记录来源。这些是 Skill 策略，不是产品原生开关。

```yaml
audit_mode: balanced
root_reasoning_cadence: milestone_only
worker_reasoning_cadence: full
source: {audit_mode: default, root_reasoning_cadence: default, worker_reasoning_cadence: default}
revision: session-audit/v2
```

| 字段 | 合法值 | 默认值 | 含义 |
| --- | --- | --- | --- |
| `audit_mode` | `economy`、`balanced`、`full` | `balanced` | 选择 Root 可见副本预设。 |
| `root_reasoning_cadence` | `full`、`milestone_only`、`off` | `milestone_only` | 选择 Root 可选摘要频率。 |
| `worker_reasoning_cadence` | `full`、`milestone_only`、`off` | `full` | 独立选择 Worker 可选摘要频率。 |
| `source.<field>` | 每个可选字段分别为 `explicit`、`default` | `default` | `explicit` 表示用户选择了该字段；`default` 表示由策略提供。 |
| `revision` | `session-audit/v2` | `session-audit/v2` | schema 与策略语义修订版本；纯文字编辑不改变它。 |

任务记录结构和配置提问字段由[委派状态记录](../delegation/delegation-state-record_zh_cn.md)定义。所选路线负责收集和更新该记录。

### 可见副本预设

所有预设下，完整实际安全任务正文和返回正文都必须可取得。Root 在依赖 Worker 返回前完整读取实际正文。预设仅控制 Root 展示的可见副本，不降低证据要求或 Worker 可见性。Worker 消息及安全正文规则遵循[子代理消息可见性](../delegation/delegation-child-message-visibility_zh_cn.md)。

| 预设 | Root 出站可见副本 | Root 入站可见副本 |
| --- | --- | --- |
| `economy` | 最多 3 项的 preview：目标、允许改动、返回条件。 | 与决策相关的摘要。 |
| `balanced` | 仅在下述确定触发条件时展示完整相关安全消息；否则使用 `economy` preview。 | 仅在下述确定触发条件时展示完整相关安全消息；否则使用 `economy` 摘要。 |
| `full` | 完整安全消息正文。 | 完整安全消息正文。 |

对 `economy`/`balanced` preview，按实际展示的 Markdown 源文本计数，包括空白、链接文字和链接目标：最多 3 项、600 个 Unicode 码位。入站摘要对应上限为 5 项、800 个 Unicode 码位；字段依次为结论、证据指针、关键依据、风险/阻塞、下一步，无值时省略。按字符而非 token 计数，无需逐条消息调用计数工具。完整正文须单独保持可用。若更高优先级指令或重要授权/失败证据无法容纳，只允许必要超限并说明原因；不得静默截断或拆分副本规避预算。预算不限制全文展示或 Worker 可见性。摘要不得泄露私有推理。

`economy` 仍允许并要求必要的面向用户进度、授权、失败、验证、阶段验收和最终报告。这些报告不能替代完整实际正文或其审阅。

### `balanced` 全文展示触发条件

仅在出现可观察事件时展示完整相关安全消息：已批准的 Contract 目标、验收条件、路径或允许影响发生变化；明确授予或撤回授权；已执行检查失败或证据直接冲突/存在争议；或用户要求精确审计本次交换。完全在既有 Contract 内执行的新切片不构成触发条件。若无法确定是否触发，保留事实供 Root 判断。不得自动将所有消息升级为 `full`。

### Worker 日志可见性

`worker_log_visibility` 描述当前 Session 对完整安全 Worker 入站/出站会话记录的访问能力；它既不是 Root 收到的最终返回正文，也不是原始加密运行日志。`available` 必须有直接证据能定位完整记录；仅工具存在不足以证明。`unverified` 表示没有肯定的成功/失败证据，包括尚未检查。`unavailable` 必须有能力明确缺失、访问失败或等价负面证据。仅未创建 Worker 时可使用 `Not applicable`，并在证据字段记录原因。

首次需要 Worker 日志证据时检查一次；仅在出现新的实际访问/能力证据或失败时更新，不逐消息检查。任务明确依赖此日志证据时，不可用/未验证状态会阻塞该审计依赖。否则报告限制并继续；完整实际返回正文仍是硬要求。

### 摘要频率

Root 和 Worker 分别应用各自的频率。摘要回合边界和内容格式遵循[推理摘要可见性](reasoning-summary-visibility_zh_cn.md)。`full` 在每个已完成边界输出必需的安全摘要。`milestone_only` 在以下可观察事件时输出：

| 事件 | 输出条件 |
| --- | --- |
| 实质决策 | 新确认或变更的选择会改变下一切片执行方式或验收标准；常规读取或命令选择不算。 |
| 授权变化 | 明确授予或撤回某项允许影响的权限。 |
| 验证失败 | 已执行检查失败，或当前验收条件有直接失败证据。 |
| 阻塞 | 已授权的下一步因必需权限、能力或证据确实缺失而无法继续。 |
| 阶段验收 | Root 最终接受已声明的阶段证据并放行下一阶段；普通进度不算验收。 |

按“事件类别 + 相关决策/证据 epoch”去重。每个事实只输出一次，同一回合多个触发合并；只有相关事实或 epoch 实质变化才再次输出。不得按经过时间或重复活动推断实质性。`off` 仅抑制可选摘要；必需报告、证据、Control 更新、Progress Signal 和更高层周期更新仍然必需。任何频率都不允许披露私有推理。

## Codex CLI / ChatGPT Desktop 特别优化指令

目前没有该概念的厂商专用优化。仅使用当前 Session 实际可用的能力和证据遵循通用规范。

## Claude Code CLI / Claude Desktop 特别优化指令

目前没有该概念的厂商专用优化。仅使用当前 Session 实际可用的能力和证据遵循通用规范。

## 相关概念

- [Coding 子代理消息可见性](../delegation/delegation-child-message-visibility_zh_cn.md) — 应用安全消息可见性规则。
- [Coding Agent 推理摘要可见性](reasoning-summary-visibility_zh_cn.md) — 应用摘要边界和格式。
- [Coding 委派状态记录](../delegation/delegation-state-record_zh_cn.md) — 查找会话配置记录字段。

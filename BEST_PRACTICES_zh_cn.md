# Token I/O Decoupling Coding Flow 最佳实践

[English](BEST_PRACTICES.md) | [简体中文](BEST_PRACTICES_zh_cn.md)

本文档是可选的、非规范性指南，面向两类读者：负责安装 Skill 和配置宿主的维护者，以及在具体任务中使用 Coding Flow 的操作者。

规范行为应以 [`SKILL_zh_cn.md`](SKILL_zh_cn.md) 以及 Coding references [`references/shared-protocols_zh_cn.md`](references/shared-protocols_zh_cn.md) 和 [`references/coding-flow_zh_cn.md`](references/coding-flow_zh_cn.md) 为准。本指南只保留最短操作路径，不另行复制这些文件中的完整规则。

## 为什么使用这个 Flow？

当项目状态和结果物化是主要 Token 压力来源时，Coding Flow 可以带来以下条件性收益：

- 决策与执行职责保持清楚，实现在不打断每个机械步骤的情况下继续进行。
- 紧凑的 Semantic Contract 和有界 checkpoint 让操作者只需审查高价值决策，不必指挥每条命令。
- Context Firewall 让原始项目状态留在所属执行 Session，同时保留可恢复的明确决策。

当前 Coding Flow 已经部分实现了 LOOP 式的 closed feedback loop：Primary Output Agent 在里程碑、阻塞或高价值决策边界发送压缩反馈；Input-side Reasoning Agent 分析反馈，必要时修订 Semantic Contract，并下发下一阶段；Primary Output Agent 随后继续探索、实现、验证或修复。这样，多数微观工作循环可以在 Agents 之间闭合，用户可以站在循环之外，主要只在目标变化、重大取舍、需要权限审批或进行最终验收时介入；用户也可以与执行中的 Agent 保持隔离，与主 Agent 的日常交流通常不会打断 Primary Execution Session。这只是对 LOOP 的部分实现，并非完全自治：闭环依赖宿主持续调度和 Session 能力，并且必须在权限、安全、产品限制或需要用户判断的边界前停止。

这些是操作层面的可能收益，不是对缓存命中、成本、额度、延迟或模型质量的保证。

## 快速开始

### 一次性安装

运行 Coding Flow 所需的文件是 Skill 和对应 references：

- `SKILL.md` 与 `SKILL_zh_cn.md`；
- 成对的 `references/shared-protocols` 与 `references/coding-flow` 文件。

`BEST_PRACTICES*.md` 是面向人的可选部署指南。英文 canonical 文件与简体中文镜像应一起维护，但本指南不是运行时依赖。

### 添加全局 bootstrap

将一个语言版本放入 `~/.codex/AGENTS.md`。同层级存在 `~/.codex/AGENTS.override.md` 时，它优先于 `AGENTS.md`；请先确认当前生效的文件，不要保留相互冲突的 bootstrap。仓库和项目专属政策应放在各自的指令文件中。

持久指令使用中文时，可直接复制下面的 bootstrap：

```md
# token-io-decoupling Coding Flow 全局 bootstrap

开始任何 Coding 工作前：

1. 加载并遵循 ~/.agents/skills/token-io-decoupling/SKILL_zh_cn.md。
2. 选择 Coding Flow，只加载 references/shared-protocols_zh_cn.md 和
   references/coding-flow_zh_cn.md。
3. 将 SKILL_zh_cn.md 与这些 reference 作为 Flow、角色、模型 Profile 和执行
   边界的事实来源。若所需模型或参数不可用，遵循 Skill 的处理规则，不要静默替换。
```

英文文档保留英文 bootstrap。只复制与持久指令语言相符的版本。

### 修改后启动新的 run

Codex 会在 run 或 TUI Session 开始时构建适用的指令链。修改 `~/.codex/AGENTS.md`、当前生效的 override、Skill 文件或项目指令文件后，应启动新的 run 或 TUI Session；不要假设已有 Session 已自动采用变更。

关于指令发现与加载行为，请参阅官方 [AGENTS.md 配置文档](https://learn.chatgpt.com/docs/agent-configuration/agents-md)。

在新的 run 中执行一次小型、无破坏性的冒烟检查：

1. 确认已加载 `token-io-decoupling`。
2. 确认任务已路由到 Coding Flow，且只加载其 Coding references。
3. 确认当前模型 Profile 和 Session 行为来自 `SKILL_zh_cn.md`。
4. 在本仓库运行 `python3 scripts/check-multilingual-docs.py`，检查 `git diff --check`，并通过 `git status --short` 查看是否有意外文件。

如果检查失败，应先修复加载或优先级问题，再启动新的 run。不要把完整 Skill 粘贴进任务，也不要静默替换所需模型。

## 每次 Coding 任务怎么做

### 1. 写下最小 Semantic Contract

在实质性执行前，记录目标、约束、已批准的决策和验收条件。高价值决策变化时修改 Contract，不要反复重写完整背景。

```text
Goal：在不改变公开 API 的前提下增加 CSV 导出。
Constraints：保持 Python 3.11 支持和现有输出格式。
Decisions：复用现有 serializer；若涉及 schema 变更，先暂停确认。
Acceptance：定向测试通过，且只修改预期文件。
```

### 2. 保持角色清楚，并稳定执行上下文

Input-side Reasoning 负责目标、约束、架构、风险和验收；Primary Output 负责探索项目、物化已批准结果和机械验证。相关的探索、实现、诊断、测试和修复应复用 Primary Execution Session，除非存在具体的重建理由。

### 3. 只在高价值决策处设置边界

普通读取、局部编辑和直截了当的测试循环可以在执行 Session 内继续。只汇报里程碑、决策变化、阻塞或重大偏差，不要逐条转录命令。跨越公开 API、schema、兼容性、安全或其他难以逆转的边界前，使用简短 checkpoint 暂停；确认 Contract 仍然正确后再释放下一阶段。

决策需要证据时，只请求定向路径、短摘录、事实或验证结果。一个小证据足够时，不要转发完整 diff、日志或文件树。

### 4. 先验证，再做语义验收

执行侧负责 build、test、lint、格式化、类型检查、diff 审查和意外文件检查。决策侧负责语义验收：目标是否完成、Contract 是否实现、约束是否保持，以及验证暴露的风险是否可接受。

## 什么时候创建另一个 Session

| 情况 | 默认做法 |
| --- | --- |
| 当前 Code Agent 明确是 `gpt-5.6-luna`，且任务是普通 Coding | 使用 Single-Agent Luna Mode，默认保持一个 Session。 |
| 独立复核、写入目标不重叠的真实并行、上下文容量管理或明确隔离有具体价值 | 只为该有界目的创建另一个 Session。 |
| 当前 Agent 无法确认所需 Luna Profile | 遵循正常双 Session 映射，使用所需的独立 Luna Primary Output；若不可用，停止并报告阻塞。 |
| 理由只是仓库大、输出长或笼统的“任务复杂” | 不要仅因这一理由创建另一个 Session。 |

确切的模型和 Session 规则以 [`SKILL_zh_cn.md`](SKILL_zh_cn.md) 和 [`references/coding-flow_zh_cn.md`](references/coding-flow_zh_cn.md) 为准。

## 常见错误

- 把 Skill 或 Flow 的规范文本复制到 `AGENTS.md`、README 或任务 prompt，形成会漂移的第二套政策。
- 预加载无关 Flow reference，或在一次定向 Evidence-on-Demand 已足够时转发完整原始状态。
- 用一次无限制的实现指令跨越多个语义决策边界，却没有 checkpoint。
- 没有独立收益就创建同模型 Agent，或对重叠写入目标、有序决策运行并行工作。
- 修改指令后仍在过时 run 中继续，或把未经测量的缓存、成本、额度或延迟收益说成事实。

## References

- [`SKILL_zh_cn.md`](SKILL_zh_cn.md)：路由、角色、Profile 和执行边界。
- [`references/shared-protocols_zh_cn.md`](references/shared-protocols_zh_cn.md)：共享 Contract、dispatch、证据和汇报协议。
- [`references/coding-flow_zh_cn.md`](references/coding-flow_zh_cn.md)：Coding 角色、Session 映射、阶段和验证边界。
- [`MULTI_LINGUAL_zh_cn.md`](MULTI_LINGUAL_zh_cn.md)：本仓库的双语文档规则。

本指南只覆盖 Coding Flow。需要多模态路由时，请返回 [`SKILL_zh_cn.md`](SKILL_zh_cn.md) 并按其路由加载对应 reference，不要在这里重建 Multimodal 规则。

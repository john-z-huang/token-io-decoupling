# Token I/O Decoupling Coding Flow 最佳实践——当前 Codex 部署

[English](BEST_PRACTICES.md) | [简体中文](BEST_PRACTICES_zh_cn.md)

本文档是可选的、非规范性指南，专门说明**当前已验证的 Codex + OpenAI Coding 部署**如何安装和使用。它不是产品无关规范。规范性的 Coding 架构仍位于 Skill 与 Coding Core references；具体 Host/模型策略位于 Runtime 部署文件。

规范行为应加载 [`SKILL_zh_cn.md`](SKILL_zh_cn.md)，随后加载 Coding references [`references/shared-protocols_zh_cn.md`](references/shared-protocols_zh_cn.md)、[`references/coding-flow_zh_cn.md`](references/coding-flow_zh_cn.md)，以及通过 [`references/coding/runtime_zh_cn.md`](references/coding/runtime_zh_cn.md) 选择的 Runtime 文档。本指南只保留最短操作路径，不成为这些规则的第二份副本。

## 为什么使用这个 Flow？

当项目状态和结果物化是主要 Token 压力来源时，Coding Flow 可以带来以下条件性收益：

- 决策与执行职责保持清楚，实现在不打断每个机械步骤的情况下继续进行。
- 紧凑的 Semantic Contract 和有界 checkpoint 让操作者只需审查高价值决策，不必指挥每条命令。
- Context Firewall 让原始项目状态留在所属执行 Session，同时保留可恢复的明确决策。

当前 Coding Flow 已经部分实现 LOOP 式 closed feedback loop：独立 Primary Output Agent 在里程碑、阻塞或高价值决策边界发送压缩反馈；Input-side Reasoning Agent 分析反馈，必要时修订 Semantic Contract，并放行下一阶段。Single-Session Coding Mode 中，相同的阶段与决策边界仍作为逻辑执行纪律存在，但不会模拟父子消息。

这些是操作层面的可能收益，不是对缓存命中、成本、额度、延迟或模型质量的保证。

## 快速开始

### 一次性安装

应保留完整 Skill 安装，使按需加载能够访问被选中的 Core 与 Runtime references。当前 Coding 路径使用：

- `SKILL.md` 与 `SKILL_zh_cn.md`；
- `references/shared-protocols*` 与 `references/coding-flow*`；
- 所需的 `references/coding/*` 模块；
- `references/runtime/index*` 以及被选中的 Codex Host Adapter 与 OpenAI Model Profile。

`BEST_PRACTICES*.md` 只是面向人的可选部署指南，不是 Runtime 依赖。

### 添加 Codex 全局 bootstrap

本小节有意保持 Host-specific。将一个语言版本放入 `~/.codex/AGENTS.md`。同层级存在 `~/.codex/AGENTS.override.md` 时，它优先于 `AGENTS.md`；请先确认当前 active 文件，不要保留相互冲突的 bootstrap。仓库和项目专属政策应放在各自指令文件中。

持久指令使用中文时，可直接复制下面的 bootstrap：

```md
# token-io-decoupling Coding Flow 全局 bootstrap

开始任何 Coding 工作前：

1. 加载并遵循 ~/.agents/skills/token-io-decoupling/SKILL_zh_cn.md。
2. 选择 Coding Flow，加载 references/shared-protocols_zh_cn.md 与
   references/coding-flow_zh_cn.md，再按其要求加载 Coding 模块。
3. 通过 references/coding/runtime_zh_cn.md 解析 active Coding runtime，
   只使用为当前环境登记的 Host Adapter 与 Model Profile。
4. 所选 Profile 要求精确模型或 Runtime 参数时不得静默替换；
   按其 unavailable handling 规则处理。
```

英文文档保留英文 bootstrap。只复制与持久指令语言相符的版本。

### 修改后启动新的 run

当前 Codex Host Adapter 定义 run 生命周期和持久指令行为。修改 `~/.codex/AGENTS.md`、active override、Skill 文件或项目指令文件后，应启动新的 run 或 TUI Session；不要假设已有 Session 已自动采用变更。

Codex 指令发现与加载细节以其官方 AGENTS.md 配置文档为准。

在新的 run 中执行一次小型、无破坏性的 smoke check：

1. 确认已加载 `token-io-decoupling`。
2. 确认任务已路由到 Coding Flow，且未预加载无关 Multimodal references。
3. 确认 Coding Runtime 解析选择了注册表中的 Codex Host Adapter 与 OpenAI Model Profile，而不是从 Core 文档推导产品/模型策略。
4. 确认最终 Session 拓扑与当前模型身份及 Profile eligibility 一致。
5. 在本仓库运行 `python3 scripts/check-multilingual-docs.py`，检查 `git diff --check`，并通过 `git status --short` 查看是否有意外文件。

如果检查失败，应先修复加载、Runtime 选择或优先级问题，再启动新的 run。不要把完整 Skill 粘贴进任务，也不要静默替换所需模型。

## 每次 Coding 任务怎么做

### 1. 写下最小 Semantic Contract

在实质性执行前，记录目标、约束、已批准的决策和验收条件。高价值决策变化时修改 Contract，不要反复重写完整背景。

```text
Goal：在不改变公开 API 的前提下增加 CSV 导出。
Constraints：保持 Python 3.11 支持和现有输出格式。
Decisions：复用现有 serializer；若涉及 schema 变更，先暂停确认。
Acceptance：定向测试通过，且只修改预期文件。
```

### 2. 先解析 active runtime，再保持执行上下文稳定

Input-side Reasoning 负责目标、约束、架构、风险和验收；Primary Output 负责探索项目、物化已批准结果和机械验证。

当前已验证部署中，[`references/coding/runtime_zh_cn.md`](references/coding/runtime_zh_cn.md) 会选择 Codex Host Adapter 与 OpenAI Model Profile。相关工作优先复用由此建立的 Primary Execution Session，除非存在具体重建理由。

### 3. 只在高价值决策处设置边界

普通读取、局部编辑和直接的测试循环可以在执行 Session 内继续。只汇报里程碑、决策变化、阻塞或重大偏差，不要逐条转录命令。跨越公开 API、schema、兼容性、安全或其他难以逆转的边界前，使用简短 checkpoint 暂停；确认 Contract 仍然正确后再释放下一阶段。

决策需要证据时，只请求定向路径、短摘录、事实或验证结果。一个小证据足够时，不要转发完整 diff、日志或文件树。

### 4. 先验证，再做语义验收

执行侧负责 build、test、lint、格式化、类型检查、diff 审查和意外文件检查。决策侧负责语义验收：目标是否完成、Contract 是否实现、约束是否保持，以及验证暴露的风险是否可接受。

## 当前 OpenAI Profile 下什么时候创建另一个 Session

| 情况 | 默认做法 |
| --- | --- |
| 当前 Session 明确是 `gpt-5.6-luna`，能够满足所需 reasoning-effort 档位，且任务是普通 Coding | Profile 声明其具备双角色 eligibility；使用通用 Single-Session Coding Mode。 |
| fresh verification、写入目标不重叠的真正并行、上下文容量恢复或明确隔离有具体价值 | 只为该有界目的创建另一个 Session。 |
| 当前父 Session 按 OpenAI Profile 不具备 Primary Output eligibility | 使用正常双 Session 映射，由独立 `gpt-5.6-luna` Session 承担 Primary Output。 |
| 某个具体 high/xhigh Worker 已经反复失败或明确阻塞 | 使用 Profile 中严格收窄的 `reasoning_effort=max` escalation，条件允许时保留 handoff context。 |
| 所需 Luna 模型或 Runtime 参数无法满足 | 停止对应实质性工作并报告阻塞，不静默替换其他模型。 |
| 理由只是仓库大、输出长、build/test 或笼统的“任务复杂” | 不要仅因这一理由创建另一个 Session。 |

确切规则以 [`references/coding/runtime_zh_cn.md`](references/coding/runtime_zh_cn.md)、[`references/runtime/hosts/codex_zh_cn.md`](references/runtime/hosts/codex_zh_cn.md) 和 [`references/runtime/profiles/openai_zh_cn.md`](references/runtime/profiles/openai_zh_cn.md) 为准。

## 常见错误

- 把 Skill 或 Flow 的规范文本复制到 `AGENTS.md`、README 或任务 prompt，形成会漂移的第二套政策。
- 把 Codex/OpenAI 专属模型或参数决策重新写回 Runtime 无关的 Coding Core 文档。
- 把某个模型的一般 Coding 能力直接视为角色 eligibility，而不查 active Profile。
- 预加载无关 Flow 或 Runtime reference，或在定向 Evidence-on-Demand 已足够时转发完整原始状态。
- 用一次无限制的实现指令跨越多个语义决策边界，却没有 checkpoint。
- 没有独立收益就创建 same-runtime Agent，或对重叠写入目标、有序决策运行并行工作。
- 修改指令后仍在过时 run 中继续，或把未经测量的缓存、成本、额度或延迟收益说成事实。

## References

- [`SKILL_zh_cn.md`](SKILL_zh_cn.md)：路由与跨 Flow 边界。
- [`references/shared-protocols_zh_cn.md`](references/shared-protocols_zh_cn.md)：共享 Contract、dispatch、证据和反馈协议。
- [`references/coding-flow_zh_cn.md`](references/coding-flow_zh_cn.md)：稳定 Coding 模块加载入口。
- [`references/coding/session-model_zh_cn.md`](references/coding/session-model_zh_cn.md)：Runtime 无关角色与 Session 语义。
- [`references/coding/runtime_zh_cn.md`](references/coding/runtime_zh_cn.md)：Runtime Contract 与选择算法。
- [`references/runtime/index_zh_cn.md`](references/runtime/index_zh_cn.md)：已登记部署。
- [`references/runtime/hosts/codex_zh_cn.md`](references/runtime/hosts/codex_zh_cn.md)：当前 Codex Host Adapter。
- [`references/runtime/profiles/openai_zh_cn.md`](references/runtime/profiles/openai_zh_cn.md)：当前 OpenAI Coding Model Profile。
- [`MULTI_LINGUAL_zh_cn.md`](MULTI_LINGUAL_zh_cn.md)：本仓库双语文档规则。

本指南只覆盖当前 Codex Coding 部署。需要多模态路由时，请返回 [`SKILL_zh_cn.md`](SKILL_zh_cn.md) 并按其路由加载对应 Multimodal reference，不要在这里重建 Multimodal 规则。

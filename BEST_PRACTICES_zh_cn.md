# Coding Flow 最佳实践——当前 Codex 部署

[English](BEST_PRACTICES.md) | [简体中文](BEST_PRACTICES_zh_cn.md)

本文档是可选的、非规范性指南，说明当前已验证的 Codex + OpenAI Coding 部署如何安装和日常使用。它不是产品无关规范：规范行为属于 [`SKILL_zh_cn.md`](SKILL_zh_cn.md) 与 Coding references，具体 Host/模型策略属于 Runtime 部署文件。

最短的规范加载路径是 [`references/shared-protocols_zh_cn.md`](references/shared-protocols_zh_cn.md)、[`references/coding-flow_zh_cn.md`](references/coding-flow_zh_cn.md)，以及通过 [`references/coding/runtime_zh_cn.md`](references/coding/runtime_zh_cn.md) 选择的 Runtime 文档。本指南只保留操作步骤，不重复这些规则。

## 快速开始

### 一次性安装

将唯一的个人 Skill 源保存在 `~/.agents/skills/token-io-decoupling/`。安装内容应包括根 Skill 及中文镜像、shared/Coding references、Coding 模块、Runtime 注册表，以及已选择的 Codex Host Adapter 和 OpenAI Model Profile。`BEST_PRACTICES*.md` 只是面向人的可选指南，不是 Runtime 依赖。

各 Host Adapter 负责把这一个源映射到产品支持的发现机制。项目级 Skill 仍放在 Host 原生仓库目录中。

### 添加 Codex 全局 bootstrap

将一个语言版本放入 `~/.codex/AGENTS.md`。若存在 `~/.codex/AGENTS.override.md`，它优先于前者；请确认当前 active 文件并移除冲突的 bootstrap 副本。仓库和项目策略应放在各自的指令文件中。

持久指令使用中文时，复制下面的 bootstrap：

```md
# token-io-decoupling Coding Flow 全局 bootstrap

开始任何 Coding 工作前：

1. 加载并遵循 ~/.agents/skills/token-io-decoupling/SKILL_zh_cn.md。
2. 选择 Coding Flow，加载 references/shared-protocols_zh_cn.md 与
   references/coding-flow_zh_cn.md，再按其要求加载 Coding 模块。
3. 通过 references/coding/runtime_zh_cn.md 解析 active Coding runtime，
   只使用为当前环境登记的 Host Adapter 与 Model Profile。
4. 所选 Profile 要求精确模型或 Runtime 参数时不得静默替换；
   按其 unavailable-handling 规则处理。
5. 在实质性派发前，输入侧 Agent 必须定义问题、假设、决策问题、风险、
   验收标准以及阶段/checkpoint 计划。若缺少项目事实，先派发有界
   reconnaissance，再由输入侧综合证据并显式放行实现。不得派发未解决的
   “分析、选择、实现并验证”组合式指令。
6. 对非简单的正常双 Session 工作，每次只放行一个 Interaction Slice。
   使用自适应的非阻塞 Progress Signal 和阻塞式 Control Checkpoint；每次
   Control Checkpoint 后选择 Continue、Amend 或 Stop。
```

本文包含中文 bootstrap；持久指令使用英文时，请使用对应语言版本。

### 修改指令后启动新的 run

修改 `~/.codex/AGENTS.md`、其 override、Skill 文件或项目指令文件后，应启动新的 run 或 TUI Session；不要假设已有 Session 已采用变更。

在新的 run 中执行一次小型、无破坏性的 smoke check：

1. 确认已加载本 Skill，且任务路由到 Coding Flow。
2. 确认未预加载无关的 Multimodal reference。
3. 确认 Runtime 解析选择了登记的 Codex Host Adapter 与 OpenAI Model Profile。
4. 确认 Session 拓扑与当前模型身份及 Profile eligibility 一致。
5. 在本仓库运行 `python3 scripts/check-multilingual-docs.py`、`git diff --check` 和 `git status --short`。
6. 对非简单任务，确认存在简洁 Decision Brief；当缺少重大事实时，确认 reconnaissance 在实现前暂停，并且实现放行发生在输入侧综合证据之后。
7. 对非简单多 Session 任务，确认每个 Output Agent 都只有一个已授权 Interaction Slice；Progress Signal 不会造成不必要阻塞，并且下一个 slice 放行前，Control Checkpoint 已产生明确的 Continue/Amend/Stop 决定。

若检查失败，应先修复加载、Runtime 选择或优先级问题。不要把完整 Skill 粘贴进任务，也不要静默替换所需模型。

## 日常 Coding 循环

1. 从最小 Semantic Contract 开始；字段和更新规则见 [`references/shared-protocols_zh_cn.md`](references/shared-protocols_zh_cn.md)。
2. 对非简单工作形成简洁 Decision Brief，并把问题定义、决策问题、方案批准与放行 ownership 保留在输入侧。
3. 若缺少证据，先运行有界 reconnaissance，并在实现前暂停等待输入侧综合；随后按 [`SKILL_zh_cn.md`](SKILL_zh_cn.md) 与 [`references/coding-flow_zh_cn.md`](references/coding-flow_zh_cn.md) 进行路由和分阶段执行。
4. 对非简单的正常双 Session 工作，每次只放行一个 Interaction Slice；在 slice 内使用自适应 Progress Signal，在自然或重大边界使用阻塞式 Control Checkpoint，并在放行下一个 slice 前决定 Continue/Amend/Stop。
5. 将普通工作限制在已批准 slice 内；存在多个 Output Agent 时，遵循 [`references/coding/context-exchange_zh_cn.md`](references/coding/context-exchange_zh_cn.md) 的父级会合与 Context Exchange 指引。
6. 运行适当的机械检查，再把每项验收标准映射到压缩证据并根据 Contract 完成语义验收。Session ownership 细节以 [`references/coding/session-model_zh_cn.md`](references/coding/session-model_zh_cn.md) 为准。

该 Flow 提供操作结构，不保证缓存命中、成本、额度、延迟或模型质量。

## Runtime 专属决策

本指南不重复模型、effort、Session 拓扑、升级或 unavailable handling 策略。请通过 [`references/coding/runtime_zh_cn.md`](references/coding/runtime_zh_cn.md) 解析这些决策，再遵循登记的 [`Codex Host Adapter`](references/runtime/hosts/codex_zh_cn.md) 与 [`OpenAI Model Profile`](references/runtime/profiles/openai_zh_cn.md)。

## References

- [`SKILL_zh_cn.md`](SKILL_zh_cn.md)：Flow 路由与跨 Flow 边界。
- [`references/shared-protocols_zh_cn.md`](references/shared-protocols_zh_cn.md)：Contract、dispatch、证据和报告协议。
- [`references/coding-flow_zh_cn.md`](references/coding-flow_zh_cn.md)：Coding 模块加载器。
- [`references/coding/session-model_zh_cn.md`](references/coding/session-model_zh_cn.md)：Runtime 无关的角色与 Session 语义。
- [`references/coding/runtime_zh_cn.md`](references/coding/runtime_zh_cn.md)：Runtime Contract 与选择算法。
- [`references/runtime/index_zh_cn.md`](references/runtime/index_zh_cn.md)：已登记部署。
- [`references/runtime/hosts/codex_zh_cn.md`](references/runtime/hosts/codex_zh_cn.md)：当前 Codex Host Adapter。
- [`references/runtime/profiles/openai_zh_cn.md`](references/runtime/profiles/openai_zh_cn.md)：当前 OpenAI Coding Model Profile。
- [`MULTI_LINGUAL_zh_cn.md`](MULTI_LINGUAL_zh_cn.md)：双语文档规则。

本指南只覆盖 Coding Flow。需要 Multimodal 工作时，请返回 [`SKILL_zh_cn.md`](SKILL_zh_cn.md) 并加载其路由的 references。

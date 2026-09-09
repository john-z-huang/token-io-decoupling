# Token I/O Decoupling

[English](README.md) | [简体中文](README_zh_cn.md)

`token-io-decoupling` 是一个面向支持 Agent Skills 的 Agent 调度 Skill。它把高价值语义决策、高体量原始状态消费与输出物化分离，避免父级推理上下文持续吸收低决策密度的仓库状态或视觉世界状态。

本项目不是一套统一的多 Agent 拓扑，而是包含两条彼此独立的 Flow：

- **Coding Flow** 是当前主要维护方向。Input-side Reasoning 负责高价值决策；Primary Output 负责仓库探索、实现/物化、原始工具输出、调试和机械验证。Coding Core 现在与具体 Code Agent 产品及模型名称解耦；Coding Runtime Contract 会为当前部署选择 Host Adapter 与 Model Profile。
- **Multimodal Flow** 继续用于 Computer Use、Browser Use、视频、大量图片/截图、视觉设计及其他高体量视觉/时序状态。其现有架构继续作为独立按需 Flow 保留；当前 Multimodal 部署绑定从根 Skill 中隔离出来，而不是在缺少测试的情况下强行通用化。

## 架构

### Coding：职责、Runtime 与 Host 相互独立

```text
Coding Flow
    │
    ├─ Input-side Reasoning responsibility
    └─ Primary Output responsibility
              │
              ▼
      Coding Runtime Contract
              │
              ▼
        Runtime Registry
          ┌───────┴────────┐
          ▼                ▼
     Host Adapter      Model Profile
       "how"              "who"
          └───────┬────────┘
                  ▼
       concrete Sessions / models /
       execution parameters
```

这种拆分是有意设计的：

- **Core responsibilities** 定义谁负责决策、项目状态、物化、验证和上下文 ownership。
- **Host Adapter** 定义 Code Agent 产品如何创建/复用独立 Session、暴露模型/Runtime 参数、加载持久指令，以及映射 sandbox/filesystem capability。
- **Model Profile** 定义哪些具体 Runtime 可以承担各角色、不同任务的执行参数、定向升级策略，以及 unavailable handling。

某个模型“技术上能写代码”并不自动意味着它可以承担 Primary Output。角色 eligibility 属于部署策略，可以有意让高体量执行远离父级推理 Session。

### Single-Session 与正常双 Session Coding

Coding Core 不再包含模型专属的“single-agent”分支；具体拓扑由 active Runtime 推导：

- 当前 Session 明确同时具备两类 Coding 职责的 eligibility、能够满足所需运行参数，且不存在独立结构性拆分理由时，使用 **Single-Session Coding Mode**；
- 当前 Session 负责输入侧推理，但 active Profile 要求独立 Primary Output Runtime 时，使用**正常双 Session 模式**；
- 只有 fresh verification、真正并行、上下文容量恢复、明确隔离或 Profile 定义的定向 escalation 等具体收益，才创建额外 Session。

仓库规模、长输出、build/test 工作或笼统的“任务复杂”本身不是新建 Session 的理由。

## Coding Flow 机制

Coding Flow 保留本项目已反复迭代的架构，同时把具体 Runtime 绑定从 Core 文档移出：

- **Semantic Contract** 固化 `Goal`、`Constraints`、`Decisions` 与 `Acceptance`，而不重新编码完整上下文。
- **Context Firewall** 在 active Runtime 使用双 Session 时，把高体量项目状态留在独立 Primary Output Session。
- **Primary Execution Session Affinity** 对相关的探索、实现、诊断、测试和修复优先复用执行上下文。
- **Two-level planning** 把架构/产品判断留在输入侧，把局部执行规划留在输出侧。
- **Bounded Coding stages 与 Decision Checkpoints** 防止独立 Worker 未经父级审查跨越重要语义边界。
- **Context Exchange** 把可复用的多 Worker 状态外置到有界、带 ownership 控制的工作区文档，并优先使用文件系统 capability，避免父级重新生成中转文本。
- **Evidence-on-Demand** 只返回高价值决策所需证据，不重放完整 diff 或日志。
- **Coding Verification Boundary** 把高体量机械验证与语义验收分开。

## Multimodal Flow

Multimodal Flow 继续独立于 Coding。它负责 Primary Observation、Observation Firewall、Routine Interaction、Creative Visual Authoring、视觉/时序渐进式读取、精选视觉 checkpoint、Computer Use observe/act 行为、Semantic Checkpoint、视觉验证，以及窄 Multimodal → Coding handoff。

这些详细规则不再在根 `SKILL_zh_cn.md` 或本概览中重复。完整规则见 [`references/multimodal-flow_zh_cn.md`](references/multimodal-flow_zh_cn.md)；当前 OpenAI 部署绑定单独保存在 [`references/multimodal-openai-profile_zh_cn.md`](references/multimodal-openai-profile_zh_cn.md)。

这种隔离反映当前维护边界：Coding Runtime 可移植性是主要活跃方向；Multimodal 行为保持现状，不进行未经测试的跨产品重构。

## 当前已验证 Coding 部署

Runtime 注册表目前只有一组已验证组合：

- Host Adapter：[`references/runtime/hosts/codex_zh_cn.md`](references/runtime/hosts/codex_zh_cn.md)
- Model Profile：[`references/runtime/profiles/openai_zh_cn.md`](references/runtime/profiles/openai_zh_cn.md)

当前 OpenAI Coding Profile 保持已有行为：

- 输入侧推理：当前高级父模型/Session；
- Primary Output：`gpt-5.6-luna`；
- 当前 Session 能明确确认自身为 `gpt-5.6-luna`，并且所需 Runtime 参数可满足时，该 Session 具有双角色 eligibility，通用 Runtime 因此选择 Single-Session Coding Mode；
- 正常双 Session Primary Output 对一般实现、非平凡调试/重构和复杂验证/测试代码使用 `reasoning_effort=xhigh`；
- 有界辅助物化通常使用 `reasoning_effort=high`；
- 宿主支持的 `medium` 或更低档位只用于严格有界、低风险、易机械验证的任务；
- `reasoning_effort=max` 仅用于某个具体事项已经让现有 high/xhigh Worker 反复阻塞后的定向升级，并优先在替换前通过文件化 handoff 保留上下文。

如果所需模型或 Runtime 参数无法满足，Profile 会阻塞对应实质性工作，而不是静默替换成其他模型。

## 当前 Multimodal 部署

现有 Multimodal OpenAI 绑定继续保留，但不纳入 Coding Runtime 抽象：

- Decision Agent：当前高级父模型；
- Primary Observation Agent：`gpt-5.6-luna`，实质性高体量视觉/时序分析使用 `reasoning_effort=xhigh`；
- Optional Primary Output Agent：`gpt-5.6-luna`，实质性长输出使用 `reasoning_effort=xhigh`。

即使部署把 Observation 与 Output 绑定到同一模型，它们仍然是不同的上下文 owner。

## 场景路由

仓库探索、实现、重构、调试、build/test/lint，以及代码/配置/开发文档物化使用 Coding Flow。

连续 GUI Observation、大型视觉集合、视频/时序状态、设计对比或开放式视觉创作成为主要输入状态时使用 Multimodal Flow。

混合任务按当前阶段的 owner 选择 Flow，并且只交换窄 Handoff Contract；不要预加载两套完整 Flow，也不要跨边界重放完整原始状态。

## 文件与语言布局

英文是默认公开入口；简体中文文档统一使用 `_zh_cn` 后缀。

- `SKILL_zh_cn.md`：中文语义镜像与路由入口。
- `references/shared-protocols_zh_cn.md`：跨 Flow 共享调度协议。
- `references/coding-flow_zh_cn.md`：稳定 Coding 模块加载入口。
- `references/coding/session-model_zh_cn.md`：Runtime 无关的 Coding 角色与 Session 拓扑。
- `references/coding/runtime_zh_cn.md`：Coding Runtime Contract。
- `references/coding/execution-control_zh_cn.md`：阶段、checkpoint、验证与输出纪律。
- `references/coding/context-exchange_zh_cn.md`：文件化多 Agent 上下文传输与 ownership。
- `references/runtime/index_zh_cn.md`：具体 Coding 部署注册表。
- `references/runtime/hosts/codex_zh_cn.md`：当前 Codex Host Adapter。
- `references/runtime/profiles/openai_zh_cn.md`：当前 OpenAI Coding Model Profile。
- `references/multimodal-flow_zh_cn.md`：完整 Multimodal 行为。
- `references/multimodal-openai-profile_zh_cn.md`：保留的当前 Multimodal OpenAI 部署绑定。
- [`BEST_PRACTICES_zh_cn.md`](BEST_PRACTICES_zh_cn.md)：可选的当前 Coding 部署安装与使用指南。
- `agents/openai.yaml`：OpenAI Agent Skill 展示与隐式调用配置。

`references/` 下每个英文 reference 都有对应的 `_zh_cn.md` 简体中文语义镜像。Skill 按场景与 Runtime 选择延迟加载 reference。

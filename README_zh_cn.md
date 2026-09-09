# Token I/O Decoupling

[English](README.md) | [简体中文](README_zh_cn.md)

`token-io-decoupling` 是一个面向支持 Agent Skills 的 Agent 调度 Skill。它把高价值语义决策、高体量原始状态消费与输出物化分离，避免父级推理上下文持续吸收低决策密度的仓库状态或视觉世界状态。

本项目不是一套统一的多 Agent 拓扑，而是包含两条彼此独立的 Flow：

- **Coding Flow** 是当前主要维护方向。Input-side Reasoning 负责高价值决策；Primary Output 负责仓库探索、实现/物化、原始工具输出、调试和机械验证。Coding Core 与具体 Code Agent 产品及模型名称解耦；Coding Runtime Contract 会为当前部署选择 Host Adapter 与 Model Profile。
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

Coding Core 不包含任何产品或模型专属的“single-agent”分支；具体拓扑由 active Runtime 推导：

- 当前 Session 明确同时具备两类 Coding 职责的 eligibility、能够满足所需运行参数，且不存在独立结构性拆分理由时，使用 **Single-Session Coding Mode**；
- 当前 Session 负责输入侧推理，但 active Profile 要求独立 Primary Output Runtime 时，使用**正常双 Session 模式**；
- 只有 fresh verification、真正并行、model tiering、上下文容量恢复、明确隔离或 Profile 定义的定向 escalation 等具体收益，才创建额外 Session。

仓库规模、长输出、build/test 工作或笼统的“任务复杂”本身，不是再创建一个实质 Primary Output Session 的理由。

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

## 已登记 Coding 部署

Runtime 注册表目前包含三组彼此独立的 Host/Profile 组合。

本地个人安装如果需要跨多个 Code Agent 复用，统一把唯一 Skill 源保存在 `~/.agents/skills/token-io-decoupling/`。各 Host Adapter 只负责把这个共享源映射到各产品真实支持的发现机制，不再为每个产品维护一份可变副本。项目级 Skill 仍保留各 Host 的仓库原生目录，因为其作用域和版本控制生命周期不同。

### Codex + OpenAI

- Host Adapter：[`references/runtime/hosts/codex_zh_cn.md`](references/runtime/hosts/codex_zh_cn.md)
- Model Profile：[`references/runtime/profiles/openai_zh_cn.md`](references/runtime/profiles/openai_zh_cn.md)
- 状态：当前已验证部署。

OpenAI Coding Profile 继续把 Primary Output 绑定到 `gpt-5.6-luna`；当前 Session 本身就是符合要求的同一 Runtime 时使用通用 Single-Session Coding Mode。实质 Primary Output 使用 `xhigh`，有界辅助物化使用 `high`，更低档位只用于严格机械工作，`max` 只用于现有 Worker 反复阻塞后的定向 escalation。

### Claude Code + Anthropic API

- Host Adapter：[`references/runtime/hosts/claude-code_zh_cn.md`](references/runtime/hosts/claude-code_zh_cn.md)
- Model Profile：[`references/runtime/profiles/anthropic_zh_cn.md`](references/runtime/profiles/anthropic_zh_cn.md)
- 状态：已经按当前 Claude Code 官方 capability 完成映射；用于本次改动的环境没有安装 `claude` CLI，因此尚未做真实 CLI smoke test。

Anthropic Coding Profile 现在使用**双模型执行层**，不再把所有输出任务都默认交给 Sonnet：

- Input-side Reasoning 继续由当前高级 Claude 父 Session 负责。
- **实质 Primary Output** 绑定到明确的 `claude-sonnet-5`，用于一般 feature implementation、非平凡 debugging/refactor、跨模块工作、复杂测试、migration、兼容性/安全敏感修改，以及其他需要较多实现判断的执行。
- **轻量 Output / 辅助 Worker** 优先使用明确的 `claude-haiku-4-5-20251001`，用于有界 repo exploration、事实 inventory、机械验证/日志压缩、精确提取/替换、确定性格式整理、语义已经固定的文档/注释同步，以及已经明确行为的简单单元测试物化。
- 路由规则是 **先选模型层，再选 effort**：真正低风险、有界的任务先下放 Haiku，而不是先在 Sonnet 上降 effort 省成本。

当前主 Session 本身明确是 `claude-sonnet-5` 且所需 Sonnet effort 能真实应用时，通用 Runtime 仍对实质 Primary Output 选择 Single-Session Coding Mode。这并不禁止存在明确 model-tiering 收益时创建 Haiku 辅助 Worker；Sonnet Session 仍然是 Primary Execution Session。

Sonnet 5 的常规实质 Primary Output 使用 `effort=xhigh`；任务仍需要 Sonnet 级判断但范围更窄时使用 `high`；`max` 只用于某个具体事项已经让现有 Worker 反复阻塞后的定向 escalation。`medium`/`low` 不再是那些本来可以安全交给 Haiku 的任务的默认降本方式。

Haiku 4.5 **不继承** Sonnet effort 策略。当前 Claude Code effort 支持列表不包含 Haiku 4.5，因此 Haiku 通过严格任务 eligibility 与准确模型选择控制成本/能力，而不是虚构 `high`/`xhigh`/`max` 档位。任务如果需要明显超过 Haiku 层能够安全提供的推理，应 reroute 到 Sonnet。

Claude Code 可能因为 organization `availableModels`、provider 限制、配置的 fallback chain 或 runtime availability substitute/fail over subagent model；组织级 effort cap 也可能把 Sonnet effort 向下 clamp。这些 Host 行为**不是** Profile fallback。Host 能暴露实际 subagent runtime 时必须检查真实 model/effort；不匹配时应作为显式 capability/rerouting 决策处理，而不是静默接受。

one-shot 只读调查在“不要求保证 Haiku 成本层”时仍可使用 built-in Explore。当前 Claude Code 版本中的 built-in Explore 会继承主会话模型，因此如果部署要求低成本 exploration，必须使用显式 Haiku 的 custom `Explore` 定义或其他明确 Haiku subagent。需要连续上下文的重复轻量工作使用可 resume 的 custom/general-purpose Haiku subagent；正常双 Session 模式下的 sticky 实质 Primary Execution Session 继续使用可 resume 的 Sonnet custom/general-purpose subagent。

### Claude Code 安装说明

canonical 个人 Skill 保存在 `~/.agents/skills/token-io-decoupling/`。Claude Code 的原生个人发现入口使用 symlink 即可，不需要复制副本：

```bash
mkdir -p ~/.claude/skills
ln -s ~/.agents/skills/token-io-decoupling ~/.claude/skills/token-io-decoupling
```

项目级 Skill 仍放在 `.claude/skills/`。如果需要持久启动提示，只在 `~/.claude/CLAUDE.md` 或项目 `CLAUDE.md` 中保留简短 bootstrap 并指向本 Skill；不要把完整 Skill policy 复制进去。Claude Code cloud session 不读取本机共享 Skill 目录，因此应使用 cloud session 实际会加载的项目/synced 部署方式。

### Qwen Code + Alibaba Qwen

- Host Adapter：[`references/runtime/hosts/qwen-code_zh_cn.md`](references/runtime/hosts/qwen-code_zh_cn.md)
- Model Profile：[`references/runtime/profiles/alibaba-qwen_zh_cn.md`](references/runtime/profiles/alibaba-qwen_zh_cn.md)
- 状态：已经按当前 Qwen Code 与 Alibaba Cloud Model Studio 官方 capability 完成映射；这套部署尚未完成真实 Qwen Code CLI 的 Max-parent/Flash-subagent smoke test。

Alibaba Qwen Coding Profile 有意采用成本非对称组合：

- **Input-side Reasoning** 绑定 `qwen3.8-max`。
- **Primary Output** 绑定 `qwen3.8-flash`，并继续作为仓库探索、实现、调试、build/test loop 和机械验证的 sticky execution owner。
- 正常双 Session 模式使用 Max 父 Session + 可持续复用的 regular Flash subagent。当前 Session 本身明确为 `qwen3.8-flash` 时，通用 Runtime 可以使用 Single-Session Coding Mode，而不是只为了保持形式上的 Max/Flash 拓扑再创建一个 Flash Agent。

Qwen3.8 在本部署中当前有三个实际有效原生 reasoning 档位：`low`、`medium`、`xhigh`。Profile 在 Max 父级处理实质语义决策时使用 `xhigh`；普通 Flash Primary Output 默认使用 `medium`；只有某个有界 Flash stage 确实需要更强局部实现判断时才升到 `xhigh`；`low` 仅用于严格机械工作。通用的 `high`/`max` 请求会映射为 Qwen3.8 `xhigh`，不把它们当成额外有效档位。

Qwen Code regular subagent 具有独立 context、显式模型选择、通过 `list_agents` + `send_message` 的后台 continuation，并可通过 `working_dir` 绑定已有 git worktree。不过模型选择和 effort 是两个不同控制面：subagent 定义可以直接绑定 Flash，而 effective effort 可能依赖 Session/provider 配置。因此 Host Adapter 把准确模型绑定作为硬约束；Qwen Code 无法确认某个 per-subagent effort 档位时，不会假装该档位已经生效。

Qwen Code 可以直接扫描共享个人源：把 `~/.agents/skills` 加入 `skills.directories`，而不是再复制一份到 `~/.qwen/skills/`。其默认个人/项目目录仍然存在，并且同名 Skill 会优先使用默认目录，因此共享源作为事实来源时应移除旧的同名副本。项目级 Skill 仍放在 `.qwen/skills/`。持久指令继续使用 `QWEN.md`，Qwen Code 也会读取已有 `AGENTS.md`。

## Multimodal Flow

Multimodal Flow 继续独立于 Coding。它负责 Primary Observation、Observation Firewall、Routine Interaction、Creative Visual Authoring、视觉/时序渐进式读取、精选视觉 checkpoint、Computer Use observe/act 行为、Semantic Checkpoint、视觉验证，以及窄 Multimodal → Coding handoff。

这些详细规则不再在根 `SKILL_zh_cn.md` 或本概览中重复。完整规则见 [`references/multimodal-flow_zh_cn.md`](references/multimodal-flow_zh_cn.md)；当前 OpenAI 部署绑定单独保存在 [`references/multimodal-openai-profile_zh_cn.md`](references/multimodal-openai-profile_zh_cn.md)。

上面的 Claude Code/Anthropic 与 Qwen Code/Alibaba Qwen Runtime **只适用于 Coding Flow**，不构成对应 Multimodal 支持声明。

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
- `references/runtime/hosts/codex_zh_cn.md`：Codex Host Adapter。
- `references/runtime/hosts/claude-code_zh_cn.md`：Claude Code Host Adapter。
- `references/runtime/hosts/qwen-code_zh_cn.md`：Qwen Code Host Adapter。
- `references/runtime/profiles/openai_zh_cn.md`：OpenAI Coding Model Profile。
- `references/runtime/profiles/anthropic_zh_cn.md`：Claude Code 已登记部署使用的 Anthropic Coding Model Profile。
- `references/runtime/profiles/alibaba-qwen_zh_cn.md`：Qwen Code 已登记部署使用的 Alibaba Qwen Coding Model Profile。
- `references/multimodal-flow_zh_cn.md`：完整 Multimodal 行为。
- `references/multimodal-openai-profile_zh_cn.md`：保留的当前 Multimodal OpenAI 部署绑定。
- [`BEST_PRACTICES_zh_cn.md`](BEST_PRACTICES_zh_cn.md)：可选的 Codex/OpenAI Coding 部署安装与使用指南。
- `agents/openai.yaml`：OpenAI Agent Skill 展示与隐式调用配置。

`references/` 下每个英文 reference 都有对应的 `_zh_cn.md` 简体中文语义镜像。Skill 按场景与 Runtime 选择延迟加载 reference。

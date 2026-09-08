---
name: token-io-decoupling
description: "高体量 Agent Token I/O 解耦：Coding 场景保持输入侧高价值推理与 Primary 输出双角色职责，并在当前 Code Agent 已是 Luna 时默认单 Session 自执行；Browser Use、Computer Use、浏览器/桌面 GUI 连续操作、视频、大量图片/截图和视觉设计场景使用独立 Multimodal Flow，由 Decision Agent 与 Primary Observation Agent 隔离高体量视觉/时序 Input Token；开放式绘画、图像编辑与视觉创作采用 Decision-led Visual Authoring，并按需 handoff 到输出或 Coding 流程。"
---

# Token I/O Decoupling

[English](SKILL.md) | [简体中文](SKILL_zh_cn.md)

本 Skill 定义两套按场景选择的 Agent 调度流程，用于把高价值语义决策与高体量原始状态消费、输出物化分离。Coding 与 Multimodal 的执行架构差异较大，因此只共享少量调度协议，不强行使用统一角色拓扑。

本 Skill 提供调度约定，不能绕过更高优先级的权限、用户授权、产品限制或安全规则，也不把价格、缓存命中或额度节省表述为未经实测的事实。

## 核心原则

1. **先选 Flow，再加载细则**：不要启动时无条件加载所有 reference。
2. **Coding 保持简单**：普通 Coding 保持“输入侧推理 → Primary 输出”的双角色职责；角色分离不等于 Agent / Session 分离。当前 Code Agent 已明确是 Luna 时默认在当前 Session 内同时承担两类职责，不为保持双角色形式创建额外 Luna。
3. **Multimodal 隔离高体量 Observation**：Computer Use、视频、大量图片/截图、视觉设计等任务由 Primary Observation Agent 消费视觉/时序世界状态，Decision Agent 只接收压缩 Digest；开放式视觉创作另遵循 Decision-led Visual Authoring 的精选证据回路。
4. **混合任务使用窄 Handoff**：视觉分析与 Coding 之间只传递稳定目标、必要变更、约束、证据引用和验收标准，不跨 Flow 倾倒完整原始状态。
5. **角色按职责映射到模型与 Session**：角色首先表示职责和上下文边界，不要求一对一对应独立 Agent 实例。只有模型分层、独立上下文 ownership、并行、独立验证或容量管理存在实际收益时才分离 Session；Multimodal 中 Observation 与 Output 即使都使用 Luna，也可因高体量上下文 ownership 不同而保持独立。

## Scenario Routing

### Coding Flow

以下任务默认进入 Coding Flow：

- repo / project exploration；
- implementation、refactor、bug fix、debugging；
- 代码、配置或开发文档物化；
- build、test、lint、formatter、type check、diff / log 分析；
- 其他以项目文本状态和大体量输出为主要 Token 压力的开发任务。

选择后加载：

1. [`references/shared-protocols_zh_cn.md`](references/shared-protocols_zh_cn.md)
2. [`references/coding-flow_zh_cn.md`](references/coding-flow_zh_cn.md)

普通 Coding 任务不得仅因为本 Skill 支持 Multimodal Flow 而加载 `multimodal-flow_zh_cn.md` 或创建 Primary Observation Agent。

### Multimodal Flow

以下任务默认进入 Multimodal Flow：

- Computer Use、浏览器/桌面 GUI 的连续 observe/act 工作流；
- 大量图片、截图、设计 reference 或 rendered UI 分析；
- 视频、大量视频帧或其他时序视觉输入；
- UI / visual design 对比与验收；
- 高体量 OCR、DOM、accessibility tree 或其他世界状态主要通过视觉/界面 Observation 获得的任务。

选择后加载：

1. [`references/shared-protocols_zh_cn.md`](references/shared-protocols_zh_cn.md)
2. [`references/multimodal-flow_zh_cn.md`](references/multimodal-flow_zh_cn.md)

进入 Multimodal Flow 后先区分两种工作模式：

- **Routine Interaction**：浏览、控件定位、表单填写、普通页面检查，以及目标和视觉结果已经明确的有界编辑。沿用 Primary Observation Agent 自主维持的低开销 observe/act 闭环。
- **Creative Visual Authoring**：绘画、插画、图像编辑、合成、排版、视觉设计、画布创作、风格化或任何需要决定构图、视觉层级、色彩/光线、材质或整体观感的开放式工作。必须使用 Decision-led Visual Authoring，让 Decision Agent 在关键视觉里程碑亲自审看精选证据并批准下一阶段。Creative 模式的主要视觉设计 ownership 属于 Decision Agent：构图、视觉层级、风格、色彩关系、整体观感及跨阶段方向选择不得下放给 Observation Agent；Observation Agent 只负责局部机械视觉判断与已批准方案的物化。

如果任务从 Routine Interaction 演变为需要改变核心构图、风格或视觉层级的开放式创作，应立即切换到 Creative Visual Authoring；不能继续让 Observation Agent 独立完成后续创作。Creative 模式的完整回路、精选证据边界和宿主能力阻塞规则见 `multimodal-flow_zh_cn.md`。

不要为了形式统一同时加载 Coding Flow。只有任务真实进入代码/repo 物化阶段时，才按 Multimodal → Coding 窄 Handoff 再加载 Coding Flow。

### 小型视觉输入例外

单张简单图片、少量严格有界截图或其他明显不会产生高体量 Observation 的输入，不必机械创建 Primary Observation Agent。是否使用 Multimodal Flow 取决于潜在原始输入体积、时序/交互状态复杂度与决策密度，而不是“任务里是否出现图片”这一单一条件；但这项输入规模例外不把开放式视觉创作降级为 Routine Interaction，创作仍须遵循 Creative Visual Authoring 回路。

### 混合任务与 Flow Handoff

不要在混合任务开始时预加载两套完整 Flow。按当前阶段的主要 Token 压力选择 Flow，并在职责真正变化时 handoff。

典型视觉设计驱动 Coding：

```text
Multimodal Flow
→ Primary Observation Agent 分析 reference / current UI
→ Visual / State Digest
→ Decision Agent 确认需要修改的语义目标
→ narrow Handoff Contract
→ Coding Flow
→ Primary Output Role 实现与机械验证
→ 必要时回到原 Multimodal Flow 做视觉验收
```

典型普通 Coding 后追加 UI 验证：

```text
Coding Flow
→ implementation / tests
→ 需要高体量视觉验收时再加载 Multimodal Flow
→ visual verification
```

Handoff 的字段和禁止携带的原始状态以 `multimodal-flow_zh_cn.md` 为准。

## Reference 加载规则

- 只加载当前场景需要的 Flow 文档和共享协议。
- 如果当前会话已加载且相关规则仍然有效，不重复读取同一 reference。
- 从一个 Flow 切换到另一个 Flow 时，只新增目标 Flow 所需 reference，不重新加载无变化的共享协议。
- 主 `SKILL_zh_cn.md` 是中文路由和 Profile 镜像，不替代 Flow 细则；实际执行前必须加载所选 Flow 的中文 reference。
- 当正确性需要跨 Flow 信息时使用窄 Handoff 或 Evidence-on-Demand，不通过一次性加载所有 reference 和原始状态来规避上下文边界。

## 当前 OpenAI Profile

模型绑定属于当前运行 Profile，不是 Token I/O Decoupling 架构本身。未来模型变化应优先调整本节，而不是改写 Flow 的角色边界。

### Coding Flow

启动 Coding Flow 时先确认当前 Code Agent 的模型身份，再映射职责到 Session：

- **当前 Agent 已明确是 `gpt-5.6-luna`**：进入 **Single-Agent Luna Mode**。当前 Session 同时承担 Input-side Reasoning Role 与 Primary Output Role，直接完成项目探索、实现、调试、机械验证和输出；不得仅为了双角色拓扑再创建或要求存在额外 Luna Primary Output Agent。由于该 Session 同时承担高价值推理职责，其常规物化工作保持 `reasoning_effort=xhigh`。
- **当前 Agent 不能明确确认自己是 `gpt-5.6-luna`**：按输入侧推理角色约束自身行为，并使用独立 `gpt-5.6-luna` 承担 Primary Output Role，保持正常双 Session Coding Flow。
- 正常双 Session Coding 中，独立 Primary Output Luna 默认使用 `reasoning_effort=xhigh`。一般需求开发、非平凡重构或调试、复杂测试/验证代码，以及其他需要较多实现判断的工作使用 `xhigh`；输出很长或项目规模很大本身不能作为继续提高强度的理由。
- 对主要工作是开发文档编写/修改、代码注释、简单单元测试、低风险机械性修改或其他有界辅助物化的任务，优先使用 `reasoning_effort=high`。额外的辅助性 Coding Worker 默认使用 `high`，除非其具体任务明确符合 `xhigh` 条件。
- 只有宿主明确支持对应档位，并且任务严格有界、语义风险低且容易机械验证时，才使用 `reasoning_effort=medium` 或更低强度。适合的例子包括：运行已经选定的 test/formatter/lint 并压缩结果、收集文件/路径元数据、精确搜索或提取、字面量替换、按明确模板做格式整理或更新生成表格。低于 `medium` 的档位原则上只用于只读工作或确定性的机械变换。不得把 Semantic Contract ownership、架构/产品判断、跨模块实现、复杂调试、复杂测试设计、公共 API/schema/权限变更交给这些轻量 Worker。
- `reasoning_effort=max` 是异常升级手段，不是普通 Worker 默认配置。只有某个具体事项已经由现有 `high`/`xhigh` Worker 反复失败、来回振荡或出现明确阻塞时，才使用 max。父 Agent 为该事项创建新的、范围严格收窄的 max Worker；条件允许时，原 Worker 先按照 `references/coding-flow_zh_cn.md` 定义的文件化 Context Exchange 机制，在 primary worktree 中写好可复用上下文与 handoff 文档，新 max Worker 读取这些内容后接手，而不是从零重新探索项目。阻塞解除后，后续无关工作恢复正常 `xhigh`/`high` 档位，不让 max 继续成为默认值。
- Single-Agent Luna Mode 只有在 fresh verification、真正并行、当前上下文明显失效/膨胀、存在明确独立隔离收益，或某个具体任务反复阻塞而需要定向 `max` 升级时才允许创建额外 Agent。项目探索、实现、测试、长输出或笼统的“任务复杂”本身不是例外理由。

### Multimodal Flow

- Decision Agent：当前高级父模型。
- Primary Observation Agent：`gpt-5.6-luna`；承担大规模图片、视频帧、Computer Use Observation 或其他实质性高体量分析时显式使用 `reasoning_effort=xhigh`。
- Optional Primary Output Agent：`gpt-5.6-luna`；长输出和其他实质性物化任务显式使用 `reasoning_effort=xhigh`。
- Observation Agent 与 Output Agent 是不同职责和不同 Session Affinity；即使当前 Profile 使用同一种模型，也不得因此把两者的高体量上下文默认合并。Single-Agent Luna Mode 只改变 Coding Flow 的默认角色映射，不削弱 Multimodal Flow 的独立 Observation ownership。

### Profile 约束

- 不得把要求使用 Luna 的角色静默替换为其他模型。
- 若需要独立 Luna 角色但无法确认 `gpt-5.6-luna` 身份、无法显式选择该模型，或宿主无法满足当前 dispatch 所要求的 reasoning-effort 档位，则停止对应实质性工作并简短报告阻塞。Multimodal 的实质性 Observation/物化仍按上文要求使用 `reasoning_effort=xhigh`。
- 纯只读、严格有界的诊断或观察，在能够确认 Luna 身份但宿主无法设置 reasoning effort 时可以继续；不得因此把复杂高体量工作回退给高级父模型，也不得把原本要求 `high` 或 `xhigh` 的任务静默降级给轻量强度。

## 加载边界

本 Skill 默认允许自动发现；普通 Skill 的 `description` 只影响隐式匹配，不能保证每次启动完整加载。若要保证特定宿主每次运行都遵循核心分工，应把必要不变量放入该宿主的持久指令机制，例如 Codex 的全局 `~/.codex/AGENTS.md`，或由宿主注入 system/developer instructions。

`references/` 中的 Flow 文档采用按需加载，禁止因为“可能以后会用到”而在任务开始时全部读取。

关于 Coding Flow 的部署、bootstrap、Session 重启、验证和采用建议，请参阅 [`BEST_PRACTICES_zh_cn.md`](BEST_PRACTICES_zh_cn.md)。该指南不替代本 Skill 及所选 reference 中的规范性 Flow、角色或 Profile 规则；Multimodal Flow 应按路由加载其自身的 reference。

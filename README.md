# Token I/O Decoupling

`token-io-decoupling` 是一个面向支持 Agent Skills 的 Agent 调度 Skill。它根据任务场景把高价值语义决策、高体量原始状态消费与大体量输出物化拆开处理，避免高级父模型被低决策密度的项目状态或视觉世界状态持续占用上下文。

当前 Skill 不使用一套统一的三 Agent 架构，而是提供两条独立流程：

- **Coding Flow**：保持成熟的双角色路径，由输入侧推理 Agent 负责高价值判断，Primary 输出 Agent 负责 repo exploration、代码/文档/配置物化、测试修复和机械验证。
- **Multimodal Flow**：用于 Computer Use、视频、大量图片/截图和视觉设计，由 Decision Agent 负责高价值判断，Primary Observation Agent 负责高体量视觉/时序 Input Token；只有确实需要长输出时才创建 Optional Primary Output Agent，需要修改代码时通过窄 Handoff 进入 Coding Flow。

Multimodal Flow 明确区分两种模式：Routine Interaction 保持 Observation Agent 自主的低开销 observe/act；Creative Visual Authoring（绘画、图像编辑、排版、视觉设计、插画、合成等开放式创作）采用 Decision-led Visual Authoring，由 Decision Agent 先制定 Creative Brief/Visual Plan，并在默认 3–6 个自适应视觉 checkpoint 亲自查看精选截图或局部证据、提出批评和 amendment 后，Observation Agent 才能继续下一阶段。Creative 模式的主要视觉设计 ownership 属于 Decision Agent，而不是 Observation Agent。

## 设计目标

- 普通 Coding 任务不因支持多模态而增加 Observation Agent 或额外调度层。
- 大型 diff、测试日志、文件树等项目原始状态继续由 Coding Primary Output Agent 消费并压缩。
- 连续截图、图片集合、视频帧、Computer Use Observation、OCR / DOM / accessibility state 等高体量多模态输入由 Primary Observation Agent 消费并压缩。
- Computer Use 的普通 observe/act 循环保持在 Observation Agent 的同一 Session 内，避免逐步跨 Agent 同步临时 GUI 状态。
- 普通 GUI 操作与开放式视觉创作分流：创作阶段以 bounded visual pass → curated checkpoint → Decision critique/amendment 为基本循环，避免 Observation Agent 闷头跨越多个视觉里程碑。
- Creative Visual Authoring 中，构图、视觉层级、风格、色彩关系、整体观感及跨阶段方向选择属于 Decision Agent 的高价值设计判断；Observation Agent 只做局部机械视觉判断、工具操作和已批准方案的物化，不得成为事实上的主要设计者。
- 大量图片与视频采用渐进式筛选，只对候选区域、图片、帧或时间段提高分析密度。
- 精选 checkpoint screenshot/crop 是 Observation Firewall 的窄例外；不传递连续截图、坐标、点击序列或完整视觉历史。宿主无法向 Decision Agent 提供精选图像时，Creative 模式必须停止并报告能力阻塞。
- 通过 Semantic Checkpoint 区分普通 GUI 操作与发送、提交、支付、删除、权限变更等高影响动作。
- 设计分析与 Coding 之间只传递窄 Handoff Contract，不把完整设计图、截图历史或 OCR 全文重新灌入 Coding Agent。
- 继续使用 Dispatch Preview、事件驱动汇报、Evidence-on-Demand 和缓存友好的增量通信控制父会话 Token 规模。

## 场景路由

```text
Token I/O Decoupling
        │
        ├── Coding Flow
        │     Input-side Reasoning Agent
        │               ↓
        │     Primary Output Agent
        │
        └── Multimodal Flow
              ┌─ Routine Interaction ───────────────┐
              │   Decision Agent                    │
              │          ↓                          │
              │   Observation observe/act loop      │
              │          ↓                          │
              │   Visual / State Digest             │
              └─────────────────────────────────────┘
              ┌─ Creative Visual Authoring ─────────┐
              │   Decision Agent: Brief / Plan      │
              │          ↓                          │
              │   bounded visual pass               │
              │          ↓                          │
              │   curated checkpoint screenshot     │
              │          ↓                          │
              │   Decision critique / amendment     │
              │          ↺ next approved pass       │
              └─────────────────────────────────────┘
                             ↓
                    optional Output / Coding Handoff
```

### Coding Flow

适用于 repo exploration、implementation、refactor、debugging、build/test/lint、代码/配置/开发文档物化等任务。

核心机制包括：Context Firewall、Primary Output Agent Session Affinity、Semantic Contract、两级规划、Coding Verification Boundary 与输入侧输出纪律。

### Multimodal Flow

适用于 Computer Use、连续 GUI Observation、大量图片/截图、视频或大量帧、视觉设计 reference 对比和其他高体量视觉世界状态。

核心机制包括：模式路由（Routine Interaction / Creative Visual Authoring）、Observation Firewall、Visual / Temporal Progressive Disclosure、Ephemeral State Ownership、Routine Computer Use Observe/Act Loop、Decision-led Visual Authoring、Semantic Checkpoint、Visual / State Digest 与 Multimodal Verification。

开放式创作时，Decision Agent 先产出构图、层级、色彩/光线、阶段和验收条件；Observation Agent 每次只执行一个有界视觉阶段，在结构、色彩/光照、细节和最终等 material milestone 返回精选截图或局部 crop；Decision Agent 必须亲自审看、批评并发 amendment 后才批准继续。默认 3–6 个 checkpoint，可按任务复杂度调整。宿主不能提供精选视觉证据时，不能退回由 Observation Agent 单独完成。这里的设计职责不是“Observation 先设计、Decision 再审批”：核心视觉方向由 Decision Agent 决定，Observation Agent 负责在 Photopea、Figma、Photoshop 等 GUI 工具中把已批准方向持续实现出来。

### 混合任务

例如“根据设计稿修改前端”时，先在 Multimodal Flow 中完成视觉分析，再把稳定目标、Required changes、Constraints、Evidence 引用和 Acceptance 压缩成窄 Handoff Contract，随后进入 Coding Flow。实现后若需要视觉验收，再复用原 Primary Observation Agent。

## 当前 OpenAI Profile

当前具体运行策略为：

- Coding 输入侧推理 Agent：当前高级父模型；
- Coding Primary Output Agent：`gpt-5.6-luna`，实质性物化任务使用 `reasoning_effort=xhigh`；
- Multimodal Decision Agent：当前高级父模型；
- Multimodal Primary Observation Agent：`gpt-5.6-luna`，实质性高体量视觉/时序分析使用 `reasoning_effort=xhigh`；
- Multimodal Optional Primary Output Agent：`gpt-5.6-luna`，实质性长输出使用 `reasoning_effort=xhigh`。

Observation 与 Output 是不同职责和不同 Session Affinity。即使当前 Profile 使用同一种模型，也不默认共享它们的高体量上下文。

该 Profile 是当前部署策略，不是架构本身。未来模型变化时，应优先调整模型绑定，而保持 Flow 的职责边界稳定。

## 文件

- `SKILL.md`：轻量入口，负责核心原则、场景路由、按需加载、混合任务 Handoff 和当前 OpenAI Profile。
- `references/shared-protocols.md`：两套 Flow 共享的 Semantic Contract 基线、Dispatch Preview、事件驱动反馈、Evidence-on-Demand、缓存稳定性与委派边界。
- `references/coding-flow.md`：Coding 双角色流程的完整运行规则。
- `references/multimodal-flow.md`：Computer Use、视频、图片和视觉设计场景的完整运行规则，包括 Routine Interaction 与 Creative Visual Authoring 的分流和协作回路。
- `agents/openai.yaml`：OpenAI Agent Skill 展示与隐式调用配置。

Skill 按场景延迟加载 reference；普通 Coding 不读取 Multimodal Flow，纯多模态分析也不预加载 Coding Flow。

## 开发流程

本项目的修改遵循 `dev-workflow-standards`：使用合规工作分支、中文提交与文档、开放 Issue 关联、通过 Pull Request 合并，并避免任何 Code Agent 署名或生成声明。

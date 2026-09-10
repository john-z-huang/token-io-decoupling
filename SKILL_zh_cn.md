---
name: token-io-decoupling
description: "高体量 Agent Token I/O 解耦：Coding 将输入侧高价值推理、实现输出、独立改动验证以及按需文档/注释物化分离，同时让 Core 的角色与 Session 规则保持对具体 Code Agent 产品和模型无关；具体 Runtime 绑定通过 Host Adapter 与 Model Profile 选择。Browser Use、Computer Use、连续 GUI 工作流、视频、大量图片/截图和视觉设计使用独立 Multimodal Flow 隔离高体量视觉/时序输入。"
---

# Token I/O Decoupling

[English](SKILL.md) | [简体中文](SKILL_zh_cn.md)

本 Skill 定义两套按场景选择的 Agent 调度流程，用于把高价值语义决策与高体量原始状态消费、输出物化分离。Coding 与 Multimodal 的执行架构差异较大，因此只共享少量调度协议，不强行使用统一角色拓扑。

本 Skill 提供调度约定，不能绕过更高优先级的权限、用户授权、产品限制或安全规则，也不把价格、缓存命中、额度节省或 Runtime 质量表述为未经实测的事实。

## 核心原则

1. **先选 Flow，再加载细则**：不要启动时无条件加载所有 reference。
2. **Coding Core 保持 Runtime 无关**：Coding 独立于具体产品或模型定义 Input-side Reasoning、Primary Output、按需 Change Verification 与 Documentation/Comments 职责、Session/context 规则、checkpoint 和验证边界；当前环境的 Runtime 映射由 Coding Runtime Contract、Host Adapter 与 Model Profile 共同解析。
3. **Multimodal 细节独立存放**：Computer Use、视频、大量图片/截图、视觉设计等任务使用独立 Multimodal Flow；其工作模式、视觉 checkpoint、Observation 规则和当前部署绑定全部放在按路由加载的 reference 中，不在根文件重复。
4. **混合任务使用窄 Handoff**：视觉分析与 Coding 之间只传递稳定目标、必要变更、约束、证据引用和验收标准，不跨 Flow 倾倒完整原始状态。
5. **角色首先表示职责**：角色表示责任和上下文 ownership，不要求一对一对应独立 Agent 实例。Coding 的 Session 拓扑由 active runtime 推导；Multimodal 保留自己的上下文 ownership 规则。

## Scenario Routing

### Coding Flow

以下任务默认进入 Coding Flow：

- repo / project exploration；
- implementation、refactor、bug fix、debugging；
- 代码、配置或开发文档物化；
- 对实质性功能改动及其周边行为进行独立验证；
- build、test、lint、formatter、type check、diff / log 分析；
- 其他以项目文本状态和大体量输出为主要 Token 压力的开发任务。

选择后加载：

1. [`references/shared-protocols_zh_cn.md`](references/shared-protocols_zh_cn.md)
2. [`references/coding-flow_zh_cn.md`](references/coding-flow_zh_cn.md)

随后按 `references/coding-flow_zh_cn.md` 中的模块加载表继续。不要预加载 `references/coding/` 或 `references/runtime/` 下全部文件，只加载当前职责、阶段与 active runtime 所需的 Coding 模块和部署文档。

普通 Coding 任务不得仅因为本 Skill 支持视觉工作而加载 Multimodal Flow 或创建 Primary Observation Agent。

### Multimodal Flow

连续 GUI Observation、大量图片/截图、视频或大量帧、视觉 reference 对比、高体量 OCR/DOM/accessibility state，或开放式视觉创作占主要 Token 压力时，进入 Multimodal Flow。

选择后加载：

1. [`references/shared-protocols_zh_cn.md`](references/shared-protocols_zh_cn.md)
2. [`references/multimodal-flow_zh_cn.md`](references/multimodal-flow_zh_cn.md)
3. 当前随仓库提供的部署绑定使用 [`references/multimodal-openai-profile_zh_cn.md`](references/multimodal-openai-profile_zh_cn.md)

`references/multimodal-flow_zh_cn.md` 独立负责 Routine Interaction 与 Creative Visual Authoring 的详细区分、Observation Firewall、视觉/时序渐进式读取、精选视觉 checkpoint、Computer Use 执行、Semantic Checkpoint 和视觉验证。不得在本根入口重新构造或摘要这些规则。

当前 Multimodal 部署 Profile 有意与 Coding Runtime 注册表分离；本 Skill 不在这里声称 Multimodal 绑定已经完成跨 Code Agent 产品的通用化或测试。

### 混合任务与 Flow Handoff

不要在混合任务开始时预加载两套完整 Flow。按当前阶段主要 Token 压力选择 Flow，并在职责真正变化时 handoff。

典型视觉设计驱动 Coding：

```text
Multimodal Flow
→ visual analysis / Visual-State Digest
→ Decision 确认稳定的必要变更
→ narrow Handoff Contract
→ Coding Flow
→ implementation / provisional focused checks
→ 需要时进行独立改动验证
→ 按需物化文档/注释
→ 必要时回到原 Multimodal Flow 做视觉验收
```

典型普通 Coding 后追加 UI 验证：

```text
Coding Flow
→ implementation / tests
→ 只有确实需要高体量视觉验收时再加载 Multimodal Flow
→ visual verification
```

准确 Handoff 字段和禁止携带的原始状态以 `references/multimodal-flow_zh_cn.md` 为准。

## Reference 加载规则

- 只加载当前场景需要的 Flow 文档、Coding 模块和 active runtime 文档。
- 如果当前会话已加载且相关规则仍然有效，不重复读取同一 reference。
- 从一个 Flow 切换到另一个 Flow 时，只新增所需 reference，不重新加载无变化的共享协议。
- 主 `SKILL_zh_cn.md` 是中文路由入口，不替代 Flow、Runtime 或部署细则。
- Coding 专属模块通过 [`references/coding-flow_zh_cn.md`](references/coding-flow_zh_cn.md) 加载；具体 Coding Host/Model 部署文件由 Runtime Contract 选择，不在 Core 规则中写死。
- 当正确性需要跨 Flow 信息时使用窄 Handoff 或 Evidence-on-Demand，不通过一次性加载全部 reference 和原始状态规避上下文边界。

## Runtime 边界

Coding 架构与具体部署策略有意分离：

```text
Coding Core responsibilities
        ↓
Coding Runtime Contract
        ↓
Host Adapter + Model Profile
        ↓
具体 Code Agent Sessions / models / parameters
```

Runtime Contract 通过 Coding Flow 加载，并只选择与当前环境匹配的已登记部署。产品专属持久指令路径、Agent/Session 操作、模型名称和执行参数值属于 Runtime 部署文件，不属于根 Skill 或 Coding Core 模块。

Multimodal Flow 当前不纳入这套 Coding Runtime 抽象；其现有部署绑定保存在自己的按需 Profile 中，不进行未经测试的可移植性重构。

## 加载边界

本 Skill 默认允许自动发现；普通 Skill `description` 只影响隐式匹配，不能保证每次启动都加载完整 Skill。若某个 Host 必须始终遵循特定不变量，应使用该 Host Adapter 定义的持久指令机制，或其他更高优先级、由宿主正式支持的指令通道。

`references/` 中的文档采用按需加载，禁止因为“可能以后会用到”而在任务开始时全部读取。

关于当前已验证 Coding 部署的 bootstrap、Session 重启、验证和采用建议，请参阅 [`BEST_PRACTICES_zh_cn.md`](BEST_PRACTICES_zh_cn.md)。该指南是非规范性说明，不能替代所选 Flow、Runtime Contract、Host Adapter 或 Model Profile。

# Multimodal Flow

本 Flow 用于 Computer Use、连续 GUI Observation、大量图片/截图、视频或大量视频帧、视觉设计分析、reference design 对比、高体量 OCR / DOM / accessibility state，以及其他以大量视觉或时序世界状态为主要 Input Token 来源的任务。

本 Flow 与 Coding Flow 独立。不要为了统一角色模型而把 Observation Agent 引入普通 Coding 任务，也不要把高体量视觉历史直接交给 Coding Flow。

所有角色同时遵循 [`shared-protocols.md`](shared-protocols.md)。

## 架构角色

### Decision Agent

负责高价值语义与风险判断：理解用户视觉/交互目标、定义业务与安全约束、决定分析重点、形成或修订 Semantic Contract、处理语义歧义与 Semantic Checkpoint、接收压缩后的视觉结论，并执行最终语义验收。

Decision Agent 不默认持续查看大量截图、逐帧分析视频、摄入 OCR/DOM 全文，也不参与 Computer Use 的每一步普通导航和视觉定位。

### Primary Observation Agent

负责高 Input Token 密度的世界状态消费与压缩，包括但不限于：

- screenshots、image collections、design references、rendered UI；
- video frames、关键帧和时序片段；
- Computer Use observations；
- OCR、DOM、accessibility tree 或其他高体量视觉/界面状态。

它负责筛选、去重、聚类、视觉理解、时序定位、局部 OCR、差异分析、focused inspection、证据选择和 ephemeral world-state tracking。

Primary Observation Agent 的默认输出不是长报告，而是低 Token、高信息密度的 Visual / State Digest。它可以在 Semantic Contract 授权范围内执行维持 Computer Use observe/act 闭环所需的普通低风险操作。

### Optional Primary Output Agent

只有 Multimodal 任务在视觉/时序分析之后仍需要大量非 Coding 物化时才创建，例如长报告、大体量结构化内容或其他长输出。

它只接收 Decision Agent 的 Semantic Contract、Observation Agent 的压缩 Digest 和必要的 Evidence-on-Demand 证据，不默认接收完整视觉历史。

如果后续工作属于 repo 修改、代码实现、调试或构建测试，则不要在 Multimodal Flow 内复制 Coding 执行规则；改用本文件定义的窄 Handoff 进入 [`coding-flow.md`](coding-flow.md)。

## Observation Firewall

以下原始状态默认只由 Primary Observation Agent 摄入，不持续进入 Decision Agent：

- 连续全屏截图和页面滚动过程中产生的截图；
- Computer Use observation history；
- 大批原始图片、设计 reference 或渲染结果；
- 全量视频帧或大规模时序切片；
- OCR 全文；
- DOM dump、accessibility tree、UI state dump；
- 为定位控件或验证视觉变化产生的重复中间证据。

Primary Observation Agent 只向 Decision Agent 返回做下一步高价值判断所需的状态、发现、风险、证据引用和待决问题。Decision Agent 需要确认具体视觉事实时，按 Evidence-on-Demand 请求最小必要证据，不重新摄入整个视觉集合。

判断依据是潜在原始 Observation 体积与决策密度，而不是输入介质名称本身。单张简单图片或严格有界的小型视觉状态若不会形成上下文倾倒，可由 Decision Agent 直接查看；不要为了形式统一机械创建 Observation Agent。

## Visual Progressive Disclosure

大量图片/截图默认采用渐进式读取，而不是一开始对所有输入做最高细节分析：

1. `Inventory`：确认数量、文件名/标识、尺寸、格式、时间顺序或其他低成本元数据；
2. `Screening`：用足够完成粗筛的最低合理细节判断相关性；
3. `Dedup / Group`：去除明显重复内容，并按场景、状态或视觉相似性分组；
4. `Candidate Selection`：挑出真正需要深入判断的候选图片；
5. `Focused Inspection`：只对候选输入提高细节；
6. `Local Evidence`：必要时使用 crop、局部放大、OCR 或其他定向方法获取最小证据。

具体缩略图、detail 级别、聚类算法或图像工具由 Primary Observation Agent 根据宿主能力决定，本 Skill 不固定实现方式。

禁止为了“完整分析”默认把整个大型图片集逐张高细节复述给 Decision Agent。

## Video / Temporal Progressive Disclosure

视频和大规模时序视觉输入默认采用类似的渐进式策略：

```text
video / frame stream
→ temporal sampling
→ scene / segment localization
→ key-frame selection
→ repeated-frame elimination
→ focused inspection
→ Temporal Digest
```

Primary Observation Agent 应先定位可能相关的时间段和关键变化，再对候选片段提高分析密度；除非任务本身要求逐帧检查且确有必要，不默认让每一帧进入高细节推理。

本 Skill 不规定固定帧率、采样间隔或场景分割算法。正确性需要更密集检查时优先提高局部相关时间段的分析密度，而不是无条件提升整个视频的帧消费量。

## Session Affinity 与 Ephemeral State Ownership

同一连续 Multimodal 工作流默认维持一个 Primary Observation Agent。其 Session Affinity 用于保留视觉/时序工作上下文、已筛选候选、页面导航历史以及当前 ephemeral world state，减少重复 Observation 和重复定位。

以下信息默认视为 ephemeral execution state，由 Primary Observation Agent 在自身上下文中维护：

- 屏幕坐标；
- 当前滚动位置；
- 动态页面布局；
- 弹窗、控件或临时 UI 状态；
- 当前窗口/页面/视频位置；
- 只对最新 Observation 有效的视觉定位信息。

这些状态不得作为长期 Semantic Contract 的核心内容，也不应周期性同步给 Decision Agent。

Decision Agent 描述语义目标，例如“打开账户安全设置并检查双重验证状态”；Primary Observation Agent 根据最新 Observation 自行决定当前页面中的具体坐标、控件定位和普通导航步骤。

Primary Observation Agent 同样 sticky but not immortal。上下文明显失效、视觉历史冲突严重、任务需要真正独立验证或隔离收益明确时，可以重建。

## Computer Use Observe / Act Loop

Computer Use 的普通执行闭环由 Primary Observation Agent 自己维持：

```text
observe
→ ordinary action
→ observe
→ ordinary action
→ observe
```

在已批准 Semantic Contract 范围内，滚动、普通导航、打开无副作用页面、定位控件、填写尚未提交的字段等低风险动作不需要逐步回到 Decision Agent。普通截图变化、元素定位和下一步执行计划留在 Observation Agent 自身上下文。

不要把闭环机械拆成：

```text
Observation Agent → Decision Agent → Output Agent → Observation Agent
```

否则会导致状态同步成本、视觉信息丢失和过期状态风险。

Primary Observation Agent 每次执行动作前仍须遵守宿主工具自身的确认、权限和安全要求；本 Skill 不覆盖这些更高优先级边界。

## Semantic Checkpoints

Computer Use 的升级边界按语义副作用判断，而不是按动作是否只是一次 click/type 判断。

典型 Semantic Checkpoint 包括但不限于：

- 发送外部消息或邮件；
- 提交、发布或公开内容；
- 支付、购买、转账或其他资金动作；
- 删除、合并、批准或其他难以撤销的操作；
- 权限、访问控制或账户安全设置变更；
- 创建或修改真实外部资源；
- 用户明确要求在执行前确认的动作。

若 Semantic Contract 已明确授权该具体副作用，且宿主工具不要求额外确认，Primary Observation Agent 可继续；否则必须在动作前暂停，把当前状态、预期影响和需要的决定极简升级给 Decision Agent。

不要因为“操作很简单”跳过语义边界，也不要因为存在 Semantic Checkpoint 规则而对每个普通导航动作请求批准。

## Visual / State Digest

Primary Observation Agent 的返回默认使用弹性、高密度摘要。可使用以下字段，但只写有信息价值的字段：

- `State`：当前页面、视觉集合或时序分析进度；
- `Findings`：对下一步决策有意义的发现；
- `Evidence`：必要的图片、帧、时间段或局部证据引用；
- `Issue`：异常、冲突或风险；
- `Need`：需要 Decision Agent 做出的决定。

示例：

```text
State: 已筛查 184 张截图
Findings: 7 张相关，其中 4 张出现同一登录跳转错误
Evidence: IMG_034, IMG_039, IMG_042, IMG_087
Issue: 错误仅发生于 OAuth redirect 后
```

```text
State: 已进入支付确认页
Finding: 地址和支付信息均已完成
Issue: 下一动作将提交真实订单
Need: 是否提交
```

禁止逐图片、逐帧、逐截图或逐操作复述整个观察历史。若父 Agent 只需要一个二元结论或少量事实，Digest 应进一步压缩。

## Multimodal Verification Boundary

Primary Observation Agent 负责高体量视觉/时序机械验证，例如：

- 页面是否到达目标状态；
- 目标控件是否出现、消失或进入预期状态；
- UI 是否存在明显布局破坏或与 reference 的关键差异；
- 图片处理结果是否满足明确视觉条件；
- 目标视频事件是否实际出现，以及相关时间段；
- Computer Use 操作后的最终状态是否符合 Contract 中可机械确认的要求。

Decision Agent 负责语义验收：视觉结果是否真正满足用户目标、业务或风险约束是否被破坏、剩余偏差是否可接受。

Decision Agent 不默认重新读取全部截图、设计稿或视频帧进行二次视觉检查。需要确认具体结论时使用 Evidence-on-Demand；高风险或独立审查价值明确时才创建 fresh verifier。

## Multimodal → Coding 窄 Handoff

当 Multimodal 分析结果需要代码、repo、配置修改或 Coding 验证时，结束当前视觉分析阶段，由 Decision Agent 形成窄 Handoff Contract，再进入 Coding Flow。

Handoff 只包含：

- `Goal`：需要通过 Coding 完成的目标；
- `Required changes`：已确认需要物化的变化；
- `Constraints`：兼容性、业务、安全或不得破坏的边界；
- `Evidence`：必要的设计 frame、截图、时间段等引用，不复制完整视觉内容；
- `Acceptance`：Coding 完成后需要满足的视觉/业务验收标准。

禁止在 Handoff 中传递完整图片集、全量视频帧、Computer Use Observation history、OCR 全文或 Primary Observation Agent 的完整分析历史。

典型设计场景：

```text
Multimodal Flow
→ visual comparison
→ Visual Digest
→ Decision
→ narrow Handoff Contract
→ Coding Flow
→ implementation / tests
→ Multimodal Flow visual verification
→ semantic acceptance
```

Coding 完成后若需要视觉验收，优先复用原 Primary Observation Agent；不要让 Coding Primary Output Agent 为验证视觉结果重新摄入整套原始 reference。

## Multimodal 内的 Optional Output Agent

若任务不涉及 Coding，但需要把已经确定的视觉/时序结论展开成长报告、大体量文档或其他长产物，可由 Decision Agent 创建 Optional Primary Output Agent。

该 Agent 只负责物化，不接管 Primary Observation Agent 的世界状态，也不重新分析整个视觉输入。它发现 Digest 或 Contract 不足以安全生成产物时，应请求 Decision Agent 定向补充，而不是自行要求全量视觉历史。
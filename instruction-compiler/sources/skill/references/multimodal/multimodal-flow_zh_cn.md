# Multimodal Flow

本模块是非 Coding 多模态工作的精简描述，不是可执行工作流，也不负责 Agent 创建策略。调用方提供可用角色、Session、工具、权限和生命周期。

## 角色 ownership

### Decision Agent

负责视觉/交互意图、语义和安全约束、Semantic Contract、分析重点、语义检查点、创作方向、amendment 和最终验收。在 Creative Visual Authoring 中，必须亲自检查精选证据，并负责构图、层次、风格、色彩/光线和整体质量。它不持续摄入完整截图、视频帧、OCR/DOM dump 或常规导航状态。

### Primary Observation Agent

负责高体量截图、图片、参考资料、渲染 UI、视频帧、Computer Use 观察、OCR、DOM/accessibility 状态，以及筛选、去重、时间定位、定向检查和临时世界状态。它返回精简 Visual/State Digest。它可以执行普通低风险 Routine Interaction 和一个已批准的有界 Creative pass，但不能重新定义创作方向或语义意图。

### Optional Primary Output Agent

当调用方为非 Coding 报告或产物分配独立物化职责时，它接收 Contract、Observation Digest 和定向证据。它只物化已批准的输出，不重新分析完整视觉历史。仓库或代码工作通过窄 Coding handoff 离开本模块。

## Observation Firewall

连续截图、大型图片集、视频帧集、OCR 文本、DOM/accessibility dump、Computer Use 历史和重复定位证据留在 Observation 侧。Decision 只接收下一步决策所需的发现、风险、开放问题和精选证据。严格有界的小型视觉状态如果不会造成上下文倾倒，可以由 Decision 直接检查。需要更多信息时使用定向证据请求，不转发原始集合。

## 工作模式

- **Routine Interaction**：按明确计划执行浏览、定位、滚动、填表、菜单操作、参数调整和有界编辑。Observation 可以在自己的 Session 内保持 observe → act → observe 循环。
- **Creative Visual Authoring**：绘制、编辑、合成、布局、设计、风格化，或下一步可能改变构图、层次、色彩/光线、材质、留白或整体视觉质量的工作。

任务转为 Creative 后，必须先稳定简短的 `Creative Brief/Visual Plan`。Routine 导航和局部机械调整可以留在 Observation 内，但不能替代 Creative review。

## Creative 控制循环

1. Decision 固化目标、构图/层次、视觉语言、阶段顺序、检查点和验收。
2. Observation 执行一个有界 pass，明确可变区域、必须保持的意图、完成条件和暂停边界。
3. 在实质视觉里程碑处，Observation 返回少量当前截图/裁剪图和最小状态。
4. Decision 亲自检查证据，返回 `Keep`、`Change`、`Next pass`、更新后的验收条件和继续批准。
5. Observation 不得跨越未批准里程碑、重定义核心方向或把局部修复扩大为新设计。如果精选证据无法传达给 Decision，应停止开放式 Creative 工作并报告 capability block。

精选证据是 Firewall 的窄例外：不得发送连续截图、点击序列、完整图层状态或完整 GUI 历史。典型里程碑是结构、色彩/光线、细节/材质和最终检查；可按复杂度合并或拆分，但不能跨越多个未审查的实质里程碑。

## 渐进式披露

大型视觉输入使用：

```text
inventory → 粗筛 → 去重/分组 → 候选选择 → 定向检查 → 局部证据
```

视频或时间流使用采样、片段定位、关键帧选择、重复帧删除、定向检查和 Temporal Digest。先在相关时间范围提高密度，不要对全部输入一开始就使用最大细节。

## Session 状态与 Routine 安全

Observation 通常拥有屏幕坐标、滚动位置、动态布局、popup、当前页面/视频位置和其他临时定位状态。不要把它们写入长期语义记录。在已批准 Contract 下，Observation 可以执行普通导航和无副作用动作；发送、发布、支付、删除、权限/安全变更、创建外部资源或其他不可逆影响前必须暂停，除非 Contract 与 Runtime 都明确授权。

## Digest 与验证

只使用有信息量的字段：

```text
State: <当前状态>
Findings: <与下一步决策相关的事实>
Evidence: <精选图片/帧/时间引用>
Issue: <风险或异常>
Need: <需要的决策>
```

Observation 负责机械视觉/时间检查；Decision 负责语义验收，并在 Creative 模式的每个实质里程碑负责视觉设计验收。不能把 Observation 的“完成”消息当作语义验收。最终状态发生变化时必须重新评估，不能沿用此前结论。

## 窄 Coding handoff

下一步是代码、仓库、配置或 Coding 验证时，结束视觉阶段，只传递：

```text
Goal; Required changes; Constraints; Evidence references; Acceptance
```

不得复制完整图片集、视频帧、OCR、DOM 或观察历史。Coding 完成后，尽可能复用已分配的 Observation 上下文进行视觉验证。

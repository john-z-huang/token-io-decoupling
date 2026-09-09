# 共享调度协议

本文件只定义 Coding Flow 与 Multimodal Flow 共同遵守的协议。场景角色、上下文防火墙、执行循环、Runtime 映射和验收边界由各自 Flow 文档定义；不要为了“统一架构”把某一 Flow 的专属角色或原始状态复制到另一 Flow。

## Semantic Contract 基线

Decision / Input-side Reasoning Agent 负责固化高价值决策信息。Contract 只包含执行方安全工作所需的最小稳定语义：

- `Goal`：最终目标；
- `Constraints`：不能破坏的业务、兼容性、安全或用户边界；
- `Decisions`：已批准的架构与关键取舍；
- `Acceptance`：验收标准。

Semantic Contract 是决策锚点，不是完整上下文或原始 Observation 的替代品。宿主能够安全共享的相关上下文可直接提供给对应 Primary Agent；后续默认只发送新增目标、决策变化和必要约束，不周期性重写完整背景。

Contract 更新优先使用 amendment。只有历史修订已冲突到无法判断当前有效状态时，才发送一次明确的 authoritative decision snapshot；必要时重建对应 Primary Agent。

若安全执行所需上下文既不在当前 Primary Agent 中、宿主又无法共享，而短 Contract 也不足以弥补，则停止并报告上下文阻塞；不要由高价值决策 Agent 用长篇输出重新编码整段历史来绕过限制。

## Role 与 Session 映射

Flow 中的 Decision、Input-side Reasoning、Primary Observation、Primary Output 等名称首先表示职责和上下文 ownership，不要求每个角色都映射为独立 Agent / Session。

创建额外 Session 必须有独立结构性收益，例如 Runtime capability 分层、不同高体量上下文 ownership、真正并行、fresh verification、上下文容量管理或明确隔离需求。不得仅为了角色命名、流程拓扑、长输出、普通项目探索、实现、测试或笼统的“任务复杂”而进行 same-runtime delegation。

当当前 Agent 已经满足目标角色的 active runtime 要求，且不存在上述独立收益时，默认复用当前 Session。Coding Flow 的具体 Single-Session 与正常双 Session 语义由 [`coding/session-model_zh_cn.md`](coding/session-model_zh_cn.md) 定义，并由 [`coding/runtime_zh_cn.md`](coding/runtime_zh_cn.md) 映射到具体部署。

这条规则不意味着所有同模型角色都必须合并。Multimodal Flow 中 Primary Observation 与 Optional Primary Output 即使某个部署使用同一模型，也可因视觉/时序原始状态与输出物化上下文具有不同 ownership 而保持独立 Session。

## Dispatch Preview

每次实际创建子 Agent 或向既有独立 Primary Agent 发送新的执行指令前，父会话必须先显示一条极简 `Dispatch` 预览，使用户能够知道本次具体派发了什么。它只是即将派发指令的可见摘要，不是完整子 Agent prompt，也不得暴露不可见内部推理。

当前 Session 在同一 Agent 内切换逻辑职责、执行自己的探索/实现/验证或维护 Semantic Contract 不属于 Dispatch。同 Session Coding 不得为了满足 Dispatch Preview 规则打印虚构 self-dispatch、构造 self-prompt 或创建无必要子 Agent。

预览只保留足以识别本次任务的最小信息：

- `Task`：一句话说明目标或增量目标；
- `Scope`：仅在必要时列出关键路径、模块、视觉集合或处理范围；
- `Constraints`：仅保留会直接改变执行方式的关键约束；
- `Runtime`：仅在本次需要显式模型、执行参数或类似 Runtime 要求时简写。

默认输出 **1–3 行**，以 **约 80 tokens 以内**为目标；如果明显接近或超过 **约 120 tokens**，必须继续压缩后再派发。不要为了格式机械补齐没有内容的字段，也不要输出完整验收清单、完整 Contract 或解释性长文。

复用独立 Primary Agent 时只显示本次新增 delta，不重复此前已经可见的派发内容。若宿主已在同一父会话中自动、清晰地显示等价任务摘要，可不重复打印；仅显示“已创建 Agent”“正在工作”等无任务语义的信息不算等价。

场景特例：

- Coding Flow：禁止在 Dispatch Preview 中展开逐文件、逐行、逐命令执行计划。
- Multimodal Flow：禁止枚举大批图片/帧、复制 OCR/DOM、输出 click sequence、屏幕坐标、完整视觉历史或逐帧计划。

推荐形式：

```text
Dispatch → Primary Output | Task: 修复认证中间件刷新逻辑；Scope: auth/*；Constraints: 保持 API 兼容
```

```text
Dispatch → Observation | Task: 对比 checkout 设计稿与当前 UI；Scope: checkout；Constraints: 先粗筛再定向检查
```

## 事件驱动进度反馈

独立 Primary Agent 不持续发送工作日志。普通文件读取、grep、截图变化、滚动、局部分析、编译错误修复、下一条命令等低决策密度步骤留在自身上下文。

只在以下事件主动向父 Agent 发送极简消息：

- 关键里程碑发生，例如实现完成、视觉筛选完成、开始验证；
- 出现需要高价值语义、架构或风险决策的问题；
- 发生阻塞、重大偏差或已批准 Contract 无法继续满足。

消息只包含父 Agent 下一步判断所需内容，可使用 `Status`、`Issue`、`Need` 等有意义字段；没有内容的字段不要机械补齐。不要附完整日志、diff、截图序列、OCR 全文或其他高体量原始状态。

任务完成时只返回压缩交付摘要：主要结果、机械/视觉验证结论、仍需关注的风险或边界变化。

同 Session 执行没有独立父子 Session，不要求模拟 Agent-to-parent 进度消息；当前 Agent 按宿主正常交互规则向用户报告必要进度即可。

## Evidence-on-Demand

高价值决策 Agent 默认不重新读取完整原始证据。需要确认某项结论时，向持有原始状态的独立 Primary Agent 提出定向问题，由后者返回最小必要证据、相关路径、图片/帧引用或小段事实。

如果高价值决策职责与 Primary 职责位于同一 Session，则直接定向检查当前上下文或工具状态，不为了 Evidence-on-Demand 创建 self-handoff。只有高风险任务或确有独立审查价值时，才创建 fresh verifier；不能把独立验证变成所有任务的固定开销。

## Cache-Aware Context Stability

同一工作流优先保持 `stable prefix + small delta`：稳定已有 Session、项目历史、视觉状态 ownership 和已批准决策，只在尾部追加新的目标、amendment 或验证要求。不要为了“同步状态”周期性重新总结整个任务，也不要反复生成高度重叠的 Contract 全文。

缓存友好性只是组织上下文的设计目标；实际缓存键、命中条件和额度折算由宿主决定，不得把缓存收益描述为保证结果。若稳定历史已妨碍正确理解当前状态，应优先正确性，执行一次状态压缩或重建 Agent。

## 委派边界

任何 Primary Observation Agent 或独立 Primary Output Agent 都不得递归委派。需要额外 Agent、独立 verifier 或跨 Flow handoff 时，由当前父级高价值决策 Agent 统一调度；同 Session Coding 需要触发例外 Agent 时，也由当前 Agent 直接创建，不先构造虚拟 Primary 层级。

本 Skill 不能绕过更高优先级的权限、用户授权、产品限制或安全规则。角色分工、Semantic Contract 或已建立 Session Affinity 都不构成额外授权。

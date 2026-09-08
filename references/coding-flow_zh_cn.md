# Coding Flow

本 Flow 用于项目探索、规划、实现、重构、修复、代码/配置/文档物化、构建测试与调试等 Coding 场景。它保留 `token-io-decoupling` 已有的 Input-side Reasoning 与 Primary Output 两类逻辑职责，但把具体 Coding 规则拆分到独立模块中，使互不相关的工作可以独立演进，避免反复修改同一个共享文件。

所有 Coding 角色同时遵循 [`shared-protocols_zh_cn.md`](shared-protocols_zh_cn.md)。

## 模块加载

`coding-flow_zh_cn.md` 是稳定的 Coding 入口。不要为了方便把各模块的具体策略重新复制回本文件。

选择 Coding Flow 后：

1. 加载 [`coding/session-model_zh_cn.md`](coding/session-model_zh_cn.md)，建立角色 ownership、Luna Single-Agent Mode、Context Firewall 与 Primary Execution Session Affinity。
2. 加载 [`coding/profile_zh_cn.md`](coding/profile_zh_cn.md)，把当前运行模型和 reasoning-effort 档位映射到这些职责。
3. 在进行实质性 implementation、refactor、debugging、build/test 或其他可能跨越语义决策边界的执行前，加载 [`coding/execution-control_zh_cn.md`](coding/execution-control_zh_cn.md)。
4. 当任务使用多个独立 Coding Agent、需要复用跨 Agent 上下文，或需要 Worker 替换/升级接力时，加载 [`coding/context-exchange_zh_cn.md`](coding/context-exchange_zh_cn.md)。

纯有界 exploration 可以在真正进入执行前暂缓加载 `execution-control_zh_cn.md`。从未创建额外 Coding Agent 的 Single-Agent Luna 任务，不必机械加载 `context-exchange_zh_cn.md`，除非确实需要文件化恢复或上下文传输。

如果某个 Coding 模块已经加载且规则仍有效，不重复读取。按职责加载需要的模块，不得默认预加载整个 `references/coding/` 目录。

## 规范 ownership 边界

每类 Coding 关注点只有一个主要 owner：

| 关注点 | 负责文档 |
|---|---|
| 角色、Session 拓扑、Context Firewall、Primary Execution Session | [`coding/session-model_zh_cn.md`](coding/session-model_zh_cn.md) |
| 模型绑定、`reasoning_effort`、定向 max 升级 | [`coding/profile_zh_cn.md`](coding/profile_zh_cn.md) |
| Semantic Contract 传输、文件化 Context Exchange、Worker handoff | [`coding/context-exchange_zh_cn.md`](coding/context-exchange_zh_cn.md) |
| 两级规划、有界阶段、Decision Checkpoint、验证、输出纪律 | [`coding/execution-control_zh_cn.md`](coding/execution-control_zh_cn.md) |

不得在 `SKILL_zh_cn.md`、本入口或另一个 Coding 模块中重复某模块的规范性规则；应改为引用 owner 文档。只有当 Coding 路由、模块 ownership 或跨模块加载条件变化时才修改本文件。

这套 ownership 同时也是多 git worktree 并行维护边界：模型/Profile 调整通常只改 `coding/profile_zh_cn.md`；Context Exchange 调整通常只改 `coding/context-exchange_zh_cn.md`；checkpoint/验证调整通常只改 `coding/execution-control_zh_cn.md`；Session 拓扑调整通常只改 `coding/session-model_zh_cn.md`。语义确实跨模块时可以同时修改，但不得仅为了重述其他模块策略而制造共享文件改动。

## 职责顺序

Coding 架构仍然由 Input-side Reasoning 负责高价值语义决策，Primary Output 负责高体量项目状态消费、物化与机械验证。逻辑角色不等于独立 Agent 实例；当前运行 Profile 决定这些职责是在同一 Session 内完成还是使用独立 Session。

详细角色与 Session 规则以 [`coding/session-model_zh_cn.md`](coding/session-model_zh_cn.md) 为规范来源，不得根据本摘要额外推导新的 Session 要求。

## 与 Multimodal Flow 的边界

普通 Coding 任务始终留在本 Flow。只有当任务确实需要消费连续 GUI Observation、大量图片/截图、视频帧、设计参考或其他高体量视觉世界状态时，才切换或先进入 Multimodal Flow。

如果 Multimodal Flow 已完成视觉分析并需要修改代码，Coding Flow 只接收其窄 Handoff Contract；不得为了实现代码而把完整图片集、视频帧、Computer Use 历史、OCR 全文或视觉分析历史重新灌入 Primary Execution Session。

Multimodal Flow 架构和运行规则继续由 [`multimodal-flow_zh_cn.md`](multimodal-flow_zh_cn.md) 独立负责；Coding 模块的修改不得静默重定义这些规则。

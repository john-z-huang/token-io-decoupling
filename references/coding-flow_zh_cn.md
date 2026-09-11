# Coding Flow

本 Flow 用于项目探索、规划、实现、重构、修复、代码/配置物化、构建测试、调试、独立改动验证、按需文档/注释物化，以及所有非简单仓库 Git 工作等 Coding 场景。它以 Input-side Reasoning 与 Primary Output 为基础逻辑职责，并按需增加 Change Verification 与 Documentation/Comments & Git Operations 角色，为文档和 Git 操作分别设置获准的 Interaction Slice；具体 Coding 规则拆分到独立模块，使互不相关的关注点可以独立演进，避免反复修改同一个共享文件。

所有 Coding 角色同时遵循 [`shared-protocols_zh_cn.md`](shared-protocols_zh_cn.md)。

## 模块加载

`coding-flow_zh_cn.md` 是稳定的 Coding 入口。不要为了方便把各模块的具体策略重新复制回本文件。

选择 Coding Flow 后：

1. 加载 [`coding/session-model_zh_cn.md`](coding/session-model_zh_cn.md)，建立角色 ownership、实现与按需 Worker 的通用 Session 语义、Context Firewall 与 Primary Execution Session Affinity。
2. 加载 [`coding/runtime_zh_cn.md`](coding/runtime_zh_cn.md)，解析 active Host Adapter 与 Model Profile，并把上述 Session 语义映射到当前环境。
3. 在进行实质性 implementation、refactor、debugging、build/test 或其他可能跨越语义决策边界的执行前，加载 [`coding/execution-control_zh_cn.md`](coding/execution-control_zh_cn.md)。
4. 当任务使用多个独立 Coding Agent、需要复用跨 Agent 上下文、需要 Worker 替换/升级接力，或需要父级多 Worker 会合与 slice 同步时，加载 [`coding/context-exchange_zh_cn.md`](coding/context-exchange_zh_cn.md)。

纯有界 exploration 可以在真正进入执行前暂缓加载 `execution-control_zh_cn.md`。从未创建额外 Coding Agent 的 Single-Session Coding 任务，不必机械加载 `context-exchange_zh_cn.md`，除非确实需要文件化恢复或上下文传输。

`runtime_zh_cn.md` 只加载当前环境匹配的已登记 Host Adapter 与 Model Profile，不预加载 `references/runtime/` 下所有文件。

如果某个 Coding 模块已经加载且规则仍有效，不重复读取。按职责加载需要的模块，不得默认预加载整个 `references/coding/` 目录。

## 规范 ownership 边界

每类 Coding 关注点只有一个主要 owner：

| 关注点 | 负责文档 |
|---|---|
| 角色、Session 拓扑、Context Firewall、Primary Execution Session、派发前 ownership | [`coding/session-model_zh_cn.md`](coding/session-model_zh_cn.md) |
| Runtime 选择、Host/Profile 组成、角色 eligibility 映射、unavailable 边界 | [`coding/runtime_zh_cn.md`](coding/runtime_zh_cn.md) |
| Semantic Contract 传输、文件化 Context Exchange、Worker handoff、多 Worker 会合 | [`coding/context-exchange_zh_cn.md`](coding/context-exchange_zh_cn.md) |
| 两级规划、派发前/实现放行门槛、Interaction Slice、反馈、有界阶段、Decision Checkpoint、验证、Git 操作放行、输出纪律 | [`coding/execution-control_zh_cn.md`](coding/execution-control_zh_cn.md) |

具体产品操作与具体模型/参数策略不属于上述 Core ownership；Runtime Contract 通过注册表选择对应部署文件。

不得在 `SKILL_zh_cn.md`、本入口或另一个 Coding 模块中重复某模块的规范性规则；应改为引用 owner 文档。只有当 Coding 路由、模块 ownership 或跨模块加载条件变化时才修改本文件。

这套 ownership 同时也是多 git worktree 并行维护边界：Runtime Contract 调整通常只改 `coding/runtime_zh_cn.md`；Context Exchange 调整通常只改 `coding/context-exchange_zh_cn.md`；checkpoint/验证调整通常只改 `coding/execution-control_zh_cn.md`；Session 拓扑调整通常只改 `coding/session-model_zh_cn.md`。具体 Host 或 Model 策略应留在各自部署文件中。语义确实跨模块时可以同时修改，但不得仅为了重述其他模块策略而制造共享文件改动。

## 职责顺序

Coding 架构由 Input-side Reasoning 负责高价值语义决策，Primary Output 负责实现与实现反馈检查，Change Verification 负责独立的最终改动结果验证，Documentation/Comments & Git Operations 负责验证通过后的按需文档/注释物化，以及所有非简单仓库 Git 工作。Git 工作包括同步、分支/worktree 生命周期、暂存、提交、历史整合、冲突处理、远端、推送及适用的 Issue/PR 交付。逻辑角色不必都对应独立 Agent 实例。选择 Change Verification 时，为该 task conversation 启动一个独立 verifier 并在各验证 slice 中复用；每个新的最终状态 fingerprint/epoch 都必须独立重新评估，不能把此前结论作为证据；只有确实隔离的验证需求才创建额外 verifier。Documentation/Comments & Git Operations 在选择隔离收益时仍使用独立 Session；每个文档或 Git 操作仍需由父 Agent 单独放行 Interaction Slice。`session-model_zh_cn.md` 定义可能的拓扑，`runtime_zh_cn.md` 决定 active deployment 可以使用哪种拓扑。

在实质性派发前，应查阅 [`coding/execution-control_zh_cn.md`](coding/execution-control_zh_cn.md) 中的派发前推理、Interaction Slice、实现放行、最终验证和 Git 操作放行门槛；存在多个 Coding Worker 时，还应加载 [`coding/context-exchange_zh_cn.md`](coding/context-exchange_zh_cn.md) 中的父级会合规则。本入口只负责让这些 ownership 边界可被发现，不复制其细则。

详细角色与 Session 规则以 [`coding/session-model_zh_cn.md`](coding/session-model_zh_cn.md) 为规范来源，不得根据本摘要额外推导新的 Session 要求。

## 与 Multimodal Flow 的边界

普通 Coding 任务始终留在本 Flow。只有任务确实需要消费连续 GUI Observation、大量图片/截图、视频帧、设计参考或其他高体量视觉世界状态时，才切换或先进入 Multimodal Flow。

如果 Multimodal Flow 已完成视觉分析并需要修改代码，Coding Flow 只接收其窄 Handoff Contract；不得为了实现代码而把完整图片集、视频帧、Computer Use 历史、OCR 全文或视觉分析历史重新灌入 Primary Execution Session。

Multimodal Flow 架构和部署规则继续由它自己的按需 reference 独立负责；Coding Runtime 修改不得静默重定义这些规则。

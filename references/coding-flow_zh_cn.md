# Coding Flow

本 Flow 用于项目探索、规划、实现、重构、修复、代码/配置物化、构建测试、调试、独立改动验证、按需文档/注释物化，以及所有非简单仓库 Git 工作等 Coding 场景。具体 Coding 规则拆分到 `references/coding/` 下的独立模块；本文件只作为稳定的 Coding 路由/装配入口，不重复模块内部规范。

所有 Coding 角色同时遵循 [`shared-protocols_zh_cn.md`](shared-protocols_zh_cn.md)。

## 模块注册表与维护规则

[`coding/owner_zh_cn.md`](coding/owner_zh_cn.md) 是 `references/coding/` 下 Coding 功能模块的 **ownership 注册表**。它明确每个模块负责定义哪些语义、明确不负责哪些语义，以及与 `coding-flow`、`shared-protocols`、`references/runtime/**` 等目录外文档的边界。

当 `references/coding/` 中任一模块的**功能职责、定义边界、模块拆分/合并关系或与其他模块的 ownership 关系发生变化**时，必须在同一改动中同步更新 `coding/owner_zh_cn.md` 与英文镜像 `coding/owner.md`。仅修改既有 owner 范围内的具体规则细节，而不改变模块职责边界时，不要求机械更新注册表。

新增 Coding 模块前必须先在 owner 注册表中登记其职责边界；发现两个模块重复定义同一语义时，应依据 owner 注册表保留唯一权威定义，并删除非 owner 文档中的重复正文或改成最小引用。

owner 注册表是维护/路由元数据，不是每次 Coding 执行都必须加载的运行时模块。只有在需要判断规则归属、修改 Coding 文档结构或调整模块职责时才加载。

## 模块加载

选择 Coding Flow 后按任务需要加载模块：

1. 加载 [`coding/session-model_zh_cn.md`](coding/session-model_zh_cn.md)，建立角色与 Session 语义。
2. 加载 [`coding/runtime_zh_cn.md`](coding/runtime_zh_cn.md)，解析当前环境对应的已登记 Runtime deployment。
3. 在进行实质性 implementation、refactor、debugging、build/test 或其他可能跨越语义决策边界的执行前，加载 [`coding/execution-control_zh_cn.md`](coding/execution-control_zh_cn.md)。
4. 当任务使用多个独立 Coding Agent、需要复用跨 Agent 上下文、Worker 替换/升级接力，或父级多 Worker 会合时，加载 [`coding/context-exchange_zh_cn.md`](coding/context-exchange_zh_cn.md)。只要独立 Worker 使用 file-backed Context Exchange，还必须同时加载 [`coding/content-memo_zh_cn.md`](coding/content-memo_zh_cn.md)。

纯有界 exploration 可以在真正进入执行前暂缓加载 `execution-control_zh_cn.md`。从未创建额外 Coding Agent 的 Single-Session Coding 任务，不必机械加载 `context-exchange_zh_cn.md` 或 `content-memo_zh_cn.md`，除非确实需要文件化恢复或上下文传输。

`runtime_zh_cn.md` 只加载当前环境匹配的已登记部署文档，不预加载 `references/runtime/` 下所有文件。如果某个 Coding 模块已经加载且规则仍有效，不重复读取；按职责加载需要的模块，不得默认预加载整个 `references/coding/` 目录。

## Flow 装配边界

角色、Session topology 与角色独立性由 `session-model_zh_cn.md` 定义；Host/model 绑定由 `runtime_zh_cn.md` 解析；执行放行、Interaction Slice、checkpoint、验证与 Git 操作门槛由 `execution-control_zh_cn.md` 定义；跨 Worker 上下文传输与 handoff 由 `context-exchange_zh_cn.md` 定义；Worker Context Exchange prose 与 content memo 策略由 `content-memo_zh_cn.md` 定义。

本入口只负责决定**何时加载和组合这些模块**。不得根据本文件的摘要推导新的角色、Session、checkpoint、Context Exchange 或 Runtime 规则；详细语义以对应 owner 模块为准。模块边界的权威索引见 [`coding/owner_zh_cn.md`](coding/owner_zh_cn.md)。

## 与 Multimodal Flow 的边界

普通 Coding 任务始终留在本 Flow。只有任务确实需要消费连续 GUI Observation、大量图片/截图、视频帧、设计参考或其他高体量视觉世界状态时，才切换或先进入 Multimodal Flow。

如果 Multimodal Flow 已完成视觉分析并需要修改代码，Coding Flow 只接收其窄 Handoff Contract；不得为了实现代码而把完整图片集、视频帧、Computer Use 历史、OCR 全文或视觉分析历史重新灌入 Primary Execution Session。

Multimodal Flow 架构和部署规则继续由它自己的按需 reference 独立负责；Coding Runtime 修改不得静默重定义这些规则。

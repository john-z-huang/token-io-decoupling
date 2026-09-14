# Coding 文档 Ownership 注册表

本文件只负责登记 `references/coding/` 各模块的**定义 ownership 与边界**，用于回答“某条 Coding 规则应该由哪份文档定义”。它不是 Coding Flow 的执行规范，不重复各 owner 文档中的完整规则。

## Ownership 原则

- 每条稳定的 Coding 语义规则应只有一个主要 owner。
- 非 owner 文档可以为了路由、前置条件或结果消费而引用该规则，但不应复制完整规范正文。
- 发现两个模块同时定义同一语义时，先依据本注册表确定 owner；保留 owner 中的权威定义，把其他位置改成最小引用或删除重复内容。
- 如果新增规则无法自然落入现有 owner，应先更新本注册表或拆出新的专项模块，再写规范正文；不要临时把规则塞进最接近的长文档。
- 中英文镜像文件拥有相同的语义边界；`*_zh_cn.md` 不是独立 owner。

## `runtime.md` / `runtime_zh_cn.md`

**负责定义：**

- Coding Runtime Contract；
- Core Coding 角色如何解析到 Host Adapter + Model Profile；
- Runtime capability resolution、部署选择、降级与 unavailable handling 的 Core 边界；
- Host-neutral 的角色到运行时绑定约束。

**不负责定义：**

- 某个具体 Host 的命令、工具、Session 创建方式或产品 capability；这些属于 `references/runtime/hosts/**`；
- 某个模型供应商/模型家族的具体模型名、参数与 effort 配置；这些属于 `references/runtime/models/**`；
- Coding 角色本身的职责与独立性；这些属于 `session-model`；
- Worker 执行反馈、checkpoint 或 Context Exchange 文档行为。

## `session-model.md` / `session-model_zh_cn.md`

**负责定义：**

- Coding 角色集合及各角色职责；
- Single-Session / multi-Session topology；
- Session 生命周期、复用、替换与角色独立性；
- Primary Output、Change Verification、Documentation/Comments & Git Operations 等职责之间的隔离边界；
- 什么条件下一个逻辑职责需要或不需要独立 Session。

**不负责定义：**

- Host 如何实际创建 Session 或选择模型；属于 Runtime deployment；
- Interaction Slice 内如何汇报进度、何时阻塞父 Agent；属于 `execution-control`；
- Session 之间通过文件如何传输上下文；属于 `context-exchange`；
- Worker content memo 的语言、开关和写入策略；属于 `content-memo`。

## `execution-control.md` / `execution-control_zh_cn.md`

**负责定义：**

- Interaction Slice 的执行控制语义；
- Progress Signal；
- Control Checkpoint；
- 父 Agent 对 Worker 的 `Continue` / `Amend` / `Stop` control loop；
- Worker 在执行中何时继续、何时阻塞、何时返回；
- event-driven feedback 与执行层同步边界。

**不负责定义：**

- 角色/Session topology；属于 `session-model`；
- file-backed Context Exchange 的目录、文件 ownership 与跨 Worker 传输；属于 `context-exchange`；
- content memo 在 checkpoint 时是否刷新以及刷新什么；属于 `content-memo`。`execution-control` 只定义 checkpoint 事件本身。

## `context-exchange.md` / `context-exchange_zh_cn.md`

**负责定义：**

- Coding 上下文共享与 Semantic Contract 的传输边界；
- 多 Worker 的 file-backed Context Exchange workspace layout；
- Context Exchange Root、root `INDEX.md`、Worker 子目录的 ownership 与 filesystem capability 边界；
- 跨 Worker 的定向只读、机械复制和父级 compact handoff 降级顺序；
- Worker replacement / escalation 的上下文接力机制；
- Context Bootstrap/Refresh capsule 的选择、结构、freshness 与消费方式；
- Context 文档允许/禁止承载的信息类型以及 Evidence-on-Demand 的传输关系。

**不负责定义：**

- Worker 自己生成的 Context Exchange prose 使用什么工作语言；属于 `content-memo`；
- `write_content_memo` 的默认值、关闭权限、memo 内容与刷新节奏；属于 `content-memo`；
- Progress Signal / Control Checkpoint 的触发语义；属于 `execution-control`；
- 角色独立性与 Session topology；属于 `session-model`。

## `content-memo.md` / `content-memo_zh_cn.md`

**负责定义：**

- Worker 在自己 Context Exchange 子目录中生成 prose 文档的工作语言；
- `write_content_memo` dispatch 配置及其默认 `true` 语义；
- 只有父 Agent 可以设置 `write_content_memo: false` 的权限边界；
- 默认执行内容 memo 的职责、推荐文件名、内容边界与压缩要求；
- memo 在 material milestone、Control Checkpoint、handoff、退出/替换等事件上的刷新策略；
- `write_content_memo: false` 不会关闭哪些其他协议。

**不负责定义：**

- Context Exchange Root/Worker 子目录如何创建和隔离；属于 `context-exchange`；
- Control Checkpoint 为什么触发以及父 Agent 如何决策；属于 `execution-control`；
- Worker 是否是独立 Session、由哪个模型运行；属于 `session-model` + Runtime deployment。

## 与目录外文档的边界

### `references/coding-flow.md` / `_zh_cn.md`

这是 Coding Flow 的**路由/装配入口**：负责说明在什么任务路径下加载哪些 Coding 模块、总体阶段顺序和模块组合。它不应重新定义本目录各模块已经拥有的详细协议。

### `references/shared-protocols.md` / `_zh_cn.md`

这是跨 Coding / Multimodal 复用的**共享协议 owner**。Semantic Contract 字段、共享 Dispatch Preview、Evidence-on-Demand 等真正跨 Flow 的原语应在这里定义；Coding 模块只定义 Coding-specific 的应用、路由或扩展，不复制共享协议正文。

### `references/runtime/**`

这里负责**具体部署实现**：Host Adapter 定义宿主真实暴露的工具、Session/进程创建方式、文件系统与 capability；Model Profile 定义具体模型绑定、参数与 effort。`references/coding/runtime*` 只拥有 Host/model-neutral 的 Coding Runtime Contract。

## 新规则路由

新增或修改 Coding 规则时，先按语义回答：

1. 是“有哪些职责/Session，以及是否独立”？→ `session-model`。
2. 是“Worker 执行过程中何时汇报、阻塞、继续或停止”？→ `execution-control`。
3. 是“上下文放在哪里、谁能读写、怎样跨 Worker 传输/接力”？→ `context-exchange`。
4. 是“Worker 上下文 prose 用什么语言、是否写执行总结、总结写什么/何时刷新”？→ `content-memo`。
5. 是“这些角色如何绑定到 Host/模型 capability”？→ `runtime`；具体 Host/model 细节继续下沉到 `references/runtime/**`。
6. 是跨 Flow 通用协议？→ 优先检查 `shared-protocols`，不要在 Coding 目录创建重复定义。

如果一项需求同时跨越多个 owner，应把规范拆成各自最小的 owner 片段，并通过引用连接；不要选择一个文档一次性拥有所有跨层语义。
# Coding Context Exchange

本模块负责 Coding Flow 的上下文共享、Semantic Contract 传输边界、文件化多 Agent Context Exchange 与 Worker 替换接力。

Semantic Contract 字段与 amendment、上下文阻塞规则、Dispatch Preview、事件驱动反馈和 Evidence-on-Demand 等共享原语继续遵循 [`../shared-protocols_zh_cn.md`](../shared-protocols_zh_cn.md)。

## 上下文共享与 Semantic Contract

### 简单、自包含任务

正常双 Session 模式使用精简提示：只给目标、必要约束、相关路径和需要返回的事实。能由 Primary Output Agent 自行读取的文件或项目状态，不由输入侧 Agent 大段复制到提示词中。

Single-Agent Luna Mode 不需要把当前 Agent 已知信息重新编码成发送给自己的提示；只在当前上下文中维护完成任务所需的最小稳定目标、约束、关键决策与验收标准。

### 复杂、强上下文任务

正常双 Session 模式中，当任务明显依赖大量会话、业务或项目背景时，优先把宿主能够安全共享的完整相关上下文交给 Primary Output Agent，并额外提供简短 Semantic Contract。这样避免输入侧 Agent 为重新描述已经存在的背景信息而产生大量输出，同时用 Contract 固化最终有效决策。

Single-Agent Luna Mode 继续使用 Semantic Contract 作为逻辑决策锚点，但不得为了形式完整把它当作 self-delegation prompt 再发送给自己。

## 多 Agent Coding 的文件化 Context Exchange

当 Coding Flow 使用多个独立执行 Agent 时，可复用的跨 Agent 上下文应优先物化为小型工作区文档，而不是反复经过父 Agent 重新生成摘要。该机制只用于补充 Semantic Contract、Decision Checkpoint、Evidence-on-Demand 与各 Agent 自身的活跃上下文，不替代这些既有机制。

### 工作区布局与 ownership

- 父 Agent 建立 **Context Exchange Root**：`<primary-worktree>/.token-io-decoupling/context/`。这里的 `primary-worktree` 指当前父级/高价值决策 Agent 用于协调本任务的工作树，即使具体执行 Agent 正在另一个 worktree 中修改代码，也仍把共享上下文写入该主工作树。
- Context Exchange Root 只属于运行时协调状态。不得暂存或提交，不得把它当作产品产物；工作流结束后默认删除，只有用户明确要求保留时才继续保存。如果宿主无法让相关 Agent 对该路径进行共享读写，则回退到精简的父 Agent 中转式 handoff，不能假装共享路径存在。
- 每个独立 Worker 分配一个稳定、可安全用作目录名的 **Context ID**，并拥有独立子目录，例如 `<root>/worker-auth/`。Worker 只写自己的子目录；替换或升级出来的新 Agent 使用新的子目录，并把前任目录当作只读历史。

### 有界文档集合

每个活跃 Worker 至少维护一个精简 `INDEX.md`，只保存路由上下文所需信息：当前 `Task`、`Scope`、`Status`、最近一次实质更新、各上下文文档的一行用途，以及当前 blocker 或 handoff 目标。只有确实存在复用价值时才创建额外文档；推荐名称包括 `findings.md`、`changes.md`、`verification.md` 与 `handoff.md`。不要机械创建全部文件，也不要把目录变成逐命令执行日志。

Context 文档可以记录稳定调查结论、相关路径或 symbol、执行级假设与局部选择、已尝试方案及失败原因、精简 changed-file 摘要、准确的验证命令与结果、剩余工作以及证据引用。优先引用项目文件或日志位置，而不是复制原始内容。

不得在 Context Exchange 文档中保存凭据、秘密、不必要的个人信息、完整日志、完整 diff、大段源码副本或无关会话历史。高体量原始证据继续留在拥有它的 Agent 一侧，只在需要时通过 Evidence-on-Demand 定向展开。

### 同步与 handoff

只在实质里程碑、阻塞式 Decision Checkpoint，以及 Agent 退出或被替换前更新可复用上下文；不要在每个命令或 tool call 后写一条记录。

其他 Agent 需要复用前序工作时，父 Agent 应优先传递路径，而不是重新生成背景说明。窄 Dispatch 可使用 `Context: <INDEX path>; Read: <specific document paths>` 之类的形式。接收 Agent 先读取索引，再只读取被点名的文档与当前任务直接需要的项目文件；不得默认递归加载所有 Worker 的全部目录。

只有在需要整合多个上下文、做高价值判断或发布权威 Semantic Contract amendment 时，父 Agent 才应重新综合成新的文字摘要。共享目录是降低输出 Token 的传输层，不是绕过 Context Firewall 或预加载无关状态的理由。

`Goal`、`Constraints`、`Decisions` 与 `Acceptance` 仍以 Semantic Contract 为权威来源。Worker context 文档不得静默覆盖 Contract；如果 Worker 的新发现意味着 Contract 需要变化，必须先走既有 Decision Checkpoint 与 amendment 路径，再跨越该执行边界。

当 Worker 需要替换或进行 reasoning-effort 升级时，原 Worker 应在条件允许时刷新 `INDEX.md`，并生成或更新 `handoff.md`，记录已完成状态、失败方案与证据、当前修改与验证状态、剩余 blocker 以及下一步最有价值的动作。接手 Agent 使用新的 Context ID，把前任的索引与 handoff 作为只读输入，而不是从零重新探索项目。如果前任已经不可用，父 Agent 只根据当前已有事实写最小恢复说明，不把完整历史重新编码成长篇中转文本。

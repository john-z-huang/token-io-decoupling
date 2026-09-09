# Coding Context Exchange

本模块负责 Coding Flow 的上下文共享、Semantic Contract 传输边界、文件化多 Agent Context Exchange 与 Worker 替换接力。

Semantic Contract 字段与 amendment、上下文阻塞规则、Dispatch Preview、事件驱动反馈和 Evidence-on-Demand 等共享原语继续遵循 [`../shared-protocols_zh_cn.md`](../shared-protocols_zh_cn.md)。

## 上下文共享与 Semantic Contract

### 简单、自包含任务

正常双 Session 模式使用精简提示：只给目标、必要约束、相关路径和需要返回的事实。能由 Primary Output Agent 自行读取的文件或项目状态，不由输入侧 Agent 大段复制到提示词中。

Single-Session Coding Mode 不需要把当前 Agent 已知信息重新编码成发送给自己的提示；只在当前上下文中维护完成任务所需的最小稳定目标、约束、关键决策与验收标准。

### 复杂、强上下文任务

正常双 Session 模式中，当任务明显依赖大量会话、业务或项目背景时，优先把宿主能够安全共享的完整相关上下文交给 Primary Output Agent，并额外提供简短 Semantic Contract。这样避免输入侧 Agent 为重新描述已经存在的背景信息而产生大量输出，同时用 Contract 固化最终有效决策。

Single-Session Coding Mode 继续使用 Semantic Contract 作为逻辑决策锚点，但不得为了形式完整把它当作 self-delegation prompt 再发送给自己。

## 多 Agent Coding 的文件化 Context Exchange

当 Coding Flow 使用多个独立执行 Agent 时，可复用的跨 Agent 上下文应优先物化为小型工作区文档，而不是反复经过父 Agent 重新生成摘要。该机制只用于补充 Semantic Contract、Decision Checkpoint、Evidence-on-Demand 与各 Agent 自身的活跃上下文，不替代这些既有机制。

### 工作区布局与 ownership

- 父 Agent 建立 **Context Exchange Root**：`<primary-worktree>/.token-io-decoupling/context/`。这里的 `primary-worktree` 指当前父级/高价值决策 Agent 用于协调本任务的工作树；即使具体执行 Agent 正在其他 worktree 中修改代码，共享上下文仍统一放在该主工作树下。
- 父 Agent 在 `<root>/INDEX.md` 创建并独占维护一个**根路由索引**。该文件记录每个当前或历史 Worker/Context ID 与其专属子目录的对应关系，并只补充父 Agent 路由所需的最小元数据，例如任务、scope、状态和 handoff 关系。任何 Worker 都不得修改根 `INDEX.md`。
- 每创建一个独立 Worker，父 Agent 都必须先为它创建一个专属子目录，例如 `<root>/worker-auth/`，并在派发时明确告诉该 Worker 自己拥有的准确目录。普通执行期间，Worker 只能在这个被分配的子目录内创建、读取、修改和删除与自身工作上下文有关的文档。
- Worker **绝对禁止**在其他 Worker 的子目录、Context Exchange Root 根目录或任何其他不属于自己的位置写入、重命名、移动或删除文件。即使共享文件系统让这些目录在技术上可见，也不能跨越这个写入边界。
- Worker 默认也不得浏览或读取其他 Worker 的子目录。只有父 Agent 因具体 handoff、验证、升级或依赖关系而**明确指定需要读取的文档或路径**时，才允许该 Worker 选择性读取对应材料；只能读取父 Agent 点名的内容，不得自行递归扫描或扩展读取其他目录。
- Worker 被替换或 Runtime escalation 时，接手 Agent 必须获得新的 Context ID，并由父 Agent 为其创建新的专属子目录。前任目录对接手 Agent 保持只读，而且只有父 Agent 明确指定的前任文档才可读取；接手 Agent 永远不得写入前任目录。
- Context Exchange Root 只属于运行时协调状态。不得暂存或提交，不得把它当作产品产物；工作流结束后默认删除，只有用户明确要求保留时才继续保存。

### 文件系统 capability 兜底

上述 ownership 规则应尽量由宿主的文件系统权限或沙箱能力做代码层兜底，而不是只依赖 Worker 理解并遵守自然语言指令。

- `git worktree` 用于提供独立工作副本、分支和清晰的物理目录边界，但 **worktree 本身不是文件写权限机制**。`git worktree lock`、sparse-checkout、`.gitignore`、`skip-worktree` 等 Git 功能也不得被当成跨 Worker 写入隔离手段。
- 当宿主支持 per-Agent sandbox、container/mount namespace、路径 allowlist 或等价 filesystem capability 时，父 Agent 应在 Worker 开始执行前配置最小权限集合：
  - **RW**：该 Worker 自己的代码 worktree，以及 `<root>/<worker-context-id>/` 专属 context 子目录；
  - **RO**：父 Agent 为当前具体 handoff 明确授权的其他 Worker 单个文档或严格有界路径；
  - **DENY / 不暴露**：`<root>/INDEX.md`、其他 Worker 的其余目录，以及任何未明确授权的 Context Exchange 路径。
- 上述 capability 是宿主/进程级约束，不只是 Dispatch 文本中的建议。Worker 即使因语义漂移尝试越界写入，文件系统层也应拒绝该操作。
- 如果多个 Worker 实际共享同一个 OS 用户身份，单纯依赖 `chmod` 或普通 Unix owner/group 权限通常不能可靠地区分 Worker 身份。需要真正的 per-Worker sandbox、独立容器/挂载命名空间、路径 capability 或等价机制才能形成强制边界。
- 跨 Worker 共享优先使用**原文档的定向只读 capability**。父 Agent 只传递文档路径与授权范围，不读取正文、不复制正文到 prompt，也不为纯传输目的重新总结内容。
- 如果宿主不能把另一个 Worker 目录中的指定文件以只读方式安全暴露给接收 Worker，但父 Agent 仍能执行文件系统工具操作，则父 Agent 可以把被点名的原文档**机械复制**到接收 Worker 自己目录下的 `imports/<source-context-id>/`。复制必须由文件系统/工具完成，不经过 LLM 重新生成正文。复制件只是一次性输入快照，即使接收 Worker 修改它，也不能影响来源 Worker 的原始文档或更新其状态。
- 只有在宿主既无法提供安全的定向只读访问，也无法进行这种文件系统级复制时，才退化为精简的父 Agent 中转式 handoff。此时仍应只传递完成当前决策所需的稳定事实，不得把完整 context 文档重新编码成长篇父 Agent 输出。

### 有界文档集合

每个活跃 Worker 在自己的专属子目录内维护一个精简 `INDEX.md`。这个**Worker 本地索引**与父 Agent 维护的根 `INDEX.md` 是两个不同层级的文件。Worker 本地索引只保存该 Worker 上下文路由所需信息：当前 `Task`、`Scope`、`Status`、最近一次实质更新、各上下文文档的一行用途，以及当前 blocker 或 handoff 目标。只有确实存在复用价值时才创建额外文档；推荐名称包括 `findings.md`、`changes.md`、`verification.md` 与 `handoff.md`。不要机械创建全部文件，也不要把目录变成逐命令执行日志。

Context 文档可以记录稳定调查结论、相关路径或 symbol、执行级假设与局部选择、已尝试方案及失败原因、精简 changed-file 摘要、准确的验证命令与结果、剩余工作以及证据引用。优先引用项目文件或日志位置，而不是复制原始内容。

不得在 Context Exchange 文档中保存凭据、秘密、不必要的个人信息、完整日志、完整 diff、大段源码副本或无关会话历史。高体量原始证据继续留在拥有它的 Agent 一侧，只在需要时通过 Evidence-on-Demand 定向展开。

### 同步与 handoff

只在实质里程碑、阻塞式 Decision Checkpoint，以及 Agent 退出或被替换前更新可复用上下文；不要在每个命令或 tool call 后写一条记录。

父 Agent 使用根 `INDEX.md` 跟踪“哪个 Worker 对应哪个专属子目录”，并决定其他 Worker 是否需要接收其中的某些上下文。其他 Agent 需要复用前序工作时，父 Agent 应优先授予被点名原文档的只读 capability，并只在 Dispatch 中传递准确路径与权限边界，例如 `Own Context RW: <path>; Read-only Context: <specific paths>`。接收 Agent 只能读取父 Agent 已授权的 Worker 本地索引和被明确点名的文档，以及当前任务直接需要的项目文件；不得自行发现、遍历或递归加载其他 Worker 目录。

如果宿主无法提供定向只读 capability，则按上一节的降级顺序使用工具级机械复制，再在必要时使用精简父级 handoff。父 Agent 不得为了跨 Worker 传输而先读取完整文档，再用 LLM 把同样内容重新生成给接收 Worker。

只有在需要整合多个上下文、做高价值判断或发布权威 Semantic Contract amendment 时，父 Agent 才应重新综合成新的文字摘要。共享目录与 capability 是降低输出 Token 的传输层，不是绕过 Context Firewall 或预加载无关状态的理由。

`Goal`、`Constraints`、`Decisions` 与 `Acceptance` 仍以 Semantic Contract 为权威来源。Worker context 文档不得静默覆盖 Contract；如果 Worker 的新发现意味着 Contract 需要变化，必须先走既有 Decision Checkpoint 与 amendment 路径，再跨越该执行边界。

当 Worker 需要替换或进行 Runtime escalation 时，原 Worker 应在条件允许时刷新自己目录里的 Worker 本地 `INDEX.md`，并生成或更新 `handoff.md`，记录已完成状态、失败方案与证据、当前修改与验证状态、剩余 blocker 以及下一步最有价值的动作。父 Agent 随后更新根 `INDEX.md`，为接手 Agent 创建新的 Context ID 和专属子目录，并优先通过宿主 capability 把被明确指定的前任文档只读暴露给接手 Agent；如果无法安全只读暴露，则机械复制这些文档到接手 Agent 的 `imports/` 后再派发。接手 Agent 不从零重新探索项目，也永远不得写入前任目录。如果前任已经不可用，父 Agent 只根据当前已有事实写最小恢复说明，不把完整历史重新编码成长篇中转文本。

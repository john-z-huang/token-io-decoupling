# Coding Context Exchange

本模块负责 Coding Flow 的上下文共享、Semantic Contract 传输边界、文件化多 Agent Context Exchange 与 Worker 替换接力。

Semantic Contract 字段与 amendment、上下文阻塞规则、Dispatch Preview、事件驱动反馈和 Evidence-on-Demand 等共享原语继续遵循 [`../shared-protocols_zh_cn.md`](../shared-protocols_zh_cn.md)。

## 上下文共享与 Semantic Contract

### 简单、自包含任务

正常双 Session 模式使用精简提示：只给目标、必要约束、相关路径和需要返回的事实。能由 Primary Output Agent 自行读取的文件或项目状态，不由输入侧 Agent 大段复制到提示词中。

Single-Session Coding Mode 不需要把当前 Agent 已知信息重新编码成发送给自己的提示；只在当前上下文中维护完成任务所需的最小稳定目标、约束、关键决策与验收标准。

### 复杂、强上下文任务

正常双 Session 模式中，当任务明显依赖大量会话、业务或项目背景时，优先把宿主能够安全共享的完整相关上下文交给当前 slice 的 Worker，并额外提供简短 Semantic Contract。Primary Output Agent 接收实现上下文；Change Verification Agent 只接收最终状态验证所需输入；Documentation/Comments & Git Operations Agent 在文档 slice 中接收最终已验证状态和获准的文档/注释范围，在 Git slice 中接收准确的仓库/worktree/ref/remote 范围、当前 Git 证据、已批准内容和明确授权。这样避免输入侧 Agent 为重新描述已经存在的背景信息而产生大量输出，同时用 Contract 固化最终有效决策。

Single-Session Coding Mode 继续使用 Semantic Contract 作为逻辑决策锚点，但不得为了形式完整把它当作 self-delegation prompt 再发送给自己。

### 角色专属 handoff 与父级会合

所有独立 Worker 都由父级 Input-side Reasoning Agent 创建和管理。每个 Worker 只接收其职责所需的上下文：

- **Primary Output** 接收已批准的实现 Contract、相关项目上下文、获准写入范围和当前 Interaction Slice。它的聚焦检查属于实现反馈，并以压缩摘要向后传递。
- **Change Verification** 接收最终项目状态或隔离的验证快照、验证 slice/最终状态 fingerprint 或 epoch、Contract 与验收标准、变更范围证据以及压缩的实现反馈摘要。初始 verifier Session 独立于 Primary Output 且为全新 Session；同一个 task conversation 中的后续验证 slice 复用该 verifier。Handoff 在可用时应指出累计的完整套件入口或等价 manifest 及其已知覆盖边界，使 verifier 能先运行它，再做针对变更风险的定向分析。它必须对每个所提供的 epoch 独立重新评估，不能把此前结论作为证据；不得修改受跟踪的产品/测试/文档文件，并且应返回证据而不是修复。如果发现有价值的可重复覆盖缺口，应在保持只读的同时报告准确的预期断言；父 Agent 将物化返回 Primary Output，然后针对新的 epoch 和累计套件运行复用同一个 verifier。
- **Documentation/Comments & Git Operations** 为每个明确放行的 slice 接收新的有界上下文。文档 slice 只在 verifier 通过（或明确跳过简单任务验证）后创建，并接收最终已验证状态、Contract、verifier 结论和仅限文档/注释的范围。Git slice 接收准确的仓库/worktree/ref/remote 范围、当前 Git 证据、已批准内容、适用流程、允许的操作和明确的用户/任务授权。它可以按授权操作 Git 元数据或远端仓库；只有使用已批准内容处理明确获准操作时才可解决冲突，不得进行语义决策、实现功能/测试或从其他角色推断授权。它返回压缩后的文档或 Git 操作证据。

当 verifier 报告实质性失败且 Primary Output 完成修复后，父 Agent 应向同一个 verifier 发送新的验证 slice 和修复后的最终状态 fingerprint/epoch。verifier 必须独立重新评估验收矩阵和所需检查；此前结论不能作为修复状态的证据。不得仅因发生修复就创建新的 verifier。只有确实需要隔离时才创建额外 verifier，例如不兼容的环境/快照、不同的权限或安全域，或明确要求的独立审计。

### 多 Coding Worker 的父级会合

当多个独立 Coding Worker 同时工作时，父 Agent 必须在派发前为每个 Worker 定义 Interaction Slice 和反馈边界。每个 Worker 都应收到自己的 `Objective`、`Authorized scope/mutations`、`Return conditions` 与 `Unreleased boundary`；并行执行不会授权 Worker 跨越未放行边界，也不能从其他 Worker 的进度推断自己已获许可。

Worker 可以在已授权 slice 内发送压缩 Progress Signal，但所有阻塞式 Control Checkpoint 都由父 Agent 负责。到达 Control Checkpoint 后，父 Agent 分析证据并为该 Worker 选择 `Continue`、`Amend` 或 `Stop`，也可以先请求 Evidence-on-Demand。如果 Semantic Contract、架构、范围、权限、安全或公共接口假设发生变化，父 Agent 决定其他 Worker 是继续、接收修订后的 slice，还是停止；Worker 不得在过时指令下静默继续。verifier 的通过/失败结论不会自行放行文档、修复或 Git 阶段；只有父 Agent 可以放行下一个存在依赖关系的 slice。

Context Exchange 文档只负责在 Worker 之间传输压缩发现、handoff 状态和可复用证据，不替代这个实时的父级 control loop。父 Agent 应在重大会合点更新 routing index 和相关 Worker 上下文，不要在每个 Progress Signal 或命令之后写记录。

### 按需 Context Bootstrap/Refresh

**Context Bootstrap/Refresh** 是一个可选的辅助职责，用于在多个下游 Worker 之前构建小型、可复用的事实与 policy-routing capsule。它不是第五个核心角色、强制 Session，也不负责 Semantic Contract 决策。只有在复用收益可能超过建立成本时，父级 Input-side Agent 才选择它：预计至少有两个相互独立的下游 Worker；某个 fresh Worker 原本需要广泛探索并加载三个或更多路由 policy module；或相关 source set 大约超过 20k 原始字符 / 5k token-equivalents。Single-Session 工作、一个小型 Worker、本地或仅文档的快路径、已知只涉及一两个文件，以及预期复用不超过建立成本的情况都应跳过。上述阈值只是路由启发式，不代表已测量的 billed、cached、quota、latency 或质量节省。

选定的 Bootstrap Worker 必须独立读取所有强制指令，并且只能在 `context/context-bootstrap/` 下写入有界 capsule：`MANIFEST.md` 记录快照身份、source hash 与 freshness 规则；`project-context.md` 记录中性的项目事实和准确 source pointer；`policy-context.md` 记录 policy routing 与权威 section。Capsule 可以包含事实、路径、hash、freshness/invalidation 数据和窄范围证据指针，但不得包含实现推理、Semantic Contract 结论、私有 chain-of-thought、秘密、完整 diff 或原始日志。下游 Worker 先读取 capsule，再只读取明确指向且自身确实需要的 source/code 路径；父级 Contract 与权威文件仍具有约束力。

Freshness 必须对照 `HEAD`/tree、tracked-delta fingerprint、列出的 source hash、相关未跟踪项目状态以及当前 task/scope 检查。任何实质字段发生变化时，父 Agent 都应重新激活同一个 Bootstrap Worker，只刷新受影响 section，之后才能依赖 capsule。若无法 refresh，接收 Worker 应直接读取点名的权威 source，并将受影响的 capsule 声明视为过时。Refresh 不替代独立 Change Verification。初始 verifier 是全新的；复用的 verifier 可以使用当前有界 capsule，但每个新的最终状态 fingerprint/epoch 都必须独立重新评估，且此前结论永远不能作为新状态的证据。

## 多 Agent Coding 的文件化 Context Exchange

当 Coding Flow 使用多个独立执行 Agent 时，可复用的跨 Agent 上下文应优先物化为小型工作区文档，而不是反复经过父 Agent 重新生成摘要。该机制只用于补充 Semantic Contract、Decision Checkpoint、Evidence-on-Demand 与各 Agent 自身的活跃上下文，不替代这些既有机制。

### 工作区布局与 ownership

- 父 Agent 建立 **Context Exchange Root**：`<primary-worktree>/.token-io-decoupling/context/`。这里的 `primary-worktree` 指当前父级/高价值决策 Agent 用于协调本任务的工作树；即使具体执行 Agent 正在其他 worktree 中修改代码，共享上下文仍统一放在该主工作树下。
- 父 Agent 在 `<root>/INDEX.md` 创建并独占维护一个**根路由索引**。该文件记录每个当前或历史 Worker/Context ID 与其专属子目录的对应关系，并只补充父 Agent 路由所需的最小元数据，例如任务、scope、状态和 handoff 关系。任何 Worker 都不得修改根 `INDEX.md`。
- 每创建一个独立 Worker，父 Agent 都必须先为它创建一个专属子目录，例如 `<root>/worker-auth/`，并在派发时明确告诉该 Worker 自己拥有的准确目录。普通执行期间，Worker 只能在这个被分配的子目录内创建、读取、修改和删除与自身工作上下文有关的文档。
- Worker **绝对禁止**在其他 Worker 的子目录、Context Exchange Root 根目录或任何其他不属于自己的位置写入、重命名、移动或删除文件。即使共享文件系统让这些目录在技术上可见，也不能跨越这个写入边界。
- Worker 默认也不得浏览或读取其他 Worker 的子目录。只有父 Agent 因具体 handoff、验证、升级或依赖关系而**明确指定需要读取的文档或路径**时，才允许该 Worker 选择性读取对应材料；只能读取父 Agent 点名的内容，不得自行递归扫描或扩展读取其他目录。
- Worker 被替换或 Runtime escalation 时，接手 Agent 必须获得新的 Context ID，并由父 Agent 为其创建新的专属子目录。前任目录对接手 Agent 保持只读，而且只有父 Agent 明确指定的前任文档才可读取；接手 Agent 永远不得写入前任目录。
- **Context Exchange Root** 是持久的运行时协调状态。仓库根目录的 `.gitignore` 必须忽略 `/.token-io-decoupling/`，使目录及其中的 capsule 能跨越工作流边界保留，同时不会被暂存或提交。不得把它当作产品产物，不得自动删除；只有明确的用户或 retention policy 才能触发清理。

### 文件系统 capability 兜底

上述 ownership 规则应尽量由宿主的文件系统权限或沙箱能力做代码层兜底，而不是只依赖 Worker 理解并遵守自然语言指令。

- `git worktree` 用于提供独立工作副本、分支和清晰的物理目录边界，但 **worktree 本身不是文件写权限机制**。`git worktree lock`、sparse-checkout、`.gitignore`、`skip-worktree` 等 Git 功能也不得被当成跨 Worker 写入隔离手段。
- 当宿主支持 per-Agent sandbox、container/mount namespace、路径 allowlist 或等价 filesystem capability 时，父 Agent 应在 Worker 开始执行前配置最小权限集合：
  - **RW**：该 Worker 自己的代码 worktree，以及 `<root>/<worker-context-id>/` 专属 context 子目录；
  - **RO**：父 Agent 为当前具体 handoff 明确授权的其他 Worker 单个文档或严格有界路径；
  - **DENY / 不暴露**：`<root>/INDEX.md`、其他 Worker 的其余目录，以及任何未明确授权的 Context Exchange 路径。
- 在文档 slice 期间，已跟踪的功能与测试必须保持在 RW capability 之外。在 Git slice 期间，父 Agent 只授予执行明确操作所需的 Git 元数据、目标 worktree 和远端 capability；仍禁止写入已跟踪内容，只有使用已批准内容进行明确获准冲突解决时才允许在严格有界文件中编辑。如果冲突解决需要新的语义决策，Worker 必须暂停并返回父 Agent；Git 角色不因此获得实现权限。
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

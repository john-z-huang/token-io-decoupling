# Codex Host Adapter

本文件描述当前已验证 Codex 部署使用的宿主专属机制，不负责 Coding 角色定义或具体模型策略。角色映射由 [`../../coding/runtime_zh_cn.md`](../../coding/runtime_zh_cn.md) 解析，具体 OpenAI 模型绑定由所选 Model Profile 负责。

## Host 身份

只有当前运行中的 Code Agent 环境确实是 Codex 时才使用本 Adapter。不得根据仓库内容、Skill 安装位置、提示词中出现 Codex，或仅仅存在 `AGENTS.md` 文件来推断 Host 身份。

当运行环境能够暴露当前模型或 Session 配置时，用这些事实进行 Runtime 解析。所需身份或 capability 信息无法获得时，应把该事实返回 Coding Runtime Contract，而不是猜测。

## 持久指令加载

需要让 Skill 核心不变量在每个新 run 中都生效的 Codex 部署，应使用 Codex 的持久指令机制。全局 `~/.codex/AGENTS.md` 可以保存短 bootstrap；同层级存在 `~/.codex/AGENTS.override.md` 时，以当前 active override 为准。仓库/项目指令继续负责项目专属政策，不得复制完整 Skill 形成第二份规范。

普通 Skill description 影响发现，但不能保证每个新 run 都已经加载完整 Skill。因此 bootstrap 应指向已安装的 `token-io-decoupling` Skill，再由 `SKILL.md` 路由需要的 reference，而不是把规范性 Flow 文本复制进持久指令文件。

## 独立 Agent 与 Session 操作

当 active Model Profile 要求独立 Primary Output、verifier、辅助 Worker 或定向 escalation Session 时：

- 使用当前 Codex 环境提供的独立 Agent/Session 机制；
- Codex 暴露模型和运行参数控制时，显式请求 Profile 要求的模型与宿主支持参数；
- Profile 要求精确模型或 reasoning-effort 档位时，不依赖未指定的宿主默认值；
- 相关工作优先复用已经建立的 Primary Execution Session，只有 Core 规则给出具体重建/拆分理由时才新建；
- 同一兼容 Session 只是切换逻辑职责时，不因为角色名称变化而创建第二个 Session。

当前 Codex 环境若无法创建所需独立 Session、无法选择所需模型，或不能满足所需运行参数，应把 capability failure 交给 active Model Profile 的 unavailable 规则处理；Host Adapter 不得自行换模型。

## Runtime 参数

Codex 可以为派发工作暴露模型选择和 `reasoning_effort` 控制。本 Adapter 只负责如何请求这些控制项；具体模型名称以及 `medium` / `high` / `xhigh` / `max` 策略属于 active Model Profile，不得在这里重复。

宿主 UI 或工具可能已经显示等价的派发信息；是否还需要额外用户可见预览由共享 `Dispatch Preview` 规则决定，Adapter 不创建第二套产品专属反馈协议。

## 文件系统与 worktree 映射

多 Agent Coding 使用文件化 Context Exchange 时，应通过当前 Codex 环境能够提供的最强隔离机制实现 [`../../coding/context-exchange_zh_cn.md`](../../coding/context-exchange_zh_cn.md) 的 capability 要求：

- 宿主支持路径级限制时，每个 Worker 的 RW 范围只覆盖自己的代码 worktree 和 context 子目录；
- 跨 Worker 上下文优先以定向 RO 路径暴露；
- 宿主支持时，其他 Worker context 与父级独占的根索引保持不暴露或 DENY；
- 无法安全提供 RO 共享时，先使用工具级机械复制，再考虑父 Agent 中转。

`git worktree` 只提供物理工作副本边界，不是权限机制；Adapter 不得宣称比当前沙箱实际能力更强的隔离。

## Run 生命周期

Codex 会在 run 或 TUI Session 启动时构建适用的指令链。修改全局持久指令、active override、Skill 或仓库指令文件后，应使用新的 run/Session 验证生效情况，不假定既有 Session 已自动吸收变更。

当前部署的安装步骤与 smoke check 见 [`../../../BEST_PRACTICES_zh_cn.md`](../../../BEST_PRACTICES_zh_cn.md)。

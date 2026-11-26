# 外部参考资料

本页保留旧 MCP 服务的参考资料，规则链接指向现行维护源。 [归档说明](../README.md)


本索引仅供开发和维护 `token-io-decoupling` Skill 时查阅。它是来源目录，不是执行指导。普通 Coding 任务不应加载本索引；Coding 工作流不依赖它。

| 来源 | URL | 对应文档 | 开发用途与边界 |
| --- | --- | --- | --- |
| Pi 官方文档 | https://github.com/earendil-works/pi | [Pi 运行时与能力边界](../../../rules/references/coding/layer-01-fundamental-concepts/session-runtime/runtime-provider-support.yaml) | 核对 Skill 按需加载、MCP 工具发现和宿主能力边界；当前支持情况以实际 Pi 客户端为准。 |
| Serena Memory 发现与读取 | https://raw.githubusercontent.com/oraios/serena/main/docs/02-usage/045_memories.md | [项目 Memory](../../../rules/references/coding/layer-01-fundamental-concepts/session-runtime/project-memory.yaml)、[任务计划生命周期](../../../rules/references/coding/layer-01-fundamental-concepts/execution-planning/task-plan-memory-lifecycle.yaml) | Issue #189：核对按名称主动选择读取及主题发现；区分工具执行确认和必需的内容验证，避免重复输出全文。 |
| Serena Memory 维护门槛 | https://raw.githubusercontent.com/oraios/serena/main/src/serena/resources/memory_maintenance.md | [项目 Memory](../../../rules/references/coding/layer-01-fundamental-concepts/session-runtime/project-memory.yaml)、[任务计划生命周期](../../../rules/references/coding/layer-01-fundamental-concepts/execution-planning/task-plan-memory-lifecycle.yaml) | Issue #189：区分稳定可复用知识与本 Skill 单独管理的任务计划和 Worker 记录；避免逐命令持久化。 |
| Git canonical 共同目录 | https://git-scm.com/docs/git-rev-parse | [任务计划生命周期](../../../rules/references/coding/layer-01-fundamental-concepts/execution-planning/task-plan-memory-lifecycle.yaml) | 核对用于带版本本机仓库 key 的绝对 checkout/共同目录解析；不得从 worktree basename、分支、remote URL 或 HEAD 派生。 |
| Git linked-worktree 仓库布局 | https://git-scm.com/docs/gitrepository-layout | [任务计划生命周期](../../../rules/references/coding/layer-01-fundamental-concepts/execution-planning/task-plan-memory-lifecycle.yaml) | 核对 commondir 共享及主仓库与 worktree 专属管理目录的区别，说明搬迁及独立 clone 的身份边界。 |
| MCP Python SDK v2 | https://py.sdk.modelcontextprotocol.io/whats-new/ | [工作流架构](WORKFLOW_ARCHITECTURE.md) | 核验 v2 服务端/客户端 API，并区分协议修订与包版本。 |
| MCP SDK 测试 | https://py.sdk.modelcontextprotocol.io/get-started/testing/ | [工作流架构](WORKFLOW_ARCHITECTURE.md) | 设计内存行为测试；它们不能证明任一宿主客户端的兼容性或线上传输交换。 |
| MCP 协议版本 | https://py.sdk.modelcontextprotocol.io/protocol-versions/ | [工作流架构](WORKFLOW_ARCHITECTURE.md) | 独立核验现代协议发现与版本证据，不依赖 SDK 主版本标签。 |
| MCP 客户端传输 | https://py.sdk.modelcontextprotocol.io/client/transports/ | [工作流架构](WORKFLOW_ARCHITECTURE.md) | 核验子进程 stdio 测试，不使用 GUI 交互或额外 Agent Session。 |
| MCP 传输授权 | https://py.sdk.modelcontextprotocol.io/run/authorization/ | [工作流架构](WORKFLOW_ARCHITECTURE.md) | 核验 HTTP 令牌校验不能认证 stdio 或进程内客户端；要求独立的可信启动边界。 |
| OpenAI Decisions | https://developers.openai.com/api/docs/guides/decisions | [工作流架构](WORKFLOW_ARCHITECTURE.md) | 核验可选语义判断的类型化选项请求及拒绝响应；此引用不授权真实请求。 |
| OpenAI Python Decisions 参考 | https://developers.openai.com/api/reference/python/resources/decisions/methods/create | [Decisions 建议](../../../rules/references/coding/layer-01-fundamental-concepts/execution-planning/decisions-advisory.yaml) | 核验可选建议的 SDK 请求、固定选项响应及拒绝契约；本地配置、授权和最终判断仍为独立要求。 |
| uv workspace | https://docs.astral.sh/uv/concepts/projects/workspaces/ | [包结构与验证](mcp/DEVELOPMENT.md#包结构与验证) | 核验独立成员元数据、继承的 workspace sources 与共享 lockfile；源码根项目的 tool 安装另行验证。 |
| uv tool 环境 | https://docs.astral.sh/uv/concepts/tools/ | [MCP 开发](mcp/DEVELOPMENT.md) | 核验已安装可执行程序的环境、本地工具安装，以及统一入口的依赖/可执行程序边界。 |
| uv tool 命令参考 | https://docs.astral.sh/uv/reference/cli/#uv-tool-install | [MCP 开发](../INSTALL.md) | 核验使用 `uv tool install` 安装本地 wheel，并通过 `uv tool dir --bin` 定位入口，无须将其目录加入 PATH。 |
| uv 本地依赖缓存 | https://docs.astral.sh/uv/concepts/cache/ | [MCP 开发](../INSTALL.md) | 核验安装入口为何同时使用 `--reinstall`，确保只修改源码或规则资源后也会更新本地 workspace 依赖。 |
| OpenAI Decisions 创建接口 | https://developers.openai.com/api/reference/resources/decisions/methods/create | [运行环境与模型支持](../../../rules/references/coding/layer-01-fundamental-concepts/session-runtime/runtime-provider-support.yaml) | 核验子代理强度选择的 choice 请求、answers 中的 choice/refusal、固定 API 模型及输出边界；不授权创建 Agent。 |
| Serena MemoryManager 实现 | https://github.com/oraios/serena/blob/main/src/serena/memories/memory_manager.py | [任务计划生命周期](../../../rules/references/coding/layer-01-fundamental-concepts/execution-planning/task-plan-memory-lifecycle.yaml)、[MCP 开发](mcp/DEVELOPMENT.md) | 核实规范 Memory 路径、ignored/read-only 策略检查、原子保存和不传播引用的移动边界；这些行为不能代替对当前权限和读回证据的核验。 |
| Serena Memory API 实现 | https://github.com/oraios/serena/blob/main/src/serena/repl/api/mem_api.py | [任务计划生命周期](../../../rules/references/coding/layer-01-fundamental-concepts/execution-planning/task-plan-memory-lifecycle.yaml)、[项目 Memory](../../../rules/references/coding/layer-01-fundamental-concepts/session-runtime/project-memory.yaml) | 核实全文读取、简短写入回执，以及 `max_chars` 限制提交的写入内容而非读取输出。通用重命名会传播引用；这些操作都不构成受保护事务。 |
| OpenAI Structured Outputs | https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses | [工作流路由建议](../../../rules/references/coding/layer-01-fundamental-concepts/execution-planning/workflow-routing-advice.yaml)、[输出物化](../../../rules/references/coding/layer-01-fundamental-concepts/execution-planning/output-materialization.yaml) | 核验可选建议和已提供事实排序相关的有界结构化响应行为；不得将 API 输出当作授权。 |

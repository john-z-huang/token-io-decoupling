# 外部参考资料

[English](EXTERNAL_REFERENCES.md) | [简体中文](EXTERNAL_REFERENCES_zh_cn.md)

本索引仅供开发和维护 `token-io-decoupling` Skill 时查阅。它是来源目录，不是执行指导。普通 Coding 任务不应加载本索引；Coding 工作流不依赖它。

| 来源 | URL | 对应文档 | 开发用途与边界 |
| --- | --- | --- | --- |
| Git canonical 共同目录 | https://git-scm.com/docs/git-rev-parse | [任务计划生命周期](docs/skill/references/coding/layer-01-fundamental-concepts/execution-planning/task-plan-memory-lifecycle_zh_cn.md)、[任务计划工具](mcp/TASK_PLAN_TOOLS_zh_cn.md) | 核对用于带版本本机仓库 key 的绝对 checkout/共同目录解析；不得从 worktree basename、分支、remote URL 或 HEAD 派生。 |
| Git linked-worktree 仓库布局 | https://git-scm.com/docs/gitrepository-layout | [任务计划生命周期](docs/skill/references/coding/layer-01-fundamental-concepts/execution-planning/task-plan-memory-lifecycle_zh_cn.md)、[任务计划工具](mcp/TASK_PLAN_TOOLS_zh_cn.md) | 核对 commondir 共享及主仓库与 worktree 专属管理目录的区别，说明搬迁及独立 clone 的身份边界。 |
| Codex 桌面应用 | https://developers.openai.com/codex/app/ | [delegation-mode-confirmation_zh_cn.md](docs/skill/references/coding/layer-01-fundamental-concepts/delegation/delegation-mode-confirmation_zh_cn.md) | 仅作一般 composer 背景资料；不是 `request_user_input_async` 能力来源。 |
| Codex CLI | https://developers.openai.com/codex/cli/ | [delegation-mode-confirmation_zh_cn.md](docs/skill/references/coding/layer-01-fundamental-concepts/delegation/delegation-mode-confirmation_zh_cn.md) | 交互式终端使用的背景资料。 |
| Codex Prompting Guide | https://developers.openai.com/cookbook/examples/gpt-5/codex_prompting_guide | [delegation-mode-confirmation_zh_cn.md](docs/skill/references/coding/layer-01-fundamental-concepts/delegation/delegation-mode-confirmation_zh_cn.md) | 将多个建议呈现为编号选项的背景资料。 |
| Claude Code 工具参考 | https://code.claude.com/docs/en/tools#askuserquestion | [delegation-mode-confirmation_zh_cn.md](docs/skill/references/coding/layer-01-fundamental-concepts/delegation/delegation-mode-confirmation_zh_cn.md) | `AskUserQuestion` 界面及其回复行为的背景资料。 |
| MCP Python SDK v2 | https://py.sdk.modelcontextprotocol.io/whats-new/ | [增强架构](docs/skill/ENHANCED_ARCHITECTURE_zh_cn.md) | 核验 v2 服务端/客户端 API，并区分协议修订与包版本。 |
| MCP SDK 测试 | https://py.sdk.modelcontextprotocol.io/get-started/testing/ | [增强架构](docs/skill/ENHANCED_ARCHITECTURE_zh_cn.md) | 设计内存行为测试；它们不能证明任一宿主客户端的兼容性或线上传输交换。 |
| MCP 协议版本 | https://py.sdk.modelcontextprotocol.io/protocol-versions/ | [增强架构](docs/skill/ENHANCED_ARCHITECTURE_zh_cn.md) | 独立核验现代协议发现与版本证据，不依赖 SDK 主版本标签。 |
| MCP 客户端传输 | https://py.sdk.modelcontextprotocol.io/client/transports/ | [增强架构](docs/skill/ENHANCED_ARCHITECTURE_zh_cn.md) | 核验子进程 stdio 测试，不使用 GUI 交互或额外 Agent Session。 |
| MCP 传输授权 | https://py.sdk.modelcontextprotocol.io/run/authorization/ | [增强架构](docs/skill/ENHANCED_ARCHITECTURE_zh_cn.md) | 核验 HTTP 令牌校验不能认证 stdio 或进程内客户端；要求独立的可信启动边界。 |
| OpenAI Decisions | https://developers.openai.com/api/docs/guides/decisions | [增强架构](docs/skill/ENHANCED_ARCHITECTURE_zh_cn.md) | 核验可选语义判断的类型化选项请求及拒绝响应；此引用不授权真实请求。 |
| OpenAI Python Decisions 参考 | https://developers.openai.com/api/reference/python/resources/decisions/methods/create | [Decisions 建议](docs/skill/references/coding/layer-01-fundamental-concepts/execution-planning/decisions-advisory_zh_cn.md) | 核验可选建议的 SDK 请求、固定选项响应及拒绝契约；本地配置、授权和最终判断仍为独立要求。 |
| SQLite 备份 API | https://docs.python.org/3/library/sqlite3.html#sqlite3.Connection.backup | [增强架构](docs/skill/ENHANCED_ARCHITECTURE_zh_cn.md) | 在已授权的 schema 升级前使用数据库备份 API。 |
| uv GitHub Actions 集成 | https://docs.astral.sh/uv/guides/integration/github/ | [MCP 开发](mcp/DEVELOPMENT_zh_cn.md) | 核验 CI 中固定版本的 uv 配置、托管 Python 矩阵与锁定依赖安装；工作流实际运行与本地检查属于不同证据。 |
| Linux Unix domain socket 凭据 | https://man7.org/linux/man-pages/man7/unix.7.html | [MCP 开发](mcp/DEVELOPMENT_zh_cn.md) | 核验继承的特权宿主通道所使用的内核对端凭据；不据此证明运行时 Session 映射或操作守卫。 |
| Apple 对端凭据 | https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man3/getpeereid.3.html | [MCP 开发](mcp/DEVELOPMENT_zh_cn.md) | 独立核验原生 macOS 对端凭据认证，不假设 Python socket API 暴露相同能力。 |
| Codex MCP | https://learn.chatgpt.com/docs/extend/mcp?surface=cli | [增强架构](docs/skill/ENHANCED_ARCHITECTURE_zh_cn.md) | 核验本地传输控制，不据此推断可信的逐 Agent 身份或文件系统隔离。 |
| Codex stdio 注册 | https://learn.chatgpt.com/docs/extend/mcp | [MCP 开发](mcp/DEVELOPMENT_zh_cn.md) | 核验一个绝对入口通过不同 profile 参数分别注册四个 MCP 服务；配置与工具发现不证明 Session 身份或操作守卫。 |
| Codex stdio 环境转发 | https://learn.chatgpt.com/docs/extend/mcp?surface=cli | [MCP 开发](mcp/DEVELOPMENT_zh_cn.md#codex-stdio-环境变量转发) | 核验自动 setup 和定向修复所需的逐服务 `env_vars` 转发，并与 API 启用及宿主绑定区分。 |
| TOML Kit 解析与文档编辑 | https://tomlkit.readthedocs.io/en/latest/quickstart/ | [MCP 开发](mcp/DEVELOPMENT_zh_cn.md#codex-stdio-环境变量转发) | 核验 `parse`/`dumps` 及保留风格的文档编辑；针对锁定包版本的本地测试另行检查定向合并、错误处理和文件写入行为。 |
| TOML Kit 格式限制 | https://github.com/python-poetry/tomlkit/blob/master/README.md | [MCP 开发](mcp/DEVELOPMENT_zh_cn.md#codex-stdio-环境变量转发) | 本地缓存的上游 README 指出了乱序数组子表的规范化行为；针对锁定版本复现，并在写入前拒绝意外的排版变化。 |
| Serena Codex setup 实现 | https://github.com/oraios/serena/blob/main/src/serena/config/client_setup.py | [MCP 开发](mcp/DEVELOPMENT_zh_cn.md) | 研究显式启动/setup 分离与官方客户端注册，将模式用于单一安装入口，不根据 context 或 cwd 推断身份。 |
| uv workspace | https://docs.astral.sh/uv/concepts/projects/workspaces/ | [实现包](docs/skill/ENHANCED_ARCHITECTURE_zh_cn.md#实现包) | 核验独立成员元数据、继承的 workspace sources 与共享 lockfile；源码根项目的 tool 安装另行验证。 |
| uv tool 环境 | https://docs.astral.sh/uv/concepts/tools/ | [MCP 开发](mcp/DEVELOPMENT_zh_cn.md) | 核验已安装可执行程序的环境、本地工具安装，以及统一入口的依赖/可执行程序边界。 |
| uv tool 命令参考 | https://docs.astral.sh/uv/reference/cli/#uv-tool-install | [MCP 开发](mcp/DEVELOPMENT_zh_cn.md#uv-tool-安装与-codex-setup) | 核验单次调用安装入口使用 `--force` 安装工具、选择托管 Python，并通过 `uv tool dir --bin` 定位入口，无须将其目录加入 PATH。 |
| uv 本地依赖缓存 | https://docs.astral.sh/uv/concepts/cache/ | [MCP 开发](mcp/DEVELOPMENT_zh_cn.md#uv-tool-安装与-codex-setup) | 核验安装入口为何同时使用 `--reinstall`，确保只修改源码或规则资源后也会更新本地 workspace 依赖。 |
| OpenAI Decisions 创建接口 | https://developers.openai.com/api/reference/resources/decisions/methods/create | [运行环境与模型支持](docs/skill/references/coding/layer-01-fundamental-concepts/session-runtime/runtime-provider-support_zh_cn.md) | 核验子代理强度选择的 choice 请求、answers 中的 choice/refusal、固定 API 模型及输出边界；不授权创建 Agent。 |
| Codex 子代理配置 | https://learn.chatgpt.com/docs/agent-configuration/subagents | [运行环境与模型支持](docs/skill/references/coding/layer-01-fundamental-concepts/session-runtime/runtime-provider-support_zh_cn.md)、[子代理创建](docs/skill/references/coding/layer-01-fundamental-concepts/delegation/delegation-child-creation_zh_cn.md) | 核验创建时模型与推理强度控制，以及自定义配置的优先级；实际调用仍以当前 Session 暴露的控制为准。 |
| Claude 原生子代理 effort | https://code.claude.com/docs/en/sub-agents#choose-an-effort-level | [运行环境与模型支持](docs/skill/references/coding/layer-01-fundamental-concepts/session-runtime/runtime-provider-support_zh_cn.md)、[子代理创建](docs/skill/references/coding/layer-01-fundamental-concepts/delegation/delegation-child-creation_zh_cn.md) | 仅为 MCP 目录外的原生 Skill 指令核验 effort 调用、版本边界、恢复与环境优先级；MCP Server 不支持该客户端。 |
| Codex MCP 能力 | https://learn.chatgpt.com/docs/extend/mcp | [任务计划生命周期](docs/skill/references/coding/layer-01-fundamental-concepts/execution-planning/task-plan-memory-lifecycle_zh_cn.md) | 核实 MCP 连接范围并区分实际 Serena 调用与原生规划/回忆；当前 Session 调用提供具体 schema 证据。 |
| Claude Code MCP 工具可用性 | https://code.claude.com/docs/en/mcp#tool-availability | [任务计划生命周期](docs/skill/references/coding/layer-01-fundamental-concepts/execution-planning/task-plan-memory-lifecycle_zh_cn.md) | 核实对应可发现 MCP 服务、能力缺失和逐 Agent 权限检查；不推定相同工具前缀或共享访问。 |
| Claude Code 安全调用重放 | https://code.claude.com/docs/en/mcp#mark-tools-that-are-safe-to-call-twice | [运行环境与模型支持](docs/skill/references/coding/layer-01-fundamental-concepts/session-runtime/runtime-provider-support_zh_cn.md) | 对比带注解的 HTTP/connector 调用传输重放与 Codex effort 选择器的显式恢复；它不会使 Claude 获得此 Codex 专用 server，也不授权应用重调或创建子代理。 |
| Codex MCP 重放文档 | https://learn.chatgpt.com/docs/extend/mcp?surface=cli | [运行环境与模型支持](docs/skill/references/coding/layer-01-fundamental-concepts/session-runtime/runtime-provider-support_zh_cn.md) | 将已记载的 stdio/HTTP 连接配置与 Claude 的 annotation 驱动重试进行对照；该页面未说明等价重放，不应被视为 Codex 已实现或缺少未文档化行为的证明。 |
| Serena MemoryManager 实现 | https://github.com/oraios/serena/blob/main/src/serena/memories/memory_manager.py | [任务计划生命周期](docs/skill/references/coding/layer-01-fundamental-concepts/execution-planning/task-plan-memory-lifecycle_zh_cn.md)、[MCP 开发](mcp/DEVELOPMENT_zh_cn.md) | 核实规范 Memory 路径、ignored/read-only 策略检查、原子保存和不传播引用的移动边界；适配器须自行补充版本、锁、禁止覆盖和读回检查。本机安装版 2.1.0 观察与持续变化的上游源码分别作为证据。 |
| Serena Memory API 实现 | https://github.com/oraios/serena/blob/main/src/serena/repl/api/mem_api.py | [任务计划生命周期](docs/skill/references/coding/layer-01-fundamental-concepts/execution-planning/task-plan-memory-lifecycle_zh_cn.md) | 核实通用重命名会传播引用，工具写入有配置的回答大小限制；不得把这些操作当成受保护事务。 |
| Serena 配置实现 | https://github.com/oraios/serena/blob/main/src/serena/config/serena_config.py | [MCP 开发](mcp/DEVELOPMENT_zh_cn.md) | 核实常规配置加载可能迁移、创建配置或改变其权限；要求显式 manager/factory 注入，不在能力发现时自动加载配置。 |

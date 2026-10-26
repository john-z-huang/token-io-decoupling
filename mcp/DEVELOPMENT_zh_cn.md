# MCP 开发指南

[English](DEVELOPMENT.md) | [简体中文](DEVELOPMENT_zh_cn.md)

本指南负责可选 Python 子系统的本地开发与包检查。工作流政策仍由 [Skill 入口](../SKILL_zh_cn.md)及其链接的 owner 维护；[架构契约](../ENHANCED_ARCHITECTURE_zh_cn.md)说明组件边界。

## 环境与检查

在 `mcp/` 中运行以下命令。项目声明 Python 3.11 或更新版本，并提交依赖锁文件。使用 uv 托管的解释器和锁定的开发依赖：

```sh
uv sync --managed-python --locked --group dev
uv run --managed-python --locked -- pytest
uv run --managed-python --locked -- ruff check .
uv run --managed-python --locked -- ruff format --check .
uv run --managed-python --locked -- ty check
```

如需把虚拟环境放在 checkout 外，运行这些命令前将 `UV_PROJECT_ENVIRONMENT` 设置为临时目录的绝对路径。测试使用临时数据库与模拟绑定，不证明操作系统隔离或实际宿主客户端兼容性。测试套件不需要 API 密钥或真实 API 请求。

仓库文档检查独立执行。请从仓库根目录运行[仓库指令](../AGENTS_zh_cn.md)要求的检查，包括既有工作流路线图与上下文交换回归测试。

## Stdio 服务与可信 embedding

`token-io-mcp` 入口为 MCP 客户端启动 stdio 服务。没有宿主通道时，在本目录中使用以下开发启动命令：

```sh
uv run --managed-python --locked -- token-io-mcp
```

没有宿主通道时，生产 CLI 只暴露 `workflow_capabilities`、`rules_get_context` 和 `database_schema_status`。其 schema 诊断不检查或创建状态路径，直接返回 unavailable。它保持 Native 模式；环境变量、客户端名称、请求的角色或文件系统路径都不能提供身份或权限证明。

embedding 可以向 `token_io_mcp.server.create_server` 提供经过验证的 `BindingProvider`。完整能力的 Root 绑定暴露 15 个工具，Worker 绑定暴露 10 个，未绑定服务暴露 3 个。受保护调用每次都会重新检查绑定与必需守卫。当前包没有经过验证的 Codex 或 ChatGPT Desktop 宿主适配器；测试 provider 与子进程 harness 不构成这种证明。不得将合成 provider 复制到生产环境，也不能从这些测试推断操作系统隔离已经成立。

协议目标为 `2026-07-28`。测试使用 SDK 自动协商及真实子进程 stdio 调用，覆盖类型化枚举/UTC 值和角色拒绝。这证明包的协议连接，实际宿主客户端兼容性仍需单独检查。

### 已认证的宿主通道

`token_io_mcp.host_binding` 中的 `HostChannelBindingProvider` 和 `serve_host_binding_channel` 将 CLI 连接到可信宿主已有的 `BindingProvider`。宿主在 MCP 请求参数之外，将一个真实 Session 绑定到一个已连接的 Unix stream socket，再把该连接的描述符传给非特权 CLI 进程，并服务另一端。supervisor 必须将服务端端点保留在可信边界内，且不得将同一通道重新分配给其他 Session。宿主启动命令为 `token-io-mcp --host-fd N`，其中 `N` 是不小于 3 的继承描述符；该参数只定位传输通道，不提供身份或权限。

CLI 使用操作系统凭据认证对端：Linux 使用 `SO_PEERCRED`，macOS 使用原生 `getpeereid` 调用。此实现将可信对端固定为 UID 0，并拒绝自身以 UID 0 运行的 CLI。Agent 当前用户创建的 socket 无法建立信任。不支持的凭据能力、无效描述符或启动绑定失败，都会终止所请求的绑定启动。内核机制见 [Linux Unix socket 手册](https://man7.org/linux/man-pages/man7/unix.7.html)和 [Apple 对端凭据手册](https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man3/getpeereid.3.html)。

绑定启动的 CLI 从操作系统账户数据库获取当前有效用户的主目录，并将其下的 `.local/state/token-io-decoupling` 作为状态根目录。调用方控制的 `HOME` 不能重定向该路径；账户映射不可用或无效时拒绝启动。可信 Python embedding 仍保留 factory 的显式 `state_root` 参数。

桥接在启动时锁定项目、Root、当前 Session、parent 和角色。每次受保护调用都会重新向宿主读取当前能力与守卫证据；撤销或身份变化会使调用被拒绝。子身份验证使用宿主当前的 parent 身份。线协议只接受两种绑定操作，限制帧大小并设置有限超时；格式错误或不匹配的响应直接拒绝，不重试。失败通道不能通过后续响应重新获得信任。

宿主必须先落实实际 sandbox、路径与 Worker store 边界，再报告相应守卫。内核认证只确认可信 supervisor，不会创建这些守卫，也不证明某运行时的 Session 映射正确。此包提供桥接及宿主侧服务 API，不提供特权服务安装器，也不构成已经验证的 Codex/Claude Code 运行时集成。普通 MCP 客户端配置不能凭空建立继承的特权通道。既有测试 provider 和模拟对端凭据的测试仍属于合成证据；未修改认证逻辑的同用户通道拒绝测试覆盖真实本地凭据边界。

声明实际运行时集成前，必须通过该运行时的 MCP 连接验证 Root 初始化、证据插入、状态转换及回读；验证真实释放且绑定的 Worker 能读取任务并只写入自己的进度/证据；并在实际宿主守卫下检查撤销和跨 Worker 拒绝。现有客户端需要重启或重新连接，才能加载改变的启动参数与工具清单；编辑 checkout 不会改变已经运行的 MCP 进程。

[Codex 调用者匹配](CODEX_CALLER_CONTEXT_zh_cn.md)说明对已有可信宿主绑定可选启用的 `--codex-context` 请求匹配门禁。它消费 SDK 请求元数据，不增加身份认证来源。

## 真实 API 请求的必需配置

Root 和每个受委派的 Agent 都必须在项目功能代码及测试/smoke 代码中遵守此限制：每次真实 API 请求前，从本地进程环境读取 `OPENAI_API_KEY` 和 `OPENAI_BASE_URL`。两项都必须存在且非空，仅含空白字符也视为无效。缺少任一项或任一项无效时，不得创建 SDK client 或发送真实请求，改走文档规定的回退路径。

不得使用硬编码密钥或端点、调用方提供的替代值或 SDK 的默认端点。必须在实际调用时读取这两项本地值，并显式传给 SDK；不得打印或持久化其值。合成配置仅可用于不发送网络请求的 Mock。

API 仍默认关闭。真实请求还必须具备显式启用及出站数据授权；本文档本身不授予这些权限。普通测试套件使用 Mock，真实 smoke 测试需要单独显式 opt-in，并遵守相同的双环境变量要求。

经过授权的 embedding 通过 factory 的 `decisions_config` 参数传入 `DecisionsRuntimeConfig(enabled=True, outbound_data_permitted=True)` 启用建议。两个评估工具的可选 `semantic_input` 仅限任务意图、输出类别、Contract 变化、验证影响和 Control。返回中 Core 结果与建议分开；未提供语义输入时保留原有 Core 返回。建议不会选择或确认 Gate 分支；过期、无效、拒绝、不可用或重放的建议均回到文档判断。

获得真实合成请求的显式授权后，确保两项本地环境变量已经配置，再从 `mcp/` 单独运行以下命令，不将其并入普通测试：

```sh
TOKEN_IO_RUN_REAL_DECISIONS=1 uv run --managed-python --locked -- python tests/decisions_real_smoke.py
```

没有 opt-in 时，脚本不发请求。它使用临时 Root 数据库和合成可信 provider，直接调用 `DecisionsAdvisor`，仅报告安全的状态、原因、分类元数据、选项和用量。它不证明真实宿主绑定，也不证明真实 API 请求经过了 MCP handler。MCP handler/协议测试使用模拟 API transport。advisor 在实际调用时读取两项必需的本地变量；脚本和项目都不提供替代凭据或默认端点。

## 构建与规则资源

在 `mcp/` 中构建 wheel 和源码分发包，输出到临时目录：

```sh
uv build --managed-python . --out-dir /tmp/token-io-mcp-dist
```

构建 Hook 从注册表及其引用的 Markdown owner 生成只读规则资源。这些生成摘录是包资源，不是第二份手工维护的政策正文。源码分发包携带自身的规则来源，使后续 wheel 构建不会借用无关的相邻 checkout。构建产物测试使用脱离原仓库的源码分发包，并检查双语规则及迁移资源。

在 checkout 中测试规则编辑时，构造 `RuleLoader` 并明确传入仓库根目录。默认加载器读取已安装的包资源。更新这些资源需要重新构建并安装分发包；编辑其他 checkout 不会更新已安装的 wheel。

迁移模块属于有版本的包资源。保留已发布文件，Schema 变化新增迁移。除新建数据库外，还要运行升级和恢复测试；仅验证初始化不能证明历史兼容性。

## CI 与隔离安装

[MCP 包工作流](../.github/workflows/mcp.yml)在托管 Python 3.11 和 3.14 上，使用锁定依赖执行完整 Mock 测试、Ruff lint/format 检查和 ty。独立的 Python 3.14 job 构建 wheel 和源码分发包，将 wheel 安装到临时 uv tool 目录，并从 checkout 外通过 SDK 调用已安装的可执行文件。这些 job 不启用 Decisions，也不需要 API 凭据。

本地隔离安装时，先用 `uv export --locked --all-groups --no-emit-project --no-hashes --no-header --no-annotate` 导出锁文件，将输出传给 `uv build --build-constraints`。再以 `--no-dev` 替代 `--all-groups` 单独导出运行时约束，安装 wheel 时传给 `uv tool install --constraints`。构建和安装均使用 `--managed-python --python 3.14`。将命令局部的 `UV_TOOL_DIR` 和 `UV_TOOL_BIN_DIR` 设置为临时目录的绝对路径，并通过绝对路径调用生成的 `token-io-mcp`。工作流包含完整命令，不需要修改 Shell 配置。

使用锁定的项目解释器运行 `tests/installed_stdio_smoke.py --cli /absolute/temporary/bin/token-io-mcp` 检查该安装。脚本在 checkout 外、空 `PYTHONPATH` 下启动服务，检查自动协议协商、三个 Native 公共工具、包内两种语言的规则及不可用的 schema 诊断。这属于包/stdio 证据，不证明 Codex 或 ChatGPT Desktop 绑定。本地执行也不能证明 GitHub Actions 已经运行。

[文档工作流](../.github/workflows/multilingual-docs.yml)保留仓库验证器及工作流路线图/上下文回归，并新增扫描器回归。共享发现逻辑在遍历前剪枝生成资源、虚拟环境、缓存、vendor 目录和符号链接；手工维护的 MCP 文档仍接受语言镜像及链接检查。

## Native 恢复开发检查

[Native 权威转交](../references/coding/layer-01-fundamental-concepts/native-authority-transfer_zh_cn.md)和 [Native 对账](../references/coding/layer-01-fundamental-concepts/native-reconciliation_zh_cn.md) owner 定义工作流边界。以下检查验证已实现的服务用例，不证明完整导出或宿主停写能力。

恢复开发使用临时数据库和合成绑定。状态服务的定向用例覆盖完整集合的显式裁定、比较历史保留、恢复 Revision/Epoch 新鲜度、尚未完成的补证请求及派发副作用阻断，也覆盖精确确认不掩盖旧冲突、恢复后首个 Slice 前的新鲜 Control、已确认派发的无副作用重放，以及超限旧快照的有界回读。迁移测试区分有证明的旧确认配对与格式错误或 Revision 不相邻的记录。从 `mcp/` 先运行定向用例，再执行完整套件：

```sh
uv run --managed-python --locked -- pytest tests/test_state_service.py -k native
uv run --managed-python --locked -- pytest tests/test_migrations.py
```

这些检查不证明宿主能够停止 Worker。受支持的实质差异恢复路径要求已有 Root 控制状态，且没有已绑定 Worker、活动 Worker Slice 或待确认派发。它裁定 Contract 来源与语义引用这一对字段，不重建缺失的身份、派发、生命周期或验收历史。不受支持的状态保持阻断并保留记录。证据引用和请求 Hash 提供审阅指针与完整性绑定；两者都不能认证调用方，也不能独立证明新鲜度或静默状态。

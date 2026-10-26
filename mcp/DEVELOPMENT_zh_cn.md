# MCP workspace 开发指南

[English](DEVELOPMENT.md) | [简体中文](DEVELOPMENT_zh_cn.md)

本指南负责 Python workspace 的开发、构建产物检查、uv tool 安装与 Codex setup。[架构契约](../ENHANCED_ARCHITECTURE_zh_cn.md#实现包)负责包职责与依赖方向；[Skill 入口](../SKILL_zh_cn.md)及其链接的 owner 仍是工作流权威。

## 环境与检查

Workspace 包含八个可独立构建的分发包，各有自己的 `pyproject.toml`，共同使用一份 `uv.lock`。只有根分发包 `token-io-decoupling` 导出 console script。从 `mcp/` 使用托管 Python 和锁定依赖运行：

```sh
uv sync --managed-python --locked --all-packages --group dev
uv run --managed-python --locked -- pytest
uv run --managed-python --locked -- ruff check .
uv run --managed-python --locked -- ruff format --check .
uv run --managed-python --locked -- ty check
```

`ty` 覆盖根源码、测试、各库包及 core 构建 Hook。如需将环境放在 checkout 外，设置 `UV_PROJECT_ENVIRONMENT` 为临时目录的绝对路径。测试使用临时数据库、模拟绑定及 API transport，不需要真实 API 请求。从仓库根目录运行[仓库指令](../AGENTS_zh_cn.md)要求的文档检查。

## 统一入口与 profile 工具

安装后的命令为 `token-io-decoupling`，启动时选择 profile：

```sh
token-io-decoupling start-mcp-server --profile workflow
```

`--profile` 接受 `workflow`、`root`、`worker` 或 `share`。省略子命令时使用 workflow profile 启动 stdio；`--version` 输出入口版本。各 profile 的清单固定且互不重复：

| Profile / Codex 服务注册名 | 工具 |
| --- | --- |
| `workflow` / `token-io-decoupling-workflow` | `workflow_capabilities`、`rules_get_context`、`workflow_evaluate`、`evaluate_control_checkpoint` |
| `root` / `token-io-decoupling-root-agent-tools` | `workflow_open`、`delegation_reserve`、`delegation_bind`、`slice_check`、`slice_release`、`workflow_transition`、`parent_get_worker_summary`、`workflow_reconcile` |
| `worker` / `token-io-decoupling-worker-agent-tools` | `worker_get_assignment`、`worker_record_progress`、`worker_get_evidence`、`worker_report_blocker`、`worker_get_recovery_context` |
| `share` / `token-io-decoupling-share-tools` | `database_schema_status`、`state_get`、`record_evidence` |

Profile 控制工具发现，不授予权限。没有可信宿主通道时，公共能力/规则读取可成功，schema 状态不检查状态路径而返回 unavailable，受保护调用则拒绝缺失绑定。Workflow/Control 判断要求经过验证的 Root。共享读取与证据写入每次都解析经过验证的角色；Worker 读取拒绝非空的 Root `index_page` 游标。

Canonical Python 实现使用架构契约列出的独立包名。重命名后的 `token_io_decoupling_mcp` 适配命名空间承载原 façade 模块和默认 factory 的仅公共接口行为；`python -m token_io_decoupling_mcp.cli` 仍可使用。旧 `token_io_mcp` 导入命名空间不再作为通用 API 暴露。两个不可变 v1 迁移源仍保留历史字节中的 `token_io_mcp.models`；state migration loader 仅在导入期间临时提供 `DatabaseKind` 别名，随后移除。直接导入 frozen state 迁移模块会绕过此局部加载器，不受支持；需要直接导入时请使用重命名后的 adapter migration 路径。兼容文件分别由 core、state 或 launcher 负责，wheel 路径不重复。本 workspace 不导出旧四个 console script，也不导出之前的 `token-io-mcp` console script。

## uv tool 安装与 Codex setup

从 workspace 根项目的源码路径安装，uv 会解析其声明的本地 workspace 依赖。`uv tool dir --bin` 返回的目录须位于 `PATH`，或使用已安装命令的绝对路径调用。真实 setup 还要求 Codex CLI 位于 `PATH`：

```sh
uv tool install --managed-python --python 3.14 /absolute/path/to/skill/mcp
token-io-decoupling setup codex --dry-run
token-io-decoupling setup codex
```

Setup 使用一个核验后的可执行文件绝对路径和不同 profile 参数，注册上表的四个服务名。只配置一个时使用 `setup codex --profile root`。`--all` 是默认全 profile 选择的显式别名，不能与 `--profile` 同用。审阅 dry-run 后，要迁移已有注册，可执行：

```sh
token-io-decoupling setup codex --replace
```

Setup 与启动的分离参考 [Serena 的客户端 setup 实现](https://github.com/oraios/serena/blob/main/src/serena/config/client_setup.py)。本入口从当前安装环境的 scripts 目录及精确的分发包入口元数据解析可执行文件，不根据启动目录推断项目或身份。

Dry-run 输出所选 profile 的 JSON 参数向量，不运行子进程或 Codex 预检。真实 setup 先探测 CLI，读取服务清单及嵌套 `transport` 数据，再开始写入。已启用且解析后的命令与 `start-mcp-server --profile <profile>` 参数匹配的注册会被跳过，保留附加设置。冲突或已禁用条目要求 `--replace`。替换使用官方同名 upsert，不先删除旧条目。预检失败不写入；部分应用失败会报告已应用与待处理名称，不打印捕获的配置或子进程输出。手动等价命令示例：

```sh
codex mcp add token-io-decoupling-root-agent-tools -- /absolute/installed/token-io-decoupling start-mcp-server --profile root
```

新入口及注册核验通过后，从本仓库旧四命令工具迁移的环境可用 `uv tool uninstall token-io-mcp` 移除旧分发包。保留其他工具、服务和设置，并重新连接 MCP 客户端以加载新启动命令。Setup 不建立可信宿主绑定。

协议目标仍为 `2026-07-28`。SDK 子进程测试核验协商与调用；实际可信宿主集成仍需独立证据。

## 已认证的宿主通道

`token_io_decoupling_core.host_binding` 中的 `HostChannelBindingProvider` 和 `serve_host_binding_channel` 将 CLI 连接到可信宿主已有的 `BindingProvider`。宿主在 MCP 请求参数之外，将一个真实 Session 绑定到一个已连接的 Unix stream socket，再把该连接的描述符传给非特权 CLI 进程，并服务另一端。supervisor 必须将服务端端点保留在可信边界内，且不得将同一通道重新分配给其他 Session。宿主启动所选可执行程序，例如 `token-io-decoupling start-mcp-server --profile root --host-fd N`，其中 `N` 是不小于 3 的继承描述符；该参数只定位传输通道，不提供身份或权限。

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

## 构建、规则资源与安装检查

从 `mcp/` 构建八个 wheel 与源码分发包：

```sh
uv build --all-packages --managed-python --python 3.14 --out-dir /tmp/token-io-dist
```

规则资源及自定义构建 Hook 由 core 包负责。Canonical 注册表仍为 `mcp/rule-registry.json`；构建产物包含其英文/中文 owner 标题的有界摘录。Core sdist 携带自己的 `rule_sources`，脱离仓库构建时不借用相邻 checkout。默认 `token_io_decoupling_core.rules.RuleLoader` 读取打包快照；源码开发必须明确提供仓库根目录。修改 Markdown 不会更新已安装的 wheel，需要重新构建和安装。

已发布迁移文件属于 state 包，保持原始字节不变，因为数据库历史记录了源码校验和。state loader 为两个 v1 文件所需的历史导入 `token_io_mcp.models.DatabaseKind` 临时提供模块别名，并在导入后移除。直接导入 frozen state 迁移模块会绕过此局部加载器，不受支持；需要直接导入时请使用重命名后的 adapter migration 路径。命名空间迁移不授权改写历史、校验规则或 schema 版本。测试同时覆盖旧历史与升级，以及新建数据库。

[MCP CI 工作流](../.github/workflows/mcp.yml)在托管 Python 3.11 和 3.14 上执行锁定检查，并有独立的安装版 wheel job。用 `uv export --no-emit-workspace` 导出第三方构建/运行时约束，构建再加 `--all-groups`，运行时再加 `--no-dev`。Workspace 成员由本地产物提供，不作为 editable requirements 导出。从脱离仓库的 wheel 集安装时，以产物目录作为 `--find-links`，安装根包 `token_io_decoupling-0.1.0-py3-none-any.whl`；保留已配置的索引以解析锁定的第三方依赖。完整命令见 CI。

临时安装使用命令局部的 `UV_TOOL_DIR` 和 `UV_TOOL_BIN_DIR`，均指向临时绝对目录。用锁定的 workspace 解释器运行 `tests/installed_stdio_smoke.py --cli /absolute/temporary/bin/token-io-decoupling`。脚本在 checkout 外、空 `PYTHONPATH` 下启动四个 profile 子进程，核验精确清单与绑定拒绝，检查两种语言规则，并在空 `PATH` 下运行 setup dry-run。源码根项目的 tool 安装另行检查。这些结果证明包与 stdio 行为，不证明实际宿主绑定或 GitHub Actions 已运行。

[文档工作流](../.github/workflows/multilingual-docs.yml)保留多语言、链接、路线验证器及扫描器回归；遍历时剪枝生成资源与环境，同时检查手写的 workspace 文档。

## Native 恢复开发检查

[Native 权威转交](../references/coding/layer-01-fundamental-concepts/native-authority-transfer_zh_cn.md)和 [Native 对账](../references/coding/layer-01-fundamental-concepts/native-reconciliation_zh_cn.md) owner 定义工作流边界。以下检查验证已实现的服务用例，不证明完整导出或宿主停写能力。

恢复开发使用临时数据库和合成绑定。状态服务的定向用例覆盖完整集合的显式裁定、比较历史保留、恢复 Revision/Epoch 新鲜度、尚未完成的补证请求及派发副作用阻断，也覆盖精确确认不掩盖旧冲突、恢复后首个 Slice 前的新鲜 Control、已确认派发的无副作用重放，以及超限旧快照的有界回读。迁移测试区分有证明的旧确认配对与格式错误或 Revision 不相邻的记录。从 `mcp/` 先运行定向用例，再执行完整套件：

```sh
uv run --managed-python --locked -- pytest tests/test_state_service.py -k native
uv run --managed-python --locked -- pytest tests/test_migrations.py
```

这些检查不证明宿主能够停止 Worker。受支持的实质差异恢复路径要求已有 Root 控制状态，且没有已绑定 Worker、活动 Worker Slice 或待确认派发。它裁定 Contract 来源与语义引用这一对字段，不重建缺失的身份、派发、生命周期或验收历史。不受支持的状态保持阻断并保留记录。证据引用和请求 Hash 提供审阅指针与完整性绑定；两者都不能认证调用方，也不能独立证明新鲜度或静默状态。

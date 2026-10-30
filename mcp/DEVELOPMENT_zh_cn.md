# MCP workspace 开发指南

[English](DEVELOPMENT.md) | [简体中文](DEVELOPMENT_zh_cn.md)

本指南负责 Python workspace 的开发、构建产物检查、uv tool 安装与 Codex setup。[架构契约](../ENHANCED_ARCHITECTURE_zh_cn.md#实现包)负责包职责与依赖方向；[Skill 入口](../SKILL_zh_cn.md)及其链接的 owner 仍是工作流权威。

MCP Server 仅支持 Codex 和 ChatGPT Desktop。遵循[目录指令](AGENTS_zh_cn.md)；`mcp/` 下的开发不维护其他 Code Agent 的兼容性。支持范围不等于已验证宿主适配器。

## 环境与检查

Workspace 包含八个可独立构建的分发包，各有自己的 `pyproject.toml`，共同使用一份 `uv.lock`。只有根分发包 `token-io-decoupling` 导出 console script。从 `mcp/` 使用托管 Python 和锁定依赖运行：

```sh
uv sync --managed-python --locked --all-packages --group dev
uv run --managed-python --locked -- pytest
uv run --managed-python --locked -- ruff check .
uv run --managed-python --locked -- ruff format --check .
uv run --managed-python --locked -- ty check
```

`ty` 覆盖根源码、测试、各库包及 core 构建 Hook。如需将环境放在 checkout 外，设置 `UV_PROJECT_ENVIRONMENT` 为临时目录的绝对路径。默认测试集使用临时数据库和离线 transport；真实 API 测试必须显式启用。从仓库根目录运行[仓库指令](../AGENTS_zh_cn.md)要求的文档检查。

### 测试组织

每个新增或修改的测试均按实际依赖与行为分类：

| 目录 | 职责 |
| --- | --- |
| `tests/mock_api_tests/` | 使用 mock、fake 或 stub 替代协作者、宿主绑定、API client 或 HTTP transport 的测试。 |
| `tests/unit_tests/` | 不模拟协作者、不请求真实 API，执行实际被测代码的确定性本地单元测试。 |
| `tests/real_api_tests/` | 必须显式启用、实际发送 Decisions 或 Responses 请求的测试及 smoke 脚本。 |

混合模块按测试用例拆分，marker 或文件名不能替代正确的目录归属。共享 fixture 和子进程辅助程序可以放在这三个用例目录之外，但不得成为未分类测试用例的存放处。迁移时保留断言、参数化与收集覆盖，同步更新导入、仓库根路径定位及 CI/脚本引用。普通 pytest 必须收集并跳过真实请求用例，且跳过前不读取凭据、不发送请求。后续新增测试同样遵守这些目录规则。

## 统一入口与 profile 工具

安装后的命令为 `token-io-decoupling`，启动时选择 profile：

```sh
token-io-decoupling start-mcp-server --profile workflow
```

`--profile` 接受 `workflow`、`root`、`worker` 或 `share`。省略子命令时使用 workflow profile 启动 stdio；`--version` 输出入口版本。各 profile 的清单固定且互不重复：

| Profile / Codex 服务注册名 | 工具 |
| --- | --- |
| `workflow` / `token-io-decoupling-workflow` | `workflow_capabilities`、`rules_get_context`、`workflow_generate_decision_context`、`workflow_select_child_effort`、`workflow_select_child_role`、`workflow_select_executor`、`workflow_select_child`、`workflow_assess_output_tokens`、`task_plan_update`、`task_plan_complete`、`task_plan_archive`、`workflow_evaluate`、`evaluate_control_checkpoint` |
| `root` / `token-io-decoupling-root-agent-tools` | `workflow_open`、`delegation_reserve`、`delegation_unreserve`、`delegation_bind`、`slice_check`、`slice_release`、`workflow_transition`、`parent_get_worker_summary`、`workflow_reconcile` |
| `worker` / `token-io-decoupling-worker-agent-tools` | `worker_get_assignment`、`worker_record_progress`、`worker_get_evidence`、`worker_report_blocker`、`worker_get_recovery_context` |
| `share` / `token-io-decoupling-share-tools` | `database_schema_status`、`state_get`、`record_evidence` |

Profile 控制工具发现，不授予权限。没有可信宿主通道时，公共能力/规则读取可成功，schema 状态不检查状态路径而返回 unavailable，受保护调用则拒绝缺失绑定。Workflow/Control 判断要求经过验证的 Root。共享读取与证据写入每次都解析经过验证的角色；Worker 读取拒绝非空的 Root `index_page` 游标。

三个 Native 任务计划工具使用单独配置且绑定项目的 Serena 后端，不使用 Enhanced 数据库。没有显式注入或受信任启动 factory 时，保持 `unavailable`。其 payload、配置、确定性检查、测试和保护限制由[任务计划生命周期工具](TASK_PLAN_TOOLS_zh_cn.md)负责。不会自动加载 Serena 配置或发起模型请求。

Canonical Python 实现使用架构契约列出的独立包名。重命名后的 `token_io_decoupling_mcp` 适配命名空间承载原 façade 模块和默认 factory 的仅公共接口行为；`python -m token_io_decoupling_mcp.cli` 仍可使用。旧 `token_io_mcp` 导入命名空间不再作为通用 API 暴露。两个不可变 v1 迁移源仍保留历史字节中的 `token_io_mcp.models`；state migration loader 仅在导入期间临时提供 `DatabaseKind` 别名，随后移除。直接导入 frozen state 迁移模块会绕过此局部加载器，不受支持；需要直接导入时请使用重命名后的 adapter migration 路径。兼容文件分别由 core、state 或 launcher 负责，wheel 路径不重复。本 workspace 不导出旧四个 console script，也不导出之前的 `token-io-mcp` console script。

## 能力报告诊断

`workflow_capabilities({})` 是无参数公共工具。它保留顶层摘要，新增 `schema_version: 1` 的 `capability_details`。每个详情项包含 `status`、`reason_code`、安全的 `message`、诊断 `source` 和 `next_step`。

| 详情分组 | 含义与边界 |
| --- | --- |
| `support.host_adapters` | 内置 Desktop 身份/守卫的静态支持：`unavailable/adapter_not_implemented`。这不是 provider 探测；注入的可信 provider 仍可能验证成功。 |
| `configuration.caller_match` | 启动配置 `required/configured_required` 或 `disabled/configured_disabled`。公共发现不验证请求调用方元数据。 |
| `configuration.api_decisions` | 持久化建议配置 `enabled/configured_enabled` 或 `disabled/configured_disabled`。disabled 是正常配置。逐调用工具独立，不测试 API 是否可用。 |
| `runtime.binding` | 当前 Session 关系和基线守卫。成功仅含角色（`parent` 或 `worker`），不含身份值；具体操作授权另行检查。 |
| `runtime.binding_transport` | 类型分类：已知继承宿主通道为 `available/known_transport`，自定义 provider 为 `unverified/transport_not_reported`。识别类型不证明当前通道健康。 |
| `runtime.server_mode` | 启动准入（`embedded` 或 `public_only`）。后续诊断不扩大注册范围，不绕过检查。 |

绑定诊断结果：

| 状态 / 原因代码 | 证据与下一步 |
| --- | --- |
| `unverified/provider_not_configured` | 默认拒绝 provider，未尝试探测。使用 Native 或配置可信宿主集成。 |
| `available/baseline_verified` | Session 关系和基线守卫通过。另行检查目标操作守卫和调用方上下文。 |
| `unavailable/required_guards_missing` | 缺少基线守卫。修正宿主绑定，不绕过检查。 |
| `unavailable/session_identity_mismatch` | 角色/Session 关系无效。修正宿主提供的身份。 |
| `unavailable/permission_denied` | provider 抛出非 `BindingError` 的 `PermissionError`。由宿主维护者检查权限。 |
| `unknown/binding_unavailable` | `BindingError` 无法区分拒绝、超时或协议故障。查阅可信宿主诊断，不猜测根因。 |
| `unknown/probe_failed` 或 `unknown/invalid_binding_response` | 意外异常或无效类型结果。修复 provider 后再进行受保护访问。 |

`BindingError` 继承 `PermissionError`，因此优先分类前者。一次报告最多读取一次绑定，可能联系已配置的宿主通道，不发送 API 请求，不检查状态或路径。固定解释不回显异常、凭据、身份值、路径或任意 provider 属性。

非 embedded 的旧摘要保持 `enhanced_binding: unverified` 和 `binding_transport: unavailable`，即使后续探测成功也不改变；详情区分当前验证与启动准入。embedded 的绑定摘要仍为 `available`/`unavailable`。传输摘要仅使用 `authenticated_inherited_unix_socket` 或 `embedded_provider`，不回显自定义标签。任何结果均不自动启用 Enhanced 或授予权限。

### 已安装客户端运行时检查

`tests/unit_tests/test_real_clients.py` 中的 `real_client` 用例运行真实安装的 Codex CLI，以及 ChatGPT Desktop 随附的 Codex 可执行文件。它们通过各自可执行文件的 app-server MCP 接口测试，不模拟客户端传输或宿主身份。覆盖范围是 MCP 宿主运行时边界，不包含 Desktop GUI 操作、已运行的 daemon，或已认证的 Enhanced 宿主绑定。

获得创建临时测试线程和进程的授权后，从 `mcp/` 执行：

```sh
TOKEN_IO_RUN_REAL_CLIENTS=1 uv run --managed-python --locked -- pytest -q -s tests/unit_tests/test_real_clients.py
```

CLI 默认使用 `PATH` 中的 `codex`；Desktop 默认使用 `/Applications/ChatGPT.app/Contents/Resources/codex-cli/CodexCLI.app/Contents/MacOS/codex`。可通过 `TOKEN_IO_CODEX_CLI_PATH` 和 `TOKEN_IO_DESKTOP_CODEX_PATH` 指向其他真实安装位置。覆盖值是调用方提供的路径，不构成客户端身份证明。证据包含解析后的可执行文件路径、实际版本、可执行文件 SHA-256、被测源码指纹和通过的检查；修改 JSON-RPC 客户端名称不能证明客户端覆盖。

每个用例启动独立的真实 app-server，通过进程内 `mcp_servers` 覆盖值，用安全占位条目禁用继承的已配置 server，并启用当前 workspace 的 workflow server。仅读取已配置 server 名称和传输类型，不复制 URL、参数、环境变量值或凭据。它断言继承的已配置 server 不暴露工具；客户端可保留内置平台服务，测试不调用这些服务。它验证目标的无参 schema 和新版描述，调用 `workflow_capabilities` 并检查结构化诊断，确认 `workflow_evaluate` 拒绝缺少可信绑定的调用。每项使用一个 ephemeral 线程，不启动模型 turn，并通过终止自己创建的进程组释放仅驻内存的线程及 MCP 子进程。不修改用户配置或已安装 MCP 包，此能力检查不需要模型 API 请求。运行环境必须允许启动和清理这些进程。

普通 pytest 跳过两项，不探测已安装客户端。显式启用后，客户端缺失、权限失败、协议错误或旧能力响应都会使测试失败，不跳过，也不回退到模拟客户端。已有 SDK、Mock 和安装版 stdio 检查继续保持各自较窄的证明范围。运行时检查通过不证明既有客户端会话已经重载更新后的 MCP 安装；该会话仍需单独验证安装和重载。

## uv tool 安装与 Codex setup

使用[安装脚本](../scripts/install-codex-mcp.sh)，从任意工作目录一次完成包安装或更新及 Codex 配置：

```sh
bash /absolute/path/to/skill/scripts/install-codex-mcp.sh
```

前置条件为 Bash 3.2 或更新版本（包括 macOS 的 `/bin/bash`）、`uv` 和 Codex CLI；`uv` 与 `codex` 必须位于 `PATH`。脚本相对自身定位 `mcp/`，针对该源码执行 `uv tool install --force --reinstall --managed-python --python 3.14`，通过 `uv tool dir --bin` 获取 bin 目录，再以绝对路径调用安装后入口的 `setup codex`。uv 会解析已声明的本地 workspace 依赖；即使只修改了依赖的源码或打包规则，`--reinstall` 也会更新它们。工具 bin 目录无需位于 `PATH`，不必手动切换目录、激活虚拟环境或另行执行 setup。重复运行会从当前 checkout 更新此工具，不会卸载旧 `token-io-mcp` 工具。

每项操作只需调用脚本一次，在上述命令后追加相应选项即可：

| 选项 | 操作 |
| --- | --- |
| `--dry-run` | 输出安装和 setup 计划，不运行安装/setup 命令或读写配置；真实运行前，未来的工具 bin 路径以符号占位表示。 |
| `--profile root` | 只注册指定的 `workflow`、`root`、`worker` 或 `share` profile；安装包仍包含全部 profile。 |
| `--all` | 显式选择默认的四个 profile，不能与 `--profile` 同用。 |
| `--replace` | 允许 setup 替换冲突或已禁用的注册；省略时仍拒绝冲突。 |
| `--python VERSION` | 指定 uv 托管的 Python 版本，替代默认的 `3.14`。 |
| `--help` | 显示用法，不安装或修改配置。 |

脚本在安装前验证参数及必需命令。某阶段失败后停止后续阶段并返回非零状态。安装和注册是不同副作用：若安装后 setup 失败，更新后的工具仍保留安装状态；重新运行前先检查 setup 的部分状态报告。注册设置保留和转发检查仍由现有 setup helper 负责。成功后重新加载受影响的服务；脚本不会重启客户端或提供凭据值。

Setup 使用一个核验后的可执行文件绝对路径和不同 profile 参数注册上表的四个服务名，并自动将两个必需环境变量名合并到各自的 `env_vars`。自行单独管理工具安装的用户仍可直接调用 `token-io-decoupling setup codex`。例如，一次安装后命令调用即可只注册 root profile 并修复其转发：

```sh
token-io-decoupling setup codex --profile root
```

Setup 与启动的分离参考 [Serena 的客户端 setup 实现](https://github.com/oraios/serena/blob/main/src/serena/config/client_setup.py)。本入口从当前安装环境的 scripts 目录及精确的分发包入口元数据解析可执行文件，不根据启动目录推断项目或身份。

安装后命令的 `setup codex --dry-run` 输出所选 profile 的 JSON 参数向量及变量名转发计划，不运行子进程，也不读写配置。真实 setup 在注册写入前验证本地配置并探测 CLI，读取服务清单及嵌套 `transport` 数据。已启用且解析后的命令与 `start-mcp-server --profile <profile>` 参数匹配的注册会跳过重新注册，但仍补齐缺失的转发变量名。冲突或已禁用条目要求 `--replace`。替换使用官方同名 upsert，不先删除旧条目。后续转发失败会与已经应用的注册分开报告；重试前先检查报告中的部分状态。不打印捕获的配置或子进程输出。

由于 Codex upsert 会替换注册项，setup 会将原设置暂存在内存中，每次 upsert 成功后连同转发声明一起恢复，再处理下一个 profile。替换 stdio 注册时保留附加设置和已有转发变量名，只改变入口、profile 参数及预期的启用状态。HTTP 转为 stdio 时保留通用工具策略和超时设置，但移除旧传输与认证字段。后续 profile 失败时，报告会区分已完成的注册/转发和待处理项。需要保留这些设置的替换应使用 setup。

新入口及注册核验通过后，从本仓库旧四命令工具迁移的环境可用 `uv tool uninstall token-io-mcp` 移除旧分发包。保留其他工具、服务和设置，并重新连接 MCP 客户端以加载新启动命令。Setup 不建立可信宿主绑定。

协议目标仍为 `2026-07-28`。SDK 子进程测试核验协商与调用；实际可信宿主集成仍需独立证据。

### Codex stdio 环境变量转发

安装脚本已通过 setup 自动处理转发。若仅修复已有注册的转发，从任意工作目录调用一次[独立修复脚本](../scripts/configure-codex-mcp-env.py)：

```sh
uv run --managed-python -- /absolute/path/to/skill/scripts/configure-codex-mcp-env.py --server dev-workflow-standards-tools
```

追加 `--dry-run` 可改为只预览而不写入。已有安装也可用 `token-io-decoupling setup codex-env --server NAME` 完成相同操作；两者是替代入口，无须连续执行。重复 `--server NAME` 可在一次文件操作中更新多个已有 stdio 注册项。默认合并 `OPENAI_API_KEY` 和 `OPENAI_BASE_URL`；重复 `--env-var NAME` 可改用自定义变量名列表。`--config /absolute/path/config.toml` 显式选择文件，否则目标为 `$CODEX_HOME/config.toml`，未设置 `CODEX_HOME` 时使用 `~/.codex/config.toml`。脚本通过 PEP 723 元数据让 uv 准备 TOML Kit，并从当前 checkout 导入 helper，因此不依赖已安装的 MCP 包或 Codex CLI。安装后的命令使用相同 helper。

Helper 只合并所选 `env_vars`，保留其他变量名、注释、设置和文件权限。没有缺失变量名时，重复成功运行不改变文件字节或修改时间。写入通过同目录临时文件完成，并在替换前检测输入是否发生变化；应避免其他进程同时写配置，因为这不是跨客户端事务。文件或服务条目不存在、非 stdio 服务、TOML 或字段类型无效、目标为符号链接、所需变量存在冲突的远端来源、写入失败时，均返回安全错误。它不会创建服务条目、打印配置值或发起 API 请求。此修复命令的 `--dry-run` 会读取并验证所选文件，但不写入；上文的注册 dry-run 则明确不检查配置。

TOML Kit 文档说明了一项格式保留例外：扩展数组表的乱序子表在重新序列化时会被重新排列，锁定版本也存在这一行为。计划写入修复前，helper 会检查原文档未经修改时能否逐字节往返还原；不支持的排版会被拒绝且不写入，避免静默移动无关内容。注册 setup 也在 upsert 前的预检中执行相同检查。若独立修复命令发现转发已经完整，即使存在这种排版也仍保持无改动。

下面是不完整的结果示例。手动编辑时须保留已有 `command`、`args`、审批设置及其他转发变量名：

```toml
[mcp_servers.token-io-decoupling-workflow]
env_vars = ["OPENAI_API_KEY", "OPENAI_BASE_URL"]

[mcp_servers.token-io-decoupling-root-agent-tools]
env_vars = ["OPENAI_API_KEY", "OPENAI_BASE_URL"]

[mcp_servers.token-io-decoupling-worker-agent-tools]
env_vars = ["OPENAI_API_KEY", "OPENAI_BASE_URL"]

[mcp_servers.token-io-decoupling-share-tools]
env_vars = ["OPENAI_API_KEY", "OPENAI_BASE_URL"]
```

Codex 自身的环境中必须持有这两个非空白变量。`env_vars` 允许将对应变量转发给各自单独启动的 MCP 进程；它不会读取 Shell 配置或 `.env` 文件，也不会复制其他终端的环境。不要将真实值写入仓库文件、setup 参数、日志或示例。字段含义见 [Codex MCP 配置参考](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)。

新注册和已匹配注册都会在 setup 时合并转发声明，`--replace` 后也会执行相同合并。安装脚本已自动包含 setup；单独执行 `uv tool install` 仍不会注册服务或提供凭据。修改配置后重新加载受影响的 MCP 服务；若客户端没有重载机制，退出后重新打开客户端以创建新服务进程。运行中的进程不会自动获得修改后的配置。

终端调用成功而 MCP 请求报告缺配置时，检查客户端进程环境、各注册项的转发变量名，以及服务是否已重新创建。只记录变量存在性及是否非空白。当前 Decisions advisor 在任一必需值缺失或为空白时，在创建 SDK client 之前返回 `fallback`，原因为 `missing_credentials`；不要套用其他服务的 `missing_api_key` 错误名称。转发不会启用 API 请求、授予出站数据权限或建立可信宿主绑定；下文的独立要求仍须满足。



## 已认证的宿主通道

`token_io_decoupling_core.host_binding` 中的 `HostChannelBindingProvider` 和 `serve_host_binding_channel` 将 CLI 连接到可信宿主已有的 `BindingProvider`。宿主在 MCP 请求参数之外，将一个真实 Session 绑定到一个已连接的 Unix stream socket，再把该连接的描述符传给非特权 CLI 进程，并服务另一端。supervisor 必须将服务端端点保留在可信边界内，且不得将同一通道重新分配给其他 Session。宿主启动所选可执行程序，例如 `token-io-decoupling start-mcp-server --profile root --host-fd N`，其中 `N` 是不小于 3 的继承描述符；该参数只定位传输通道，不提供身份或权限。

CLI 使用操作系统凭据认证对端：Linux 使用 `SO_PEERCRED`，macOS 使用原生 `getpeereid` 调用。此实现将可信对端固定为 UID 0，并拒绝自身以 UID 0 运行的 CLI。Agent 当前用户创建的 socket 无法建立信任。不支持的凭据能力、无效描述符或启动绑定失败，都会终止所请求的绑定启动。内核机制见 [Linux Unix socket 手册](https://man7.org/linux/man-pages/man7/unix.7.html)和 [Apple 对端凭据手册](https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man3/getpeereid.3.html)。

绑定启动的 CLI 从操作系统账户数据库获取当前有效用户的主目录，并将其下的 `.local/state/token-io-decoupling` 作为状态根目录。调用方控制的 `HOME` 不能重定向该路径；账户映射不可用或无效时拒绝启动。可信 Python embedding 仍保留 factory 的显式 `state_root` 参数。

桥接在启动时锁定项目、Root、当前 Session、parent 和角色。每次受保护调用都会重新向宿主读取当前能力与守卫证据；撤销或身份变化会使调用被拒绝。子身份验证使用宿主当前的 parent 身份。线协议只接受两种绑定操作，限制帧大小并设置有限超时；格式错误或不匹配的响应直接拒绝，不重试。失败通道不能通过后续响应重新获得信任。

宿主必须先落实实际 sandbox、路径与 Worker store 边界，再报告相应守卫。内核认证只确认可信 supervisor，不会创建这些守卫，也不证明某运行时的 Session 映射正确。此包提供桥接及宿主侧服务 API，不提供特权服务安装器，也不构成已经验证的 Codex/ChatGPT Desktop 运行时集成。普通 MCP 客户端配置不能凭空建立继承的特权通道。既有测试 provider 和模拟对端凭据的测试仍属于合成证据；未修改认证逻辑的同用户通道拒绝测试覆盖真实本地凭据边界。

声明实际运行时集成前，必须通过该运行时的 MCP 连接验证 Root 初始化、证据插入、状态转换及回读；验证真实释放且绑定的 Worker 能读取任务并只写入自己的进度/证据；并在实际宿主守卫下检查撤销和跨 Worker 拒绝。现有客户端需要重启或重新连接，才能加载改变的启动参数与工具清单；编辑 checkout 不会改变已经运行的 MCP 进程。

[Codex 调用者匹配](CODEX_CALLER_CONTEXT_zh_cn.md)说明对已有可信宿主绑定可选启用的 `--codex-context` 请求匹配门禁。它消费 SDK 请求元数据，不增加身份认证来源。

## 真实 API 请求的必需配置

Root 和每个受委派的 Agent 都必须在项目功能代码及测试/smoke 代码中遵守此限制：每次真实 API 请求前，从本地进程环境读取 `OPENAI_API_KEY` 和 `OPENAI_BASE_URL`。两项都必须存在且非空，仅含空白字符也视为无效。缺少任一项或任一项无效时，不得创建 SDK client 或发送真实请求，改走文档规定的回退路径。

不得使用硬编码密钥或端点、调用方提供的替代值或 SDK 的默认端点。必须在实际调用时读取这两项本地值，并显式传给 SDK；不得打印或持久化其值。合成配置仅可用于不发送网络请求的 Mock。

可选检查点建议仍默认关闭。其真实请求还必须具备显式启用及出站数据授权；本文档本身不授予这些权限。普通测试套件使用 Mock，真实 smoke 测试需要单独显式 opt-in，并遵守相同的双环境变量要求。

经过授权的 embedding 通过 factory 的 `decisions_config` 参数传入 `DecisionsRuntimeConfig(enabled=True, outbound_data_permitted=True)` 启用建议。两个评估工具的可选 `semantic_input` 仅限任务意图、输出类别、Contract 变化、验证影响和 Control。返回中 Core 结果与建议分开；未提供语义输入时保留原有 Core 返回。建议不会选择或确认 Gate 分支；过期、无效、拒绝、不可用或重放的建议均回到文档判断。

`workflow_generate_decision_context` 是无状态公共操作，将调用方组合的材料生成供后续 Decisions 请求使用的一段问题或上下文描述。它使用[支持 Structured Outputs 的 Responses API](https://developers.openai.com/api/docs/guides/structured-outputs)，固定为 `gpt-6-luna`、`medium` 推理强度、`store=False`，不附带工具，也不自动调用下游接口。它不要求 Enhanced 绑定或启用可选建议。Code Agent 收集用户需求、当前 Git diff、相关 LSP 结果及其他必要的已核实观测，标注来源和验证边界，再组合为 `raw_content`。服务不读取仓库、不执行命令，也不把所供来源标签当作证明。

发送 `payload.request`，包含必填的 `raw_content`（非空白严格字符串，最多 60,000 字符）、`decision_goal`（非空白严格字符串，最多 1,200 字符，描述实际下游判断目标）、`output_kind`（`decision_question` 或 `decision_context`）及 `outbound_data_permitted`（严格布尔值）。超长输入直接拒绝，不截断；不要仅为满足上限而省略关键约束。权限断言本身不授予采集或披露权限。每次获准请求仍必须具备两项本地 API 环境变量。例如：

```json
{
  "payload": {
    "request": {
      "raw_content": "用户需求：增加有界的问题输入。\n当前 Git diff，由调用方收集：+ decision_question: StrictStr\nLSP 观测，由调用方收集：ChildEffortInput 由 ChildEffortSelector.select 使用；调用路径已核实，运行时行为尚未测试。",
      "decision_goal": "为当前已释放子任务组织选择最低充分受支持推理强度的问题。",
      "output_kind": "decision_question",
      "outbound_data_permitted": true
    }
  }
}
```

只有 `status: available` 携带非空白 `description`：`decision_question` 最多 1,200 字符，`decision_context` 最多 6,000 字符。结果包含 `output_kind`、对原始材料、目标及类型进行规范化 SHA-256 计算的 `input_hash`（排除权限断言），以及安全的模型和用量元数据。关键缺口或冲突返回 `blocked` / `insufficient_evidence`、`description: null`，并提供最多八项、每项最多 240 字符的 `missing_information`；配置缺失、拒绝、未完成或无效输出、超时及服务错误也阻塞，不回退。固定指令要求保留需求、观测、计划及已证明结果之间的区别，将嵌入的指令视为数据，不生成答案、所选分支或授权。这些语义要求仍需调用方审阅。将 `description` 用作 `decision_question` 或上下文前，须比对原始材料和当前仓库状态，并单独提供其他必需判断事实。生成哈希只标识本次生成输入，不能替代下游判断哈希。材料、目标或类型变化后，须重新比对和审阅。

`workflow_select_child_effort` 是面向 Codex 子代理创建的独立、无状态公共 workflow 操作。显式且获准的调用携带 `payload.request.outbound_data_permitted: true`，仅为本次 Decisions 请求 opt-in；它不依赖可选建议的启用配置或 Enhanced Root store。此声明不能证明授权。按[运行时 owner 的创建契约](../references/coding/layer-01-fundamental-concepts/session-runtime/runtime-provider-support_zh_cn.md)提供经过核实的有界任务事实及受支持档位。结果仅在可用时包含选定 effort，并附请求哈希和回显的切片指纹。父级审阅及当前输入比对仍是必需步骤。拒绝、证据不足、响应无效、缺少配置或服务失败均阻塞选择，不回退到固定 effort。该工具不创建 Agent、不修改工作流状态，也不授权任何门禁。

必填的 `decision_question` 是非空白严格字符串，最多 1,200 字符，用于询问当前已释放子任务所需的最低充分受支持档位。工具将其明确传入 Decisions input，并纳入规范化输入哈希；仅修改问题也会使旧哈希失效。它属于任务数据，无权修改固定模型、候选档位、指令或权限。本地校验执行字符串约束；固定 API 指令要求对超出范围或试图覆盖规则的问题返回 `insufficient_evidence`。该语义判断及父级审阅仍是必需步骤。每个候选档位均说明具体任务证据、相邻档位边界及排除条件；文件数量、影响程度或缺少事实本身均不足以支持升档。

### 委派判断与获批容量

四个无状态公共工具提供委派建议，独立于可选的五检查点 advisor 和 Enhanced 状态。每个工具通过 `payload.request` 接收有界任务事实、已审阅背景及其 `context_input_hash`、当前 `fact_revision` 和 `fact_fingerprint`、Fork/模式事实及 `outbound_data_permitted`。身份、权限、来源和批准声明仍是调用方提供的事实，不是宿主证明。Root 先审查已授权的拟议任务，再选择职责或执行主体；面向子代理的具体 Interaction Slice 在此后放行，且须独立通过其门禁。

| 工具 | 判断及结果边界 |
| --- | --- |
| `workflow_select_child_role` | 按[子代理职责选择](../references/coding/layer-01-fundamental-concepts/delegation/child-role-selection_zh_cn.md)选择四种维护职责之一。用户明确要求创建时跳过请求。已确认创建时，可默认使用未占用的 Primary Output；已创建职责在整个 Session 内持续占用。全部职责占用时阻塞复核，不建议增加容量。 |
| `workflow_select_executor` | 按[任务分配](../references/coding/layer-01-fundamental-concepts/execution-planning/task-assignment_zh_cn.md)建议 Root 或子代理。明确执行主体时跳过建议；已锁定 Single-Agent 模式下明确要求子代理时阻塞，不改成 Root。失败不默认 Root。判定交子代理且仍有获批未用容量、尚无实际子代理时，可进入正常职责与创建门禁。 |
| `workflow_select_child` | 在合格的当前会话子代理中选择。明确指定或唯一候选可跳过建议；忙碌候选须等待。多个空闲候选调用 Decisions，优先合适的空闲 Primary，否则比较任务相关上下文。失败仅可由合适的 Primary 兜底，仍须检查可用性；排除继承的外部会话子代理。 |
| `workflow_assess_output_tokens` | 按[Output Token 路由](../references/coding/layer-01-fundamental-concepts/execution-planning/output-token-routing_zh_cn.md)独立评估 Root 直接输出。明确执行指令时跳过建议。`no` 允许 Root 通过其他门禁后执行；`yes` 禁止 Root 立即输出，须用适任空闲子代理或挂起等待。有独立授权的创建仍可走正常门禁；输出建议本身不授权创建。 |

获准的 API 请求在每次调用时明确读取非空白的 `OPENAI_API_KEY` 与 `OPENAI_BASE_URL`，只用 `gpt-6-luna`，不自动重试或请求后备模型。工具输入不能覆盖模型或端点。公共[判断背景生成](../references/coding/layer-01-fundamental-concepts/execution-planning/decision-context-generation_zh_cn.md)操作复用 Responses 生成供审阅的背景；问题生成可选。其指令现来自当前 owner 的通用规范；`source_policy_hash` 标识加载的规则，成功请求期间规则发生变化时以 `stale_policy` 阻止复用。

选择器通过 `RuleLoader` 加载当前 owner 指令和具体候选描述。结果区分 `available`、`skipped`、`fallback`、`blocked` 和 `stale`，带有请求/背景/事实及来源策略哈希。实际效果前，Root 必须与当前证据重新核对。缺少配置或必要策略时在请求前阻塞；过期规则必须刷新，不能转为兜底。选择器不会创建子代理、派发工作、修改预算或建立可信绑定。这些工具只接收一个已界定任务，不会将指令分解成多个任务。

受保护的 Root `delegation_reserve` 仅在当前未分配容量耗尽后接受可选 `budget_approval`。Root 须通过 `user_approval` 引用用户实际的明确批准，为不同的未占用职责精确申请当前数量加一。原有绑定、guard、revision 和幂等要求继续生效。事务保留旧来源、记录批准、增加一个槽位并预留该职责；重放不能重复增加。已有未分配容量无需扩额。批准绝不允许重复职责或替代子代理，见[委派数量门禁](../references/coding/layer-01-fundamental-concepts/delegation/delegation-mode-count-gate_zh_cn.md)。

创建开始之前，受保护的 Root `delegation_unreserve` 可以取消角色预留，使同一个尚未使用的槽位可以重新规划。它要求明确证明创建尚未开始的证据、当前 revision、幂等键以及原有 Root binding/guard。已绑定或身份不明，以及具有 Slice、派发或 Worker 历史的 allocation 均拒绝撤销。该证据是 Root 声明，不是独立宿主证明。撤销只清除尚未使用的预留，不减少锁定数量，也不释放子代理创建后的角色或身份。再次选择或预留新角色前必须刷新 allocation 事实。

### 真实 API 集成测试

`tests/real_api_tests/` 下的 `real_api` 用例覆盖真实 Responses 背景生成、子代理 effort Decisions、经协商的进程内 MCP 生成到强度选择链路，以及四类委派判断：新子代理角色、Root/子代理执行主体、已有子代理选择和 Output Token 路由。它们使用合成的需求、diff 文本、Session 事实与 LSP 观测，不采集仓库或宿主数据。委派用例先生成并审核背景，再请求判断，随后核对预期结果、输入哈希及当前策略哈希。这些检查证明真实 API 和 MCP handler 行为，不证明可信桌面宿主绑定或稳定的语义排序。

普通 pytest 运行会收集并跳过这些用例，在访问凭据或创建客户端前结束，即使已有凭据也不会启用。只有精确的 `TOKEN_IO_RUN_REAL_API=1` 才启用它们。启用后，`OPENAI_API_KEY` 或 `OPENAI_BASE_URL` 缺失或空白会使测试失败，不跳过，也不替换为 Mock。请求使用已配置的端点和固定 `gpt-6-luna`；不回退到其他端点或模型，也不自动重试。测试作用域抑制 SDK/HTTP 日志，只报告安全的状态和原因，不输出凭据、端点值或原始服务错误。获得显式授权后，从 `mcp/` 运行：

```sh
TOKEN_IO_RUN_REAL_API=1 uv run --managed-python --locked -- pytest -m real_api tests/real_api_tests/ -q
```

旧的任务意图 advisor smoke 保持独立，使用自己的启用开关。获得该真实合成请求的显式授权后，确保两项本地环境变量已配置，再从 `mcp/` 运行：

```sh
TOKEN_IO_RUN_REAL_DECISIONS=1 uv run --managed-python --locked -- python tests/real_api_tests/decisions_real_smoke.py
```

没有 opt-in 时，脚本不发请求。它使用临时 Root 数据库和合成可信 provider，直接调用 `DecisionsAdvisor`，仅报告安全的状态、原因、分类元数据、选项和用量。它不证明真实宿主绑定，也不证明真实 API 请求经过了 MCP handler。MCP handler/协议测试使用模拟 API transport。advisor 在实际调用时读取两项必需的本地变量；脚本和项目都不提供替代凭据或默认端点。

## 构建、规则资源与安装检查

从 `mcp/` 构建八个 wheel 与源码分发包：

```sh
uv build --all-packages --managed-python --python 3.14 --out-dir /tmp/token-io-dist
```

规则资源及自定义构建 Hook 由 core 包负责。Canonical 注册表仍为 `mcp/rule-registry.json`；构建产物包含其英文/中文 owner 标题的有界摘录。Core sdist 携带自己的 `rule_sources`，脱离仓库构建时不借用相邻 checkout。默认 `token_io_decoupling_core.rules.RuleLoader` 读取打包快照；源码开发必须明确提供仓库根目录。修改 Markdown 不会更新已安装的 wheel，需要重新构建和安装。

构建还打包 `child-role-selection`、`task-assignment`、`output-token-routing`、`session-role-ownership` 和 `decision-context-generation` 的英中通用规范。这些是固定允许列表中的策略资源，不新增 Core 检查点 ID。`tests/unit_tests/test_build_artifacts.py` 验证脱离仓库的 sdist 到 wheel 构建，并通过打包的 `RuleLoader` 加载这些策略及核对内容哈希。

已发布迁移文件属于 state 包，保持原始字节不变，因为数据库历史记录了源码校验和。state loader 为两个 v1 文件所需的历史导入 `token_io_mcp.models.DatabaseKind` 临时提供模块别名，并在导入后移除。直接导入 frozen state 迁移模块会绕过此局部加载器，不受支持；需要直接导入时请使用重命名后的 adapter migration 路径。命名空间迁移不授权改写历史、校验规则或 schema 版本。测试同时覆盖旧历史与升级，以及新建数据库。

[MCP CI 工作流](../.github/workflows/mcp.yml)在托管 Python 3.11 和 3.14 上执行锁定检查，并有独立的安装版 wheel job。用 `uv export --no-emit-workspace` 导出第三方构建/运行时约束，构建再加 `--all-groups`，运行时再加 `--no-dev`。Workspace 成员由本地产物提供，不作为 editable requirements 导出。从脱离仓库的 wheel 集安装时，以产物目录作为 `--find-links`，安装根包 `token_io_decoupling-0.1.0-py3-none-any.whl`；保留已配置的索引以解析锁定的第三方依赖。完整命令见 CI。

临时安装使用命令局部的 `UV_TOOL_DIR` 和 `UV_TOOL_BIN_DIR`，均指向临时绝对目录。用锁定的 workspace 解释器运行 `tests/support/installed_stdio_smoke.py --cli /absolute/temporary/bin/token-io-decoupling`。脚本在 checkout 外、空 `PYTHONPATH` 下启动四个 profile 子进程，核验精确清单与绑定拒绝，检查两种语言规则，并在空 `PATH` 下运行 setup dry-run。源码根项目的 tool 安装另行检查。这些结果证明包与 stdio 行为，不证明实际宿主绑定或 GitHub Actions 已运行。

[文档工作流](../.github/workflows/multilingual-docs.yml)保留多语言、链接、路线验证器及扫描器回归；遍历时剪枝生成资源与环境，同时检查手写的 workspace 文档。

## Native 恢复开发检查

[Native 权威转交](../references/coding/layer-01-fundamental-concepts/enhanced-native-state/native-authority-transfer_zh_cn.md)和 [Native 对账](../references/coding/layer-01-fundamental-concepts/enhanced-native-state/native-reconciliation_zh_cn.md) owner 定义工作流边界。以下检查验证已实现的服务用例，不证明完整导出或宿主停写能力。

恢复开发使用临时数据库和合成绑定。状态服务的定向用例覆盖完整集合的显式裁定、比较历史保留、恢复 Revision/Epoch 新鲜度、尚未完成的补证请求及派发副作用阻断，也覆盖精确确认不掩盖旧冲突、恢复后首个 Slice 前的新鲜 Control、已确认派发的无副作用重放，以及超限旧快照的有界回读。迁移测试区分有证明的旧确认配对与格式错误或 Revision 不相邻的记录。从 `mcp/` 先运行定向用例，再执行完整套件：

```sh
uv run --managed-python --locked -- pytest tests/mock_api_tests/test_state_service.py -k native
uv run --managed-python --locked -- pytest tests/unit_tests/test_migrations.py
```

这些检查不证明宿主能够停止 Worker。受支持的实质差异恢复路径要求已有 Root 控制状态，且没有已绑定 Worker、活动 Worker Slice 或待确认派发。它裁定 Contract 来源与语义引用这一对字段，不重建缺失的身份、派发、生命周期或验收历史。不受支持的状态保持阻断并保留记录。证据引用和请求 Hash 提供审阅指针与完整性绑定；两者都不能认证调用方，也不能独立证明新鲜度或静默状态。

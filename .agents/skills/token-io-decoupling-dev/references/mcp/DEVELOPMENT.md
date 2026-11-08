# MCP workspace 开发指南


本指南负责 Python workspace 的开发、构建产物检查、uv tool 安装与 Codex setup。[架构契约](../../../../../instruction-compiler/sources/skill/WORKFLOW_ARCHITECTURE.md#独立服务)负责包职责与依赖方向；[Skill 入口](../../../../../instruction-compiler/sources/skill/SKILL.md)及其链接的 owner 仍是工作流权威。

MCP Server 面向本地可用的 Codex CLI，包括本地 Work 使用的本地 Codex CLI/app-server 路径。云端 ChatGPT 对话、远端 Work 和其他 Code Agent 不是直接客户端。如果其他 Agent 在自己的环境安装 Codex CLI，并按本仓库说明配置 Server，则仅支持该环境中的本地 Codex CLI 路径；不维护其他 Agent 或云端界面适配器。Server 不增加运行环境选择步骤。遵循[目录指令](AGENTS.md)。固定客户端范围不等于宿主集成已经验证；各操作仍按现有流程检查实际能力、可信身份、守卫和权限。

## 环境与检查

Workspace 包含五个分发包：可选根管理／完整安装、共享 core/transport，以及可独立安装的 tools/workflow 运行时。运行时成员拥有各自 console script，互不依赖。Workflow 拥有编译规则；tools 拥有计划、Memory、preflight 与物化。以下命令在 mcp/ 中使用托管 Python 和锁定依赖执行：

```sh
uv sync --managed-python --locked --all-packages --group dev
uv run --managed-python --locked -- pytest -c pyproject.toml
uv run --managed-python --locked -- ruff check --config pyproject.toml . ../.agents/skills/token-io-decoupling-dev/tests/mcp
uv run --managed-python --locked -- ruff format --config pyproject.toml --check . ../.agents/skills/token-io-decoupling-dev/tests/mcp
uv run --no-sync -- ty check --extra-search-path ../.agents/skills/token-io-decoupling-dev/tests/mcp --extra-search-path ../.agents/skills/token-io-decoupling-dev/tests/mcp/support src packages ../.agents/skills/token-io-decoupling-dev/tests/mcp
```

`ty` 覆盖根源码、测试、各库包及 core 构建 Hook。如需将环境放在 checkout 外，设置 `UV_PROJECT_ENVIRONMENT` 为临时目录的绝对路径。默认测试集仅在本地运行且不联网；真实 API 测试必须显式启用。文档工作可参考[项目开发指导](../../AGENTS.md)，并从仓库根目录运行适用的私有检查器和回归。

### 测试组织

每个新增或修改的测试均按实际依赖与行为分类：

| 目录 | 职责 |
| --- | --- |
| `../.agents/skills/token-io-decoupling-dev/tests/mcp/mock_api_tests/` | 使用 mock、fake 或 stub 替代协作者、宿主绑定、API client 或 HTTP transport 的测试。 |
| `../.agents/skills/token-io-decoupling-dev/tests/mcp/unit_tests/` | 不模拟协作者、不请求真实 API，执行实际被测代码的确定性本地单元测试。 |
| `../.agents/skills/token-io-decoupling-dev/tests/mcp/real_api_tests/` | 必须显式启用、实际发送 Decisions 或 Responses 请求的测试及 smoke 脚本。 |

混合模块按测试用例拆分，marker 或文件名不能替代正确的目录归属。共享 fixture 和子进程辅助程序可以放在这三个用例目录之外，但不得成为未分类测试用例的存放处。迁移时保留断言、参数化与收集覆盖，同步更新导入、仓库根路径定位及 CI/脚本引用。普通 pytest 必须收集并跳过真实请求用例，且跳过前不读取凭据、不发送请求。后续新增测试同样遵守这些目录规则。

## 独立 MCP 可执行程序

MCP 运行时由两个分别安装的可执行程序组成。每个程序都不需要启动参数，即可启动 stdio server。`token-io-decoupling` 是用于 setup、Skill 安装和环境变量转发修复的管理 CLI，不是 MCP 运行时，也没有直接启动 MCP server 的默认行为。

| MCP 可执行程序 / Codex 注册名 | 工具 |
| --- | --- |
| `token-io-decoupling-workflow` | 11 个无状态工作流能力、事件、规则、建议和评估工具。 |
| `token-io-decoupling-tools` | 共 41 个工具：33 个开发工作流工具和 `materialize_decoupled_output`；见[两个 MCP 程序与 Codex 注册](TOOLS_REGISTRATION.md)。 |

使用一次 setup 命令注册两个可执行程序：

```sh
"$(uv tool dir --bin)/token-io-decoupling" setup codex
```

也可从已安装的 tool bin 目录取得可执行文件绝对路径，分别注册：

```sh
codex mcp add token-io-decoupling-workflow -- /absolute/path/to/token-io-decoupling-workflow
codex mcp add token-io-decoupling-tools -- /absolute/path/to/token-io-decoupling-tools
```

`workflow_check_event` 的有界请求、规则交付、结构／建议分层和可选原生 CLI 契约见[Workflow 事件与 Hook](WORKFLOW_HOOKS.md)。旧路由工具已移除，Agent 自行在上下文中保存状态，并根据简短流程指令选择执行路径。

只读工具 `validate_decoupling_compliance` 按操作员配置的 checkout 检查有界候选覆盖层。其请求、结果、启动 factory 和明确限制见[候选内容合规预检](CANDIDATE_COMPLIANCE.md)。它不授权或应用写入，也不替代仓库检查或最终验收。

仅供 Worker 使用的 `materialize_decoupled_output` 工具准备并检查有界输出产物，再通过独立授权的操作员服务应用产物。其请求、模板、授权与预检要求、启动选项 `--output-materializer-factory MODULE:CALLABLE`、结果和恢复边界见[Worker 输出材料化](OUTPUT_MATERIALIZATION.md)。可信 factory 返回 `OutputMaterializerConfig`；缺少配置时工具保持不可用，且不探测默认路径。

每个可执行程序都有固定发现清单；工具发现不授予权限。规则/工作流路径是无状态的，不需要数据库或宿主绑定。`workflow_evaluate` 和 `evaluate_control_checkpoint` 只检查调用方提供的类型化事实及声明的输入结构；其结果不会认证、授权、通过检查点、持久化状态或安排后续调用。若没有可信的启动时注入授权 provider 和单独授权，输出材料化仍不可用。

三个任务计划工具使用单独配置且绑定 checkout 的 Serena MemoryManager 后端。其能力结果报告 `project_root`、`storage_scope`、`repository_id`、`namespace` 和 `archive_namespace`；默认项目范围可配置为全局存储，让 linked worktrees 共享规划、独立仓库保持隔离。只有受信任的启动 factory 显式注入服务后，工具才可用。其 payload、配置、身份/路径映射、确定性检查、测试和保护限制由[任务计划生命周期工具](TASK_PLAN_TOOLS.md)负责。不会自动加载 Serena 配置或发起模型请求。

Canonical Python 实现使用架构契约列出的独立包名。两个 MCP 可执行程序分别安装并暴露固定清单。

[Memory 工具指南](SERENA_MEMORY_TOOLS.md)负责直接尾读/写入检查参数、本地路径解析、有界读取结果及匹配限制。这些工具用 Python 标准库读取当前项目 `.serena/memories/` 中的文件，不使用单独配置的任务计划后端。

## 能力报告诊断

`workflow_capabilities` 报告工作流自身的静态支持、可选 API 配置和安全绑定诊断（schema 版本 3），不导入或探测 tools 服务、Memory、计划存储、preflight 或物化。诊断不授予身份或权限。`tools_capabilities` 可选地报告 tools 后端、本地 Memory 绑定、preflight 和物化，不是任何操作的前置条件。未配置计划后端时不探测 Git 或 Memory 路径；已配置的全局存储可重新核验已有 Git 身份／根目录，不创建路径。

### 已安装客户端运行时检查

`../.agents/skills/token-io-decoupling-dev/tests/mcp/unit_tests/test_real_clients.py` 中的 `real_client` 用例运行真实安装的 Codex CLI，以及 ChatGPT Desktop 随附的 Codex 可执行文件。它们通过各自可执行文件的 app-server MCP 接口测试，不模拟客户端传输或宿主身份。覆盖范围是 MCP 宿主运行时边界，不包含 Desktop GUI 操作、已运行的 daemon，或独立的宿主身份认证。

获得创建临时测试线程和进程的授权后，从 `mcp/` 执行：

```sh
TOKEN_IO_RUN_REAL_CLIENTS=1 uv run --managed-python --locked -- pytest -c pyproject.toml -q -s ../.agents/skills/token-io-decoupling-dev/tests/mcp/unit_tests/test_real_clients.py
```

CLI 默认使用 `PATH` 中的 `codex`；Desktop 默认使用 `/Applications/ChatGPT.app/Contents/Resources/codex-cli/CodexCLI.app/Contents/MacOS/codex`。可通过 `TOKEN_IO_CODEX_CLI_PATH` 和 `TOKEN_IO_DESKTOP_CODEX_PATH` 指向其他真实安装位置。覆盖值是调用方提供的路径，不构成客户端身份证明。证据包含解析后的可执行文件路径、实际版本、可执行文件 SHA-256、被测源码指纹和通过的检查；修改 JSON-RPC 客户端名称不能证明客户端覆盖。

每个用例启动独立的真实 app-server，通过进程内 `mcp_servers` 覆盖值，用安全占位条目禁用继承的已配置 server，并启用当前 workspace 的 workflow server。仅读取已配置 server 名称和传输类型，不复制 URL、参数、环境变量值或凭据。它断言继承的已配置 server 不暴露工具；客户端可保留内置平台服务，测试不调用这些服务。它验证目标的无参 schema 和新版描述，调用 `workflow_capabilities` 并检查结构化诊断，确认 `workflow_evaluate` 拒绝缺少可信绑定的调用。每项使用一个 ephemeral 线程，不启动模型 turn，并通过终止自己创建的进程组释放仅驻内存的线程及 MCP 子进程。不修改用户配置或已安装 MCP 包，此能力检查不需要模型 API 请求。运行环境必须允许启动和清理这些进程。

普通 pytest 跳过两项，不探测已安装客户端。显式启用后，客户端缺失、权限失败、协议错误或旧能力响应都会使测试失败，不跳过，也不回退到模拟客户端。App Server、Mock 和安装版 stdio 检查继续保持各自较窄的证明范围。运行时检查通过不证明既有客户端会话已经重载更新后的 MCP 安装；该会话仍需单独验证安装和重载。

### Codex App Server 最终查看

测试通过标准库直接启动已安装的 `codex app-server`，以 stdio JSON-RPC 交互，无需额外 Codex Python SDK 依赖。[测试协调器](../../tests/mcp/support/final_codex_check.py)定义当前测试顺序。从仓库根准备项目环境，并调用唯一有序协调器：

~~~sh
uv sync --project mcp --locked --group dev
uv run --project mcp --no-sync python .agents/skills/token-io-decoupling-dev/tests/mcp/support/final_codex_check.py
~~~

协调器先检查编译新鲜度与编译器回归，再执行全部适用 MCP 测试、lint、格式、类型、文档回归、校验器及空白检查；任一失败即停止序列。仅在其全部通过后，构建当前产物、通过隔离临时 uv tool/bin 目录安装、测试已安装 stdio，再经仅测试使用的 App Server adapter 启动全新 Codex CLI。普通测试使用 fake，绝不启动真实 App Server。可选真实 API/客户端用例保留显式开关，并报告剩余跳过项。

全新 CLI 仅进行有界只读版本、发现、能力与中文规则检查，零 model turns。不得分配实现、规划、调试、委派、写入或任意 Shell 工作。Adapter 显式复用非空进程 OPENAI_API_KEY、OPENAI_BASE_URL，固定 gpt-6-luna、medium 并核实有效配置；缺失或冲突即失败，不回退到保存登录、其他端点、凭据、模型或强度。不得输出或保存凭据值及原始 App Server 诊断。

使用已安装 Codex CLI，可通过 TOKEN_IO_CODEX_CLI_PATH 选择，并隔离临时配置。不得修改用户设置或复用现有实例。当前会话不能动态重载 MCP，因此该检查验证新安装构建，不证明既有会话已重载。CI 仅执行政策和 fake 测试，不启动真实 App Server 查看。

## API 与工具恢复提示

child-effort、decision-context 和 delegation selector 每次调用只发出一个 API 请求；SDK 自动重试已关闭。其结果模型新增可空 `recovery` 提示，无提示时序列化为 `null`。`retry_eligible` 只表示候选；对于明确的瞬时传输、5xx 或已确认限流，`total_attempt_limit` 表示调用方跟踪的每个恢复过程最多三次调用（含首次调用）。服务不跟踪跨调用次数，也不自动重试。调用方在考虑重调前，须复核任务授权、请求 hash、当前 policy 以及任何结果/副作用。

认证、授权、配置、配额、未知错误、拒绝、格式错误/不完整响应和证据不足都不是重试候选。应解决原因、刷新并重新计算过期事实/policy 的 hash，或停止。恢复提示不会改变现有结果 status、reason、hash、fallback 或 authority。只有成功的 `available` selector 结果才可在通常门禁通过后用于后续工作。

可选建议是独立的无状态 API 操作；结构检查点评估既不调用 Decisions，也不持久化建议结果。恢复 metadata 适用于返回该信息的 API 操作，不会改变其结果 status、reason、hash、fallback 或 authority。仅在符合条件的瞬时失败且未超出调用方跟踪的尝试上限时重试，并先复核当前授权和输入。检查点评估不包含状态变更重放或已存结果行为。

## uv tool 安装与 Codex setup

### 使用 uv tool 安装可执行程序

将源码仓库放在普通开发目录中，不要放进 `~/.agents/skills/`。准备好 `uv` 后，从仓库的 `mcp/` workspace 目录安装根包；使用源码绝对路径即可在任意工作目录执行：

```sh
uv tool install --force --reinstall --managed-python --python 3.14 --with-executables-from token-io-decoupling-workflow --with-executables-from token-io-decoupling-tools /absolute/path/to/token-io-decoupling/mcp
```

uv 会在隔离的工具环境中构建并安装可执行程序及声明的本地 workspace 依赖。`--reinstall` 同时更新依赖、批准的编译指令资源及入口程序。这一步只安装程序，不注册 MCP Server，也不安装 Skill 指令。若安装已构建的 wheel，请提供同一批准批次的四个精确 wheel 路径（参见[构建产物检查](#构建规则资源与安装检查)）：

```sh
uv tool install --force --reinstall --managed-python --python 3.14 \
  --with-executables-from token-io-decoupling-workflow \
  --with-executables-from token-io-decoupling-tools \
  --with /absolute/path/to/wheels/token_io_decoupling_core-0.1.0-py3-none-any.whl \
  --with /absolute/path/to/wheels/token_io_decoupling_transport-0.1.0-py3-none-any.whl \
  --with /absolute/path/to/wheels/token_io_decoupling_workflow-0.1.0-py3-none-any.whl \
  --with /absolute/path/to/wheels/token_io_decoupling-0.1.0-py3-none-any.whl \
  token-io-decoupling
```

各文件名中的版本请使用实际构建版本。通过 `uv tool dir --bin` 定位 uv 工具 bin 目录，并以可执行文件完整路径调用，无须激活虚拟环境。例如：

```sh
"$(uv tool dir --bin)/token-io-decoupling" --version
```

### 标准安装可用范围

标准安装通过本地 stdio 提供有界、无状态的事件指令与事实结构校验。Workflow 不保存任务／运行状态，也不提供跨调用推进或恢复；Agent 自行在上下文中记忆这些信息。可选事件建议须有独立启动旗标和逐调用外发许可，24,000 字符交付默认值及原生 Stop 限制见 Hook 指南。独立 tools 拥有另行配置的任务计划服务，以及仅限启动项目已有 `.serena/memories/` 文件的只读 Memory 工具。除非配置可信 provider 和独立逐调用授权，否则输出 materializer 不可用。API 工具需要两个非空白 API 环境变量及逐调用出站授权。发现不代表已配置或已授权。

确保 Codex CLI 位于 `PATH` 后，一次注册两个 MCP 可执行程序：

```sh
"$(uv tool dir --bin)/token-io-decoupling" setup codex
```

Setup 会解析并核验当前 workflow 和 tools 可执行程序，然后使用空参数列表注册这两个目标。它保留任一目标表中的其他设置，并保持无关配置不变。它不会检查、分类、删除或迁移其他注册。`--dry-run` 会读取配置并仅预检当前两个目标表，但不启动 MCP 子进程，也不写入。注册或更新工具后重新加载受影响的 MCP Server。环境转发仅保存变量名，不提供变量值，也不建立本地会话上下文。

Memory 工具不需要额外安装选项或 Serena 包。从目标项目根目录启动 Codex；MCP 使用启动工作目录作为项目根，只读取 `.serena/memories/` 中的文件。它不搜索父级或兄弟项目。Memory 目录和所请求的文件必须已存在；缺失时返回非成功结果，不创建任何内容。文件操作使用 Python 标准库。详见[Memory 工具](SERENA_MEMORY_TOOLS.md)。

### 安装与更新入口

MCP 与 Skill 的安装、更新、脚本参数及失败恢复统一见[安装与更新](../../../../../INSTALL.md)。[公共安装脚本](../../../../../scripts/install-codex-mcp.sh)以 `--mcp` 选择 MCP，以 `--skills install|update` 选择 Skill；无参数仅打印帮助。

修改作者指令后，先通过本开发流程重新生成并验证批准资源，再安装包并更新受管 Skill。安装脚本不重新编译资源；只更新可执行程序不会更新已安装 Skill。更新后重载受影响的 MCP Server，并启动新的 Agent 会话。

Setup 使用两个经过核验的可执行文件绝对路径和空启动参数注册两个 MCP 命令。它合并必需 API 变量和可选代理变量的名称；tools 可执行程序还转发 `OPENAI_TIMEOUT_MAX_RETRIES`。它仅更新这两个目标表，保留其其他设置及无关配置，不会检查或迁移其他注册。见[两个 MCP 程序与 Codex 注册](TOOLS_REGISTRATION.md)。需要分别注册时，可使用上文两个直接 Codex 命令。

管理命令从当前安装环境的 scripts 目录及精确的分发包入口元数据解析自身路径。每个 MCP 可执行程序使用服务启动工作目录作为项目根；这不建立宿主身份。

安装后的 `setup codex --dry-run` 会输出两个目标注册的计划路径和空参数，不写入配置。真实 setup 会解析当前已安装的可执行程序，核验其 `tools/list` 清单，并以原子方式 upsert 仅有的两个目标表。它保留这些表中的其他设置和无关配置。更新保留文件权限模式，拒绝不支持的 TOML 布局，并在替换前检查输入文件是否已改变。避免并发配置写入：此检查不是全局锁。不会打印配置值或子进程输出。

若两个目标表都已正确，setup 不执行写入。它不会重写无关条目或管理其他服务注册。

协议目标仍为 `2026-07-28`。SDK 子进程测试核验协商与调用；实际可信宿主集成仍需独立证据。

### Codex stdio 环境变量转发

安装脚本的 `--mcp` 操作通过 setup 自动处理转发。若仅修复已有注册的转发，从任意工作目录调用一次[独立修复脚本](../../scripts/configure-codex-mcp-env.py)：

```sh
uv run --managed-python -- /absolute/path/to/repository/.agents/skills/token-io-decoupling-dev/scripts/configure-codex-mcp-env.py --server token-io-decoupling-tools
```

追加 `--dry-run` 可改为只预览而不写入。已有安装也可用 `token-io-decoupling setup codex-env --server NAME` 完成相同操作；两者是替代入口，无须连续执行。重复 `--server NAME` 可在一次文件操作中更新多个已有 stdio 注册项。默认合并 `OPENAI_API_KEY`、`OPENAI_BASE_URL`、`HTTP_PROXY`、`HTTPS_PROXY`、`ALL_PROXY`、`NO_PROXY` 及四个代理变量的小写形式；重复 `--env-var NAME` 可改用自定义变量名列表。`--config /absolute/path/config.toml` 显式选择文件，否则目标为 `$CODEX_HOME/config.toml`，未设置 `CODEX_HOME` 时使用 `~/.codex/config.toml`。脚本通过 PEP 723 元数据让 uv 准备 TOML Kit，并从当前 checkout 导入 helper，因此不依赖已安装的 MCP 包或 Codex CLI。安装后的命令使用相同 helper。

Helper 只合并所选 `env_vars`，保留其他变量名、注释、设置和文件权限。没有缺失变量名时，重复成功运行不改变文件字节或修改时间。写入通过同目录临时文件完成，并在替换前检测输入是否发生变化；应避免其他进程同时写配置，因为这不是跨客户端事务。文件或服务条目不存在、非 stdio 服务、TOML 或字段类型无效、目标为符号链接、所需变量存在冲突的远端来源、写入失败时，均返回安全错误。它不会创建服务条目、打印配置值或发起 API 请求。此修复命令的 `--dry-run` 会读取并验证所选文件，但不写入；上文的 setup dry-run 会读取配置并仅预检两个目标表，不启动 MCP 子进程，也不写入。

TOML Kit 文档说明了一项格式保留例外：扩展数组表的乱序子表在重新序列化时会被重新排列，锁定版本也存在这一行为。计划写入修复前，helper 会检查原文档未经修改时能否逐字节往返还原；不支持的排版会被拒绝且不写入，避免静默移动无关内容。注册 setup 会在单次原子配置更新前执行相同检查。若独立修复命令发现转发已经完整，即使存在这种排版也仍保持无改动。

下面是不完整的默认注册结果示例。手动编辑时须保留已有 `command`、`args`、审批设置及其他转发变量名；`tools` 项还应保留其 `OPENAI_TIMEOUT_MAX_RETRIES` 转发声明：

```toml
[mcp_servers.token-io-decoupling-workflow]
env_vars = [
  "OPENAI_API_KEY", "OPENAI_BASE_URL",
  "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY",
  "http_proxy", "https_proxy", "all_proxy", "no_proxy",
]

[mcp_servers.token-io-decoupling-tools]
env_vars = [
  "OPENAI_API_KEY", "OPENAI_BASE_URL",
  "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY",
  "http_proxy", "https_proxy", "all_proxy", "no_proxy",
  "OPENAI_TIMEOUT_MAX_RETRIES",
]
```

Codex 自身的环境中必须持有这两个非空白 API 变量，以及需要使用的代理变量。`env_vars` 允许将对应变量值转发给各自单独启动的 MCP 进程；它不会读取 Shell 配置或 `.env` 文件，也不会复制其他终端的环境。不要将真实值写入仓库文件、setup 参数、日志或示例。字段含义见 [Codex MCP 配置参考](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)。

两个 MCP 注册都会在 setup 时合并转发声明。安装脚本的 `--mcp` 操作包含 setup；单独执行 `uv tool install` 仍不会注册服务或提供凭据。修改配置后重新加载受影响的 MCP 服务；若客户端没有重载机制，退出后重新打开客户端以创建新服务进程。运行中的进程不会自动获得修改后的配置。

终端调用成功而 MCP 请求报告缺配置时，检查客户端进程环境、各注册项的转发变量名，以及服务是否已重新创建。只记录变量存在性及是否非空白。当前 Decisions advisor 在任一必需值缺失或为空白时，在创建 SDK client 之前返回 `fallback`，原因为 `missing_credentials`；不要套用其他服务的 `missing_api_key` 错误名称。转发不会启用 API 请求、授予出站数据权限或建立本地会话上下文；下文的独立要求仍须满足。



## 本地 stdio 工作流导航

Workflow stdio 服务提供有界事件指令与调用方事实的结构校验，不在调用之间维护线程、项目、Root、Worker、allocation 或检查点状态。项目本地 Memory 属于独立 tools 服务；启动路径或调用方 metadata 均不建立身份或授权。

单独的输出 materializer 默认不可用，须具备可信启动上下文、独立操作员授权及匹配的逐次调用绑定。实际 guard 边界见[输出物化 · 边界请求 Hook](../../../../../instruction-compiler/sources/skill/references/coding/hooks/boundary-requested.md#可选资源操作)、[输出物化 · 动作观察 Hook](../../../../../instruction-compiler/sources/skill/references/coding/hooks/action-observed.md#观察效果)和[调用方上下文](CODEX_CALLER_CONTEXT.md)。安装包检查验证 stdio 发现及有界行为；App Server 最终检查仍限版本、发现、能力和规则读取，不执行模型轮次或变更。

## 真实 API 请求的必需配置

所有 OpenAI 客户端构造路径，包括可选事件建议，均使用共享 HTTPX2 客户端构建函数，显式设置 `trust_env=True`，保留 SDK 的连接数限制及重定向默认值、各操作的 timeout 和 `max_retries=0`。每次创建客户端时，从 MCP 进程环境读取 `HTTP_PROXY`、`HTTPS_PROXY`、`ALL_PROXY` 和 `NO_PROXY`，包括对应的小写形式。代理选择和绕过行为遵循 [HTTPX2 环境变量规则](https://pydantic.dev/docs/httpx2/api/environment_variables/)。`NO_PROXY` 可允许直连；未配置代理时仍可使用正常的直连路径。代理无效或不可达时沿用现有的安全 API 失败结果，服务不会改为直连重试。关闭 SDK 客户端时一并关闭 HTTPX2 客户端；SDK 构造失败时也会关闭刚创建的 HTTP 客户端。

已有安装应更新工具、运行 `token-io-decoupling setup codex` 合并新增的转发变量名，再重新加载 MCP 服务。代理变量必须存在于启动服务的 Codex 进程环境中，只在其他终端设置并不生效。Setup 仅保存变量名，不需要通过参数提供代理值。单独调用 API 工具不会修改系统代理或用户配置。

Root 和每个受委派的 Agent 都必须在项目功能代码及测试/smoke 代码中遵守此限制：每次真实 API 请求前，从本地进程环境读取 `OPENAI_API_KEY` 和 `OPENAI_BASE_URL`。两项都必须存在且非空，仅含空白字符也视为无效。缺少任一项或任一项无效时，不得创建 SDK client 或发送真实请求，改走文档规定的回退路径。

不得使用硬编码密钥或端点、调用方提供的替代值或 SDK 的默认端点。必须在实际调用时读取这两项本地值，并显式传给 SDK；不得打印或持久化其值。合成配置仅可用于不发送网络请求的 Mock。

可选检查点建议仍默认关闭。其真实请求还必须具备显式启用及出站数据授权；本文档本身不授予这些权限。普通测试套件使用 Mock，真实 smoke 测试需要单独显式 opt-in，并遵守相同的双环境变量要求。

检查点建议在请求成功或失败时均关闭客户端。关闭失败会丢弃模型选项并返回安全的 `fallback`，不抑制独立结构检查结果。供应商故障保留分类后的 `recovery` 指引：未知关闭故障要求 `stop_and_review`，已确认的瞬态故障可以提示调用方审阅后有界重试。这里修复了先前将供应商恢复信息覆盖为通用继续提示的行为。每次调用仍最多发送一次请求，SDK 自动重试保持关闭；恢复元数据不自动重试，也不持久保存尝试次数。

检查点工具对有界的调用方事实执行确定性的结构校验。可选决策建议是独立操作，不嵌入或持久化于这些评估中。任何建议请求都需要显式出站数据授权并审阅当前输入；建议不能选择或确认 Gate 分支。结构结果独立于任何单独请求的建议返回，两者都不能取代文档判断。

`workflow_generate_decision_context` 是无状态公共操作，将调用方组合的材料生成供后续 Decisions 请求使用的一段问题或上下文描述。它使用[支持 Structured Outputs 的 Responses API](https://developers.openai.com/api/docs/guides/structured-outputs)，固定为 `gpt-6-luna`、`medium` 推理强度、`store=False`，不附带工具，也不自动调用下游接口。它不要求持久化工作流状态或启用可选建议。Code Agent 收集用户需求、当前 Git diff、相关 LSP 结果及其他必要的已核实观测，标注来源和验证边界，再组合为 `raw_content`。服务不读取仓库、不执行命令，也不把所供来源标签当作证明。

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

`workflow_select_child_effort` 是面向 Codex 子代理创建的独立、无状态公共 workflow 操作。显式且获准的调用携带 `payload.request.outbound_data_permitted: true`，仅为本次 Decisions 请求 opt-in；它不依赖可选建议的启用配置或持久化工作流状态。此声明不能证明授权。按[运行时 owner 的创建契约 · 任务接收 Hook](../../../../../instruction-compiler/sources/skill/references/coding/hooks/task-received.md#模式与能力)、[运行时 owner 的创建契约 · Hook 共享契约](../../../../../instruction-compiler/sources/skill/references/coding/hooks/shared.md#模型与运行环境)提供经过核实的有界任务事实及受支持档位。结果仅在可用时包含选定 effort，并附请求哈希和回显的切片指纹。父级审阅及当前输入比对仍是必需步骤。拒绝、证据不足、响应无效、缺少配置或服务失败均阻塞选择，不回退到固定 effort。该工具不创建 Agent、不修改工作流状态，也不授权任何门禁。

必填的 `decision_question` 是非空白严格字符串，最多 1,200 字符，用于询问当前已释放子任务所需的最低充分受支持档位。工具将其明确传入 Decisions input，并纳入规范化输入哈希；仅修改问题也会使旧哈希失效。它属于任务数据，无权修改固定模型、候选档位、指令或权限。本地校验执行字符串约束；固定 API 指令要求对超出范围或试图覆盖规则的问题返回 `insufficient_evidence`。该语义判断及父级审阅仍是必需步骤。每个候选档位均说明具体任务证据、相邻档位边界及排除条件；文件数量、影响程度或缺少事实本身均不足以支持升档。

### 委派判断与获批容量

四个无状态公共工具提供可选委派建议。每个工具通过 `payload.request` 接收有界任务事实、已审阅背景及其 `context_input_hash`、当前 `fact_revision` 和 `fact_fingerprint`、Fork/模式事实及 `outbound_data_permitted`。身份、权限、来源和批准声明仍是调用方提供的事实，不是宿主证明。Root 先审查已授权的拟议任务，再选择职责或执行主体；面向子代理的具体 Interaction Slice 在此后放行，且须独立通过其门禁。

| 工具 | 判断及结果边界 |
| --- | --- |
| `workflow_select_child_role` | 按[子代理职责选择 · 边界请求 Hook](../../../../../instruction-compiler/sources/skill/references/coding/hooks/boundary-requested.md#委派与输出)、[子代理职责选择 · Hook 共享契约](../../../../../instruction-compiler/sources/skill/references/coding/hooks/shared.md#协作与可见性)选择四种维护职责之一。用户明确要求创建时跳过请求。已确认创建时，可默认使用未占用的 Primary Output；已创建职责在整个 Session 内持续占用。全部职责占用时阻塞复核，不建议增加容量。 |
| `workflow_select_executor` | 按[任务分配 · 边界请求 Hook](../../../../../instruction-compiler/sources/skill/references/coding/hooks/boundary-requested.md#委派与输出)、[任务分配 · Hook 共享契约](../../../../../instruction-compiler/sources/skill/references/coding/hooks/shared.md#协作与可见性)建议 Root 或子代理。明确执行主体时跳过建议；已锁定 Single-Agent 模式下明确要求子代理时阻塞，不改成 Root。失败不默认 Root。判定交子代理且仍有获批未用容量、尚无实际子代理时，可进入正常职责与创建门禁。 |
| `workflow_select_child` | 在合格的当前会话子代理中选择。明确指定或唯一候选可跳过建议；忙碌候选须等待。多个空闲候选调用 Decisions，优先合适的空闲 Primary，否则比较任务相关上下文。失败仅可由合适的 Primary 兜底，仍须检查可用性；排除继承的外部会话子代理。 |
| `workflow_assess_output_tokens` | 按[Output Token 路由 · 边界请求 Hook](../../../../../instruction-compiler/sources/skill/references/coding/hooks/boundary-requested.md#委派与输出)、[Output Token 路由 · Hook 共享契约](../../../../../instruction-compiler/sources/skill/references/coding/hooks/shared.md#协作与可见性)独立评估 Root 直接输出。明确执行指令时跳过建议。`no` 允许 Root 通过其他门禁后执行；`yes` 禁止 Root 立即输出，须用适任空闲子代理或挂起等待。有独立授权的创建仍可走正常门禁；输出建议本身不授权创建。 |

获准的 API 请求在每次调用时明确读取非空白的 `OPENAI_API_KEY` 与 `OPENAI_BASE_URL`，只用 `gpt-6-luna`，不自动重试或请求后备模型。工具输入不能覆盖模型或端点。公共[判断背景生成 · 进展反馈 Hook](../../../../../instruction-compiler/sources/skill/references/coding/hooks/progress-reported.md#上下文与建议)、[判断背景生成 · 会话恢复 Hook](../../../../../instruction-compiler/sources/skill/references/coding/hooks/session-resumed.md#指令新鲜度)操作复用 Responses 生成供审阅的背景；问题生成可选。其指令现来自当前 owner 的通用规范；`source_policy_hash` 标识加载的规则，成功请求期间规则发生变化时以 `stale_policy` 阻止复用。

选择器通过 `RuleLoader` 加载当前 owner 指令和具体候选描述。结果区分 `available`、`skipped`、`fallback`、`blocked` 和 `stale`，带有请求/背景/事实及来源策略哈希。实际效果前，Root 必须与当前证据重新核对。缺少配置或必要策略时在请求前阻塞；过期规则必须刷新，不能转为兜底。选择器不会创建子代理、派发工作、修改预算或建立可信绑定。这些工具只接收一个已界定任务，不会将指令分解成多个任务。

### 组件优化测量

[优化基准](OPTIMIZATION_BENCHMARK.md)负责固定案例测量协议、原始结果链接、来源证据，以及 token、调用、延迟、修复和失败的实测结果。它通过真实参考调用方 API 请求比较直接服务组件，与 MCP 传输、当前 Agent 用量及 fresh CLI 检查分开。首版协议归档和唯一一次修正补测均保留；测量边界和复现授权请查该指南。

### 真实 API 集成测试

`../.agents/skills/token-io-decoupling-dev/tests/mcp/real_api_tests/` 下的 `real_api` 用例覆盖真实 Responses 背景生成、子代理 effort Decisions、经协商的进程内 MCP 生成到强度选择链路，以及四类委派判断：新子代理角色、Root/子代理执行主体、已有子代理选择和 Output Token 路由。它们使用合成的需求、diff 文本、Session 事实与 LSP 观测，不采集仓库或宿主数据。委派用例先生成并审核背景，再请求判断，随后核对预期结果、输入哈希及当前策略哈希。这些检查证明真实 API 和 MCP handler 行为，不证明可信桌面宿主绑定或稳定的语义排序。

普通 pytest 运行会收集并跳过这些用例，在访问凭据或创建客户端前结束，即使已有凭据也不会启用。只有精确的 `TOKEN_IO_RUN_REAL_API=1` 才启用它们。启用后，`OPENAI_API_KEY` 或 `OPENAI_BASE_URL` 缺失或空白会使测试失败，不跳过，也不替换为 Mock。请求使用已配置的端点和固定 `gpt-6-luna`；不回退到其他端点或模型，也不自动重试。测试作用域抑制 SDK/HTTP 日志，只报告安全的状态和原因，不输出凭据、端点值或原始服务错误。获得显式授权后，从 `mcp/` 运行：

```sh
TOKEN_IO_RUN_REAL_API=1 uv run --managed-python --locked -- pytest -c pyproject.toml -m real_api ../.agents/skills/token-io-decoupling-dev/tests/mcp/real_api_tests/ -q
```

独立的[官方 HTTPX2 smoke 测试](../../tests/mcp/real_api_tests/test_official_httpx2.py) 使用 `OPENAI_API_KEY_OFFICAL` 和 `OPENAI_BASE_URL_OFFICAL`（有意保留 `OFFICAL` 拼写），由单独的 `TOKEN_IO_RUN_OFFICIAL_API=1` 开关启用。该测试专用配置不改变生产工具的必需变量名。它调用共享 HTTPX2 构建函数，向固定的 `gpt-6-luna` 发出一次简短 Responses 请求，超时为 60 秒、不重试且 `store=False`。测试验证响应完成并有非空文本，只报告安全状态及配置的 transport 是否选择代理，不输出凭据、URL、响应正文或原始服务错误。代理标志为 false 表示实际配置选择直连，包括可能的 `NO_PROXY` 绕过。未启用开关时，在读取这两项变量之前跳过。取得该真实请求的授权后，从 `mcp/` 在 Zsh 中加载变量并运行：

```sh
source ~/.zshrc
TOKEN_IO_RUN_OFFICIAL_API=1 uv run --managed-python --locked -- pytest -c pyproject.toml ../.agents/skills/token-io-decoupling-dev/tests/mcp/real_api_tests/test_official_httpx2.py -q -s --tb=no
```

## 构建、规则资源与安装检查

私有编译器负责 `instruction-compiler/sources/skill` 作者源和 `instruction-compiler/sources` 中的 registry/index。从仓库根生成并核验批准输出：

~~~sh
uv run --project instruction-compiler token-io-compile compile
uv run --project instruction-compiler token-io-compile compile --check
~~~

编译器持久输出 workflow `_resources/instructions.json`、`manifest.json`、`mcp/src/token_io_decoupling/_resources/skill_bundle.zip` 及 `instruction-compiler/build-report.json`。本地 `skills/token-io-decoupling` 树仅为可选查看导出，已由 Git 忽略，产品构建和安装均不需要它。该导出缺失时，`compile --check` 根据当前编译输入核验持久 workflow 资源、ZIP 和报告，不创建导出；导出存在时，还核验其完整文件清单和内容。Workflow 指令、两类 manifest 与 Skill 的 DocumentIndex 使用 `schema_version: 3`、`language: "zh_cn"` 和相同 `build_id`，`files` 映射以 SHA-256 绑定完整字节。生成物禁止手工修改。Hash 仅证明内容一致，不证明语义正确，仍须编译场景测试和独立指令审阅。

内部五类指令集合按 ID 直达单项；registry 使用 contract 3 的唯一 owner，context index 使用 schema 2 的唯一中文 section。Reader 拒绝旧 schema、语言镜像和混合形状，且不读取作者源。外部 `rules_get_context(context_version=2)` 与 bundle schema 2 保持原形状；`language` 仅接受 `zh_cn`，省略时使用中文。静态查询不请求 API。完整中文规则仍受现有请求容量限制，超限时返回缺口而不截断批准政策。

构建 hook 仅验证批准资源，不导入编译器、不读作者文档、不抽取标题、不收集仓库附件。源码开发和安装后运行时使用同一编译格式。资源缺失、损坏、陈旧或不兼容时阻塞依赖执行，不回退作者文件。事件响应完整交付共享／当前 Hook 指令及显式选择的短流程，结构缺口和可选建议分别报告，不定义 next-stage 游标；元数据、能力结果在各自职责内保持精简。

从 `mcp/` 构建五个 wheel 和五个 sdist：

~~~sh
uv build --all-packages --managed-python --python 3.14 --out-dir /tmp/token-io-dist
~~~

产品包排除私有开发 Skill、编译器、作者源、测试、基准和旧仓库投影。sdist 携带批准资源及最少产品构建输入，独立重建不需要编译器或作者源。第三方构建依赖须事先可用，不承诺离线安装依赖。

生成 Skill 和 workflow 资源构成同一批准批次。安装器在任何目标写入前验证归档路径、完整清单、Hash 和已安装 workflow 构建标识，并保留旧 checkout 保护、本地修改检测、并发锁及更新回滚。替换安装名称时更新安装副本 manifest Hash，保留政策批次；不能以兼容为由恢复原始 owner 查找。旧受管目录的 marker format 1 只用于完整指纹及归属核验，成功时整目录原子替换，旧语言文件不会残留；旧 manifest 不作当前执行规则。构建 hook 在产品尚未安装时固定加载仅依赖标准库的归档校验模块，不导入服务、不修改 `sys.path`。

替换时的旧快照放在目标同级的独立备份目录，不属于自动清理的 staging。发布失败时先恢复旧目录；若恢复也失败，保留全部旧字节并在错误中报告准确恢复路径。成功替换或成功回滚后才清理备份目录。这是安装文件保护，不保存 workflow 运行状态。

安装脚本的 `--mcp` 操作在 `uv tool install` 前验证编译新鲜度；资源陈旧即失败，不在安装时重新生成。其 dry-run 不进行编译器、安装、网络或配置操作。更新可执行程序、注册 MCP 和更新已安装 Skill 仍是独立动作。安装同批次产物后更新 Skill、重载受影响 MCP Server，并启动新的 Agent 会话。重新读取指令和政策 Hash、重新评估陈旧结果并保留历史；编辑已安装 Skill 不能修改 MCP 资源。

开发检查和文档回归直接使用私有 Skill 的实际入口；根 scripts 仅保留安装入口，开发及测试转发别名均已移除。

[产物回归](../../tests/mcp/unit_tests/test_build_artifacts.py)验证五个分发包、私有内容排除、同批次资源、损坏拒绝及独立重建。[安装回归](../../tests/mcp/unit_tests/test_skill_artifacts.py)验证无需 checkout 的安装及其不受已安装 Skill 编辑影响。临时工具检查使用任务局部 `UV_TOOL_DIR`、`UV_TOOL_BIN_DIR` 和 [stdio smoke 脚本](../../tests/mcp/support/installed_stdio_smoke.py)。

App Server 最终查看必须按上文有序协调器执行：全部适用检查、当前构建、隔离工具安装、已安装 stdio、全新只读 CLI 查看。首个前置或检查阶段失败即停止。

## 相关概念

- [项目开发指导](../../AGENTS.md)
- [MCP 客户端边界](AGENTS.md)
- [候选合规检查](CANDIDATE_COMPLIANCE.md)
- [输出物化](OUTPUT_MATERIALIZATION.md)

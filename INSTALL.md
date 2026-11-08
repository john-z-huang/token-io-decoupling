# 安装与更新

本文统一负责最终用户的构建、安装、更新和安装恢复；开发流程由[私有开发 Skill](.agents/skills/token-io-decoupling-dev/SKILL.md)负责。

## 前置依赖

运行脚本需要 Bash 3.2 或更高版本。`--mcp` 需要完整 checkout，并要求 `uv`、`codex`、`python3`（Python 3.11 或更高版本）位于 `PATH`；获取和维护 checkout 另需 Git。脚本只检查批准的生成资源，不在安装时重新编译。uv 默认使用托管 Python 3.14，可通过 `--python VERSION` 修改。

`--skills install|update` 需要 `uv` 和已安装的 `token-io-decoupling` 管理命令，使用已安装包内资源，不要求 Codex CLI、源码编译器或 `python3`。无参数及 `--help` 只打印帮助，不检查依赖。
首次安装可能需要联网获取 Python、构建依赖及固定版本的 `dev-workflow-standards` 依赖。本地规则查询不需要 OpenAI Key。不要把源码 checkout 放进 Skill 安装目录。

## 独立服务

[仅安装 tools 的源码方法](README.md#仅安装-tools)不安装 workflow 包、编译规则或 Coding Skill。两个运行时分发包分别拥有自己的可执行入口，均可通过 `setup codex [--dry-run]` 只注册自身。可选完整管理命令支持 `setup codex --server tools|workflow|both`；省略时保持兼容的 `both` 默认值。按服务选择的 setup 不检查、启动或修改未选服务，并保留无关配置及已有启用／禁用状态。

脱离 checkout 仅安装 tools wheel 时，用 `--with` 提供匹配的 core 和 transport wheel，再安装 `token_io_decoupling_tools-*.whl`；仅使用 workflow 则改为安装 `token_io_decoupling_workflow-*.whl`。两个运行时互不依赖，也不依赖管理分发包。Core 和 transport 不含规则资源；规则由 workflow 分发包拥有。Tools 的发现和本地调用不需要编译规则构建身份或 Skill 安装。

## 脚本参数

安装与更新统一使用根目录下的可执行脚本 `./install`，无需 `bash` 前缀。从其它工作目录或符号链接调用时，仍定位到脚本所属 checkout。

| 参数 | 行为 |
| --- | --- |
| 无参数、`-h`、`--help` | 打印使用帮助，不安装或更新。 |
| `--mcp` | 安装或更新 MCP 命令，并注册两个服务。 |
| `--skills install` | 首次安装 Skill。 |
| `--skills update` | 更新已有受管 Skill。 |
| `--name NAME` | 指定 Skill 名称，须与 `--skills` 一起使用。 |
| `--python VERSION` | 指定 MCP 安装使用的 Python 版本，默认 `3.14`。 |
| `--dry-run` | 仅打印所选操作的计划，不检查依赖、执行命令或读写配置。单独使用时预览 MCP 操作。 |

`--mcp` 可与 `--skills install` 或 `--skills update` 组合，按 MCP、Skill 的顺序执行，任一步失败即停止。单独操作 Skill 不重装 MCP 或注册服务；尚未安装管理命令时先运行 `--mcp`。同时安装两者可运行 `./install --mcp --skills install`，同时更新可运行 `./install --mcp --skills update`。

## 首次安装

在 checkout 根目录运行：

```sh
./install --mcp
./install --skills install
```

`--mcp` 核验资源新鲜度，通过 uv 构建并安装根包及四个本地 workspace 依赖，然后注册、检查 `token-io-decoupling-workflow` 和 `token-io-decoupling-tools`，不安装 Skill。第二条命令核对包内 Skill 与已安装 workflow 资源，并将受管快照发布到 `~/.agents/skills/token-io-decoupling-skill`。

脚本通过 `uv tool dir --bin` 定位已安装管理命令，即使 uv 的 bin 目录不在 `PATH` 中也可使用，不需要激活虚拟环境。

## 更新

取得所需 checkout 版本后，在其根目录运行：

```sh
./install --mcp
./install --skills update
```

`--mcp` 检查资源新鲜度后，重装工具及 workspace 依赖并更新两个 MCP 注册；`--skills update` 使用更新后的包替换受管快照。已安装 Skill 的用户需要同时更新包和 Skill；仅使用 MCP 的用户只运行第一条命令。成功更新会保留无关 Codex 配置及 setup 支持的现有目标设置，不删除其它注册；已有的 `enabled=false` 设置也会保持禁用。

默认 Skill 名为 `token-io-decoupling-skill`。如果选择了其它名称，两条 Skill 命令均追加相同的 `--name my-coding-skill`；名称仅允许小写字母、数字及分隔它们的连字符。已有 Skill 使用 `update`，尚未安装使用 `install`。

生成的 Skill 只包含一份中文指令，使用 `references/coding/hooks/` 下的 Hook 文档与两份简短流程，不保留英文副本或 `_zh_cn` 文件。`instruction-index.json` 采用 schema 3，将事件、流程和检查点 ID 直接映射到唯一文档或中文章节。多个检查点可以引用同一文档，各自的必需事实、证据和合法分支仍独立保留。

Workflow 与 Skill 清单采用 schema 3、`language: "zh_cn"` 和相同 `build_id`。更新 Skill 时先核验受管标记和完整文件指纹，再整体替换快照；归属不明或已有本地修改时停止，不覆盖内容。

## 仅构建发行文件

在 checkout 根目录运行：

```sh
uv build --project mcp --all-packages --out-dir mcp/dist
```

该命令在 `mcp/dist/` 产生五个 wheel 和五个 sdist，不安装或注册任何内容。它打包批准的生成资源，不编译作者指令。如果作者指令已修改，维护者须先通过私有开发流程重新生成、验证资源，再交付构建。

## 脱离 checkout 安装 wheel 集合

把同一次构建的五个 wheel 放入 `dist/` 目录，目录中只保留该版本的 wheel。从其父目录运行：

```sh
uv tool install --force --reinstall --managed-python --python 3.14 \
  --with-executables-from token-io-decoupling-workflow \
  --with-executables-from token-io-decoupling-tools \
  --with dist/token_io_decoupling_core-*.whl \
  --with dist/token_io_decoupling_transport-*.whl \
  --with dist/token_io_decoupling_workflow-*.whl \
  --with dist/token_io_decoupling_tools-*.whl \
  dist/token_io_decoupling-*.whl
"$(uv tool dir --bin)/token-io-decoupling" setup codex
"$(uv tool dir --bin)/token-io-decoupling" skills install
```

已有受管 Skill 时，最后一行改为 `skills update`。显式提供五个准确 wheel 匹配，可避免同版本缓存依赖替换所选构建的成员。不要混用 wheel 集合；已安装 workflow 与 Skill bundle 的构建身份及文件清单须一致，Skill 安装器会拒绝不一致。

其它 Code Agent 的纯文档用户可以省略 `setup codex`，这不使其成为直接 MCP 客户端。Skill 命令读取已安装包资源，不需要 checkout 或编译器。

## 验证与启用

Setup 成功表示已检查两个 MCP 工具清单：workflow 为 11 个工具，tools 服务为 41 个工具。Skill 安装／更新成功表示已核验 workflow 与 bundle 批次，并在 Skill 目录写入 `manifest.json`、`.token-io-skill.json`；二者均记录 `build_id`，受管文件哈希也反映选定的安装名称。已有禁用注册须先通过通常的 Codex 配置方式启用，才能使用。

安装或更新后，重载两个 MCP 服务并开启新 Agent 会话。现有连接和已加载 Skill 指令不会热更新。新会话加载选定的 Skill 名称（默认 `token-io-decoupling-skill`），再遵循已安装的 `~/.agents/skills/<selected-name>/SKILL.md` 中的 Coding 入口。即使包版本号没有变化，也需要这一步。

可选 API 操作要求启动 Codex 的环境中提供非空 `OPENAI_API_KEY` 和 `OPENAI_BASE_URL`。Setup 转发变量名，不写秘密值，不创建凭据或提供端点；MCP 发出的 OpenAI 请求使用 `gpt-6-luna`。通过既有本地环境机制配置变量值后重启服务。安装、发现和静态规则查询不需要 API 请求。

## 可选 workflow 事件与原生 Hook

`workflow_check_event` 的 `payload.request.event` 接受 `task_received`、`boundary_requested`、`action_observed`、`progress_reported`、`completion_requested` 或 `session_resumed`，返回共享契约、当前 Hook、结构缺失事实／证据及可选建议。指定 `mode` 为 `single-agent` 或 `multi-agent` 并设 `include_workflow: true`，可同时取得同批次的简短流程。目标、运行时限制、待办工作和证据均由 Agent 自行记忆在上下文中，workflow 不保存或恢复这些信息。

所有规则和事件查询默认使用中文；`language` 只接受 `zh_cn`，显式 `en` 会被拒绝。原生命令的 `--language` 同样只接受 `zh_cn`。

事件及可选流程文本共用 `max_chars`，默认 24,000，范围 256–60,000。这是完整交付容量，不是执行预算。容量不足时不返回部分指令正文，也不发送语义请求。旧 `rules_get_context` 保持 12,000 默认值。

静态检查不需要 API。选择事件建议时，将 workflow 命令配置为带 `--enable-event-advice` 启动，每次请求还须明确提供 `semantic_input: {"outbound_data_permitted": true}`；只有启动旗标不会外发数据。建议使用既有环境配置、单次固定 `gpt-6-luna` 请求、20 秒超时且不自动重试。返回选项不包含模型逐案理由：`feedback` 摘录该选项的文档含义，结构缺口另行报告。建议不授予权限，也不确立验收成功。

可选原生命令从 stdin 读取一个有界 JSON 对象并写出一个原生响应：

```sh
"$(uv tool dir --bin)/token-io-decoupling-workflow" hook --mode single-agent
```

在自行审阅的 Hook 配置中，仅映射已支持的 Codex 事件：

| 原生事件 | 逻辑事件 |
| --- | --- |
| `UserPromptSubmit` | `task_received` |
| `PreToolUse` | `boundary_requested` |
| `PostToolUse` | `action_observed` |
| `SubagentStop` | `progress_reported` |
| `Stop` | `completion_requested` |
| `SessionStart` | `session_resumed` |

安装和 setup 不安装原生 Hook。适配器无法判断原生会话是否采用本 workflow，调用方须将命令限定到已采用的会话；无法可靠限定时，使用 Agent 主动 `workflow_check_event` 调用。不提供全局注册或采用状态文件，也不为独立工具增加前置检查。适配器不读取 transcript 或任意文件，不持久化状态，也不输出权限 `allow`。默认 Stop/SubagentStop 响应使用 `systemMessage`，不会把契约回灌模型；Agent 须通过 Skill 或 MCP 工具主动消费完成／进展检查。

Hook 选项错误、输入错误及运行故障均返回退出码 1；argparse 的错误码 2 会转换为 1，避免被原生宿主误作阻塞。`--help` 返回 0。只有下述显式 JSON 响应会请求阻塞。

原生语义模式须同时提供 `--semantic --outbound-data-permitted`。额外的 `--block-once` 仅在原生 `stop_hook_active` 严格为 `false`、指令完整且新鲜、有效建议为 `needs_evidence` 或 `amend` 时允许一次纠正。标志为 true、缺失或类型错误，`wait`／`stop`、缺失／故障／陈旧建议均不阻塞。此行为依赖宿主的续跑标志，不证明授权，也不限制整个会话或其它 Hook。等待、阻塞或预算耗尽的工作可以准确报告状态并结束当前轮次。

## 失败与恢复

| 结果 | 处理 |
|---|---|
| 新鲜度检查或构建失败 | 停止。使用批准资源，或由维护者重新生成；不会安装作者文档回退路径。 |
| 工具安装成功但 setup 失败 | 已安装工具仍可用。处理报告的配置问题后，运行 `"$(uv tool dir --bin)/token-io-decoupling" setup codex`。 |
| Skill 不存在或已存在 | 选择匹配的 `install` 或 `update`；两者不会静默转换操作。 |
| Skill 有本地修改、归属未知、符号链接或并发更新 | 保留当前目录并处理报告的问题；不要修改 marker 绕过校验或强行覆盖文件。 |
| Skill 更新发布失败，且自动回滚也失败 | 旧快照保留在错误报告给出的同级恢复目录中，不会随临时 staging 清理；停止更新，检查目标状态后从该准确路径恢复。 |
| 混批次 bundle 被拒绝 | 重装目标构建的全部五个 wheel，再重跑 Skill 命令。 |

旧 `~/.agents/skills/token-io-decoupling` checkout 受保护，这些命令不会迁移、覆盖或删除它。源码 checkout 保持在 Skill 发现目录之外；自定义名称不豁免归属和本地修改保护。

脚本预览示例：

```sh
./install --mcp --dry-run
./install --skills update --dry-run
```

脚本预览仅打印计划。底层 `setup codex --dry-run` 会读取并预检配置，不写入或启动服务；底层 `skills install`、`skills update` 没有 `--dry-run` 选项。

## 相关文档

- [产品说明](README.md)。
- [项目开发](.agents/skills/token-io-decoupling-dev/SKILL.md)。

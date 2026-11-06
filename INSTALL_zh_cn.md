# 安装与更新

[English](INSTALL.md) | [简体中文](INSTALL_zh_cn.md)

本文统一负责最终用户的构建、安装、更新和安装恢复；开发流程由[私有开发 Skill](.agents/skills/token-io-decoupling-dev/SKILL_zh_cn.md)负责。

## 前置依赖

执行下述源码 checkout 命令前，确保 `PATH` 中有 `uv`、`git`、`python3`（Python 3.11 或更高版本）、Bash 3.2 或更高版本及本地 `codex` CLI。使用包含批准生成资源的完整 checkout。uv 为已安装工具选择托管 Python 3.14；helper 的 `--python VERSION` 可以修改此选择。新鲜度检查使用已有的 `python3` 命令。

首次安装可能需要联网获取 Python、构建依赖及固定版本的 `dev-workflow-standards` 依赖。本地规则查询不需要 OpenAI Key。不要把源码 checkout 放进 Skill 安装目录。

## 独立服务

[仅安装 tools 的源码方法](README_zh_cn.md#仅安装-tools)不安装 workflow 包、编译规则或 Coding Skill。两个运行时分发包分别拥有自己的可执行入口，均可通过 `setup codex [--dry-run]` 只注册自身。可选完整管理命令支持 `setup codex --server tools|workflow|both`；省略时保持兼容的 `both` 默认值。按服务选择的 setup 不检查、启动或修改未选服务，并保留无关配置及已有启用／禁用状态。

脱离 checkout 仅安装 tools wheel 时，用 `--with` 提供匹配的 core 和 transport wheel，再安装 `token_io_decoupling_tools-*.whl`；仅使用 workflow 则改为安装 `token_io_decoupling_workflow-*.whl`。两个运行时互不依赖，也不依赖管理分发包。Core 和 transport 不含规则资源；规则由 workflow 分发包拥有。Tools 的发现和本地调用不需要编译规则构建身份或 Skill 安装。

### 迁移

任务计划和 Memory 调用从 workflow 注册项迁至 tools；候选 preflight 随其服务一起迁移。重载两个服务，并更新 enabled_tools/disabled_tools 筛选和操作者 factory 导入。Factory 现在从 `token_io_decoupling_tools` 导入 `TaskPlanService`、`SerenaMemoryStore`、`CompliancePreflightService` 及物化类型；`--task-plan-factory`、`--compliance-factory` 和 `--output-materializer-factory` 属于 tools 可执行程序，workflow 拒绝这些旧启动选项。操作 payload 及现有计划／Memory 数据保留，工具清单变为 workflow 11 项、tools 41 项。`tools_capabilities` 是可选诊断，`workflow_capabilities` 仅报告工作流自身依赖。已有 prepared artifact 的 schema 与授权检查保持不变。

每个工具校验调用提供的当前资源，不检查先前工具调用。例如完成操作消费已有兼容计划，归档消费已有完成计划，apply 消费已有 prepared artifact；这些资源状态不放行也不要求任何工作流节点。API 操作仍需要各自配置，受保护写入仍需要当前权限。

## 首次安装

在 checkout 根目录运行：

```sh
bash scripts/install-codex-mcp.sh
"$(uv tool dir --bin)/token-io-decoupling" skills install
```

Helper 核验资源新鲜度，通过 uv 构建并安装根包及四个本地 workspace 依赖，然后注册、检查 `token-io-decoupling-workflow` 和 `token-io-decoupling-tools`，不安装 Skill。第二条命令核对包内 Skill 与已安装 workflow 资源，并将受管快照发布到 `~/.agents/skills/token-io-decoupling-skill`。

按示例通过 `uv tool dir --bin` 调用管理命令，即使 uv 的 bin 目录不在 `PATH` 中也可使用，不需要激活虚拟环境。

## 更新

取得所需 checkout 版本后，在其根目录运行：

```sh
bash scripts/install-codex-mcp.sh
"$(uv tool dir --bin)/token-io-decoupling" skills update
```

Helper 重装工具和 workspace 依赖、刷新批准的编译资源，并检查两个当前 MCP 注册；随后 `skills update` 替换受管快照。产品更新后两条命令都要运行。成功更新会保留无关 Codex 配置及 setup 支持的现有目标设置，不删除其它注册；已有的 `enabled=false` 设置也会保持禁用。

默认 Skill 名为 `token-io-decoupling-skill`。如果选择了其它名称，两条 Skill 命令均使用相同的 `--name my-coding-skill`。已有 Skill 使用 `update`，尚未安装使用 `install`。

生成的指令文档使用可读的来源名称，例如 `instructions/workflow-concepts--entry-and-context--contract.md`。文档链接保留作者原有的可读名称，内部单元 ID 保留在索引和 MCP 查询中。清单覆盖 `instruction-index.json`，将稳定单元 ID 和检查点 ID 映射到对应的双语文档。多个检查点可以共用文档，索引仍保留各自独立的必需事实、证据、合法分支和返回规则。更新会替换受管快照，同时移除旧文档名称。

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

安装或更新后，重载两个 MCP 服务并开启新 Agent 会话。现有连接和已加载 Skill 指令不会热更新。新会话加载选定的 Skill 名称（默认 `token-io-decoupling-skill`），再遵循已安装的 `~/.agents/skills/<selected-name>/SKILL_zh_cn.md` 中的 Coding 入口。即使包版本号没有变化，也需要这一步。

可选 API 操作要求启动 Codex 的环境中提供非空 `OPENAI_API_KEY` 和 `OPENAI_BASE_URL`。Setup 转发变量名，不写秘密值，不创建凭据或提供端点；MCP 发出的 OpenAI 请求使用 `gpt-6-luna`。通过既有本地环境机制配置变量值后重启服务。安装、发现和静态规则查询不需要 API 请求。

## 失败与恢复

| 结果 | 处理 |
|---|---|
| 新鲜度检查或构建失败 | 停止。使用批准资源，或由维护者重新生成；不会安装作者文档回退路径。 |
| 工具安装成功但 setup 失败 | 已安装工具仍可用。处理报告的配置问题后，运行 `"$(uv tool dir --bin)/token-io-decoupling" setup codex`。 |
| Skill 不存在或已存在 | 选择匹配的 `install` 或 `update`；两者不会静默转换操作。 |
| Skill 有本地修改、归属未知、符号链接或并发更新 | 保留当前目录并处理报告的问题；不要修改 marker 绕过校验或强行覆盖文件。 |
| 混批次 bundle 被拒绝 | 重装目标构建的全部五个 wheel，再重跑 Skill 命令。 |

旧 `~/.agents/skills/token-io-decoupling` checkout 受保护，这些命令不会迁移、覆盖或删除它。源码 checkout 保持在 Skill 发现目录之外；自定义名称不豁免归属和本地修改保护。

上述安装步骤可通过 `setup codex --dry-run` 或 `bash scripts/install-codex-mcp.sh --dry-run` 预览。Helper 预览只打印计划，不执行安装或读取配置；setup 预览读取、预检两个目标配置段，不写入或启动服务。`skills install`、`skills update` 没有 `--dry-run` 选项。

## 相关文档

- [产品说明](README_zh_cn.md)。
- [项目开发](.agents/skills/token-io-decoupling-dev/SKILL_zh_cn.md)。

# 安装与使用

本页记录旧 MCP 服务的安装流程，现行入口见 [归档说明](README.md)。

仓库提供面向 Pi Coding Agent 的 Skill 和 MCP 工具服务。旧工作流插件已归档，仅供只读参考，不随当前安装加载。

## 首次安装与后续更新

准备 Bash、`uv` 和兼容 Python 3.11 或更高版本的环境。从仓库根目录运行以下命令。首次构建可能需要下载 Python 和依赖。

```bash
bash scripts/update-pi-tools-and-skill.sh
```

脚本按顺序执行四步。任一步失败即停止。

1. 将 `rules/` 中的 YAML 编译为 `skill/`。
2. 为 MCP workspace 构建本地 wheel。
3. 通过 `uv tool` 安装或更新 `token-io-decoupling-tools`。重复运行会使用本次构建的 wheel，即使软件包版本号未变。
4. 调用刚安装的工具同步本地 Skill。首次创建默认 Skill，后续更新现有受管理的安装。

默认 Skill 目录为 `~/.pi/agent/skills/token-io-decoupling-skill/`。已有其他名称的受管理 Skill 时，使用对应名称运行。Skill 安装器会拒绝未知目录、符号链接和含本地修改的安装。

```bash
bash scripts/update-pi-tools-and-skill.sh --name my-coding-skill
```

只安装或更新 MCP 工具时，运行 `bash scripts/install-pi-mcp.sh`。完整脚本更新 Skill 失败时，已安装的 MCP 工具会保留本次版本。

## 在 Pi 中使用

1. 用 `uv tool dir --bin` 查询可执行程序所在目录。将该目录下 `token-io-decoupling-tools` 的绝对路径登记到 Pi 实际使用的 MCP 配置，采用 stdio，参数留空。脚本不会修改 Pi 配置。 [MCP 注册说明](docs/mcp/DEVELOPMENT.md#在-pi-中注册)
2. 在 Pi 中执行 `/reload` 或新开会话，然后从已安装的 Skill 入口开始任务。按当前会话暴露的工具确认 MCP 已连接。 [现行 Skill 源入口](../../rules/SKILL.yaml)
3. 需要更新时，重新运行安装脚本并重新加载 Pi。若 MCP 正在运行，按当前宿主的配置重启该服务，使其加载新版工具。

用以下命令核对 `uv` 工具入口。

```bash
"$(uv tool dir --bin)/token-io-decoupling-tools" --version
```

安装流程不调用模型 API。需要配置可选 API 能力或单独开发 MCP 时，参阅开发指南。[MCP 开发指南](docs/mcp/DEVELOPMENT.md) · [工作流架构](docs/WORKFLOW_ARCHITECTURE.md)

# Token I/O Decoupling

[English](README.md) | [简体中文](README_zh_cn.md)

Token I/O Decoupling 通过两个本地 MCP Server 和生成的 Skill 交付 Coding 工作流。指令提供当前动作、守卫、证据和精确续接；共享或条件指令具有明确的加载要求，Agent 无需搜索作者文档来重建工作流。

## 首次安装

准备好[前置依赖](INSTALL_zh_cn.md#前置依赖)后，在源码 checkout 根目录运行：

```sh
bash scripts/install-codex-mcp.sh
"$(uv tool dir --bin)/token-io-decoupling" skills install
```

第一条命令检查编译资源新鲜度，构建并安装全部四个运行时包，将两个 MCP 可执行程序注册到 Codex。第二条命令把同批次 Skill 安装到 `~/.agents/skills/token-io-decoupling-skill`。之后重载两个 MCP 服务并开启新 Agent 会话。

## 更新

取得所需 checkout 版本后，在其根目录运行：

```sh
bash scripts/install-codex-mcp.sh
"$(uv tool dir --bin)/token-io-decoupling" skills update
```

更新工具不会自动更新已安装 Skill。首次安装 Skill 使用 `install`，已有受管快照使用 `update`。[安装指南](INSTALL_zh_cn.md)统一说明前置依赖、发行文件构建、仅使用 wheel 的安装、验证和恢复。

## 开始 Coding 任务

按[安装指南](INSTALL_zh_cn.md)完成安装后，加载已安装的 `token-io-decoupling-skill`。使用 MCP 时，先调用 `workflow_capabilities`，再以 `node_id=contract`、`context_version=2` 调用 `rules_get_context`。遵循返回的准确指令，在依赖动作前取得已触发的共享单元。显式非空 `fragment_ids` 只返回指定单元；省略时返回完整默认检查点。版本 1 被拒绝。

MCP Server 支持本地 Codex CLI，包括经该 CLI 使用的本地 Work。其它 Code Agent 可以不使用这两个 MCP Server，直接使用生成文档。静态规则查询不需要 API 凭据或网络；可选 API 工具需要安装指南说明的环境配置和逐次授权。

指令、哈希、能力报告及结构审阅状态不能证明身份、授权副作用或完成结果；受保护操作保留各自守卫。运行时无需作者源、私有编译器或开发 Skill。

## 仓库三部分

| 部分 | 位置与职责 |
|---|---|
| 产品 | `mcp/` 运行时包；可执行工具、守卫、core 编译资源及包内 Skill ZIP。 |
| 私有开发 Skill | [开发入口](.agents/skills/token-io-decoupling-dev/SKILL_zh_cn.md)；项目指导、检查器、产品测试和发布协调。 |
| 私有编译器 | `instruction-compiler/`；作者政策、执行依赖、确定性生成及编译器测试。 |

私有开发与编译输入不进入 wheel、Skill ZIP 或 sdist。不得手工编辑生成资源。根 `scripts/` 仅包含安装入口；开发脚本与文档测试位于私有开发 Skill。

## 相关文档

- [安装与更新](INSTALL_zh_cn.md)。
- [项目开发](.agents/skills/token-io-decoupling-dev/SKILL_zh_cn.md)。

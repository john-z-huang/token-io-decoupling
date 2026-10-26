# Token I/O Decoupling

[English](README.md) | [简体中文](README_zh_cn.md)

`token-io-decoupling` 是一个 Agent 调度 Skill，用于把高价值语义决策与高体量状态消费、输出物化分离。

它维护面向仓库和开发工作的 **Coding** 工作流。Multimodal 内容仅作为独立 reference 保留，不作为可执行工作流维护。请从 [Skill 入口](SKILL_zh_cn.md) 开始；它会按任务当前阶段路由到所需的 reference。

## 将 MCP 服务安装到 Codex

准备好 `uv`、Bash 3.2 或更新版本和 Codex CLI 后，从任意工作目录执行一条命令：

```sh
bash /absolute/path/to/skill/scripts/install-codex-mcp.sh
```

[安装脚本](scripts/install-codex-mcp.sh)会安装或更新当前 checkout 的 MCP 包，自动定位安装后的可执行文件，注册全部四个 profile，并合并必需环境变量的转发名称。安装后工具的 bin 目录无需位于 `PATH`。更新源码后再次运行同一命令即可。追加 `--dry-run` 可预览而不安装或修改配置，`--profile root` 可只注册一个 profile，`--replace` 可显式替换冲突注册。完成后重新加载受影响的 MCP 服务。前置条件、选项和失败处理见[安装指南](mcp/DEVELOPMENT_zh_cn.md#uv-tool-安装与-codex-setup)。

## 文档入口

- [Skill 入口](SKILL_zh_cn.md)：主要路由入口。
- [Coding reference](references/)：由工作流组合使用的独立 Coding 模块和共享协议模块。
- [多语言规则](MULTI_LINGUAL_zh_cn.md)：双语文档规则。
- [增强架构](ENHANCED_ARCHITECTURE_zh_cn.md)：可选 MCP 状态、规则上下文、语义建议及经核验的宿主边界；Native 仍为默认路径。
- [MCP 开发指南](mcp/DEVELOPMENT_zh_cn.md)：本地 Python 检查与包构建。

可选 Decisions 集成默认关闭。每次真实请求（包括测试请求）必须读取本地 `OPENAI_API_KEY` 和 `OPENAI_BASE_URL`，缺少任一项就不得请求。显式启用与测试方法见开发指南。当前生产入口没有经核验的 Codex 或 ChatGPT Desktop 宿主绑定，因此只暴露公共诊断与规则上下文。

`token-io-decoupling setup codex` 会注册所选 profile，并自动将 `OPENAI_API_KEY` 和 `OPENAI_BASE_URL` 合并到各服务的 `env_vars`，包括已匹配的注册项。随后重新加载服务。对于任意名称的已注册服务，可使用 `setup codex-env --server NAME` 或[独立修复脚本](scripts/configure-codex-mcp-env.py)，两者都支持 `--dry-run`。详见[环境转发说明](mcp/DEVELOPMENT_zh_cn.md#codex-stdio-环境变量转发)。转发只让进程获得配置，不会启用 Decisions 或建立宿主绑定。

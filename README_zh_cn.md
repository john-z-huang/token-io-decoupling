# Token I/O Decoupling

[English](README.md) | [简体中文](README_zh_cn.md)

`token-io-decoupling` 是一个 Agent 调度 Skill，用于把高价值语义决策与高体量状态消费、输出物化分离。

它维护面向仓库和开发工作的 **Coding** 工作流。Multimodal 内容仅作为独立 reference 保留，不作为可执行工作流维护。请从 [Skill 入口](docs/skill/SKILL_zh_cn.md) 开始；它会按任务当前阶段路由到所需的 reference。

## 独立安装 Skill

将开发仓库放在用户 Skill 目录之外。安装构建后的 CLI（参见 MCP 安装指南）后运行：

```bash
token-io-decoupling skills install
token-io-decoupling skills update
```

默认安装到 `~/.agents/skills/token-io-decoupling-skill`；可用 `--name NEW-NAME` 指定另一个小写、连字符分隔的名称。旧名称 `token-io-decoupling` 始终被拒绝。安装器不会修改或删除旧项目，会拒绝符号链接路径及已有未知目录，只更新内容未经修改且由本工具管理的安装。更新前请将本地修改另行保存。发布失败时会恢复旧安装；进程中断可能遗留锁或暂存目录，应先检查再人工恢复。

Skill 指令源位于 [docs/skill](docs/skill/SKILL_zh_cn.md)。wheel 和源码分发包携带独立快照，包含双语工作流、引用以及支持文档和脚本。安装只读取该快照，不读取或克隆源码仓库；开发改动必须重新构建、安装 CLI 并显式更新 Skill 后才生效。安装后的 `_project/` 是生成的支持资料快照，不是新的源文档 owner。MCP 注册仍通过独立的 `setup codex` 操作完成。

兼容旧安装时，请在请求中使用新 Skill 名称。已有会话可能保留旧指令：保留并迁移旧开发仓库后，使用现有配置人工停用其旧 Skill 发现入口，再启动使用新名称的新会话。安装器不删除旧项目，也不自动处理重复发现。不要再次将开发仓库本身放进 Skill 目录。

## MCP 支持范围与纯文档使用

本项目的 MCP Server 仅面向本地 Codex CLI 开发。本地 ChatGPT Work 通过本地 Codex CLI 使用它。其他 Code Agent、云端 ChatGPT 聊天和远端 ChatGPT Work 均不直接支持此 Server；只有在各自环境中安装 Codex CLI，并按本项目指示为该 CLI 安装 Server，才能通过该 CLI 使用，这不增加对这些宿主或 Agent 的支持。Codex CLI 调用这些工具时不执行运行环境判断步骤；实际能力、身份、权限和守卫检查仍然适用。参见 [MCP 客户端边界](mcp/AGENTS_zh_cn.md)。

其他 Code Agent 可以不使用此 MCP Server，通过纯文档方式使用 Skill。本项目会持续更新指令，在支持 Codex CLI 的同时维护对其他 Code Agent 的描述兼容；MCP Server 的开发始终聚焦 Codex CLI。

## 开发本仓库

独立的[项目开发 MCP](mcp-project-dev/README_zh_cn.md)和[开发 Skill](.agents/skills/token-io-decoupling-dev/SKILL_zh_cn.md)说明仓库维护与产品工具的分阶段拆分。开发服务当前提供只读骨架能力，后续迁移阶段仍明确列出。

## 将 MCP 服务安装到 Codex

准备好 `uv`、Bash 3.2 或更新版本，并确保 Codex CLI 可用，然后从本仓库根目录运行：

```sh
bash scripts/install-codex-mcp.sh
```

标准安装使用本地 Codex CLI stdio，不需要特权宿主服务、宿主描述符或额外 identity provider。状态调用使用 Codex 的线程元数据和已有分配记录，继续检查路径、角色及授权；这不是独立进程认证或 OS 隔离。参见[本地会话上下文](mcp/CODEX_CALLER_CONTEXT_zh_cn.md)。

安装脚本不会绑定 Memory 项目或安装 Serena。从目标项目根目录启动 Codex；MCP 进程只读取 `<工作目录>/.serena/memories/` 下的文件，不搜索父级或兄弟项目。Memory 目录和所请求的文件必须已存在；缺失时返回非成功结果，不创建文件或目录。

[安装脚本](scripts/install-codex-mcp.sh)会安装或更新当前 checkout 的 MCP 包，定位可执行文件、注册各 profile，并合并环境变量转发名称。Memory 读取使用 Python 标准库，不需要 Serena 包、额外解释器、factory 或 helper。`--dry-run` 可预览而不安装或写入配置。完成后重新加载 MCP 服务。从非仓库根目录运行时，使用安装脚本的绝对路径，并将占位内容替换为真实位置。详见[安装指南](mcp/DEVELOPMENT_zh_cn.md#uv-tool-安装与-codex-setup)和[Memory 工具指南](mcp/SERENA_MEMORY_TOOLS_zh_cn.md)。

## 文档入口

- [Skill 入口](docs/skill/SKILL_zh_cn.md)：主要路由入口。
- [Coding reference](docs/skill/references)：由工作流组合使用的独立 Coding 模块和共享协议模块。
- [多语言规则](MULTI_LINGUAL_zh_cn.md)：双语文档规则。
- [增强架构](docs/skill/ENHANCED_ARCHITECTURE_zh_cn.md)：可选 MCP 状态、规则上下文、语义建议及经核验的宿主边界；Native 仍为默认路径。
- [MCP 开发指南](mcp/DEVELOPMENT_zh_cn.md)：本地 Python 检查与包构建。

可选的持久化 Decisions 集成默认关闭。每次真实请求（包括测试请求）必须读取本地 `OPENAI_API_KEY` 和 `OPENAI_BASE_URL`，缺少任一项就不得请求。显式启用与测试方法见开发指南。公共接口还包括本地 Memory 读取、Native 任务计划、合规预检、路由及无状态上下文/选择工具。它们不要求 Enhanced binding，但保留各自的配置与授权条件；工具发现本身不能证明任何一项已满足。状态操作要求有效的本地请求范围、已登记角色与操作授权。

OpenAI API 工具共用显式设置 `trust_env=True` 的 HTTPX2 客户端，从 MCP 进程环境读取 `HTTP_PROXY`、`HTTPS_PROXY`、`ALL_PROXY` 和 `NO_PROXY`，包括对应的小写形式。`NO_PROXY` 可使指定目标绕过代理；未配置代理时使用客户端正常的直连路径。代理无效或不可达时返回现有的安全 API 错误结果，不会改为直连重试。

`token-io-decoupling setup codex` 会注册所选 profile，并自动将 `OPENAI_API_KEY`、`OPENAI_BASE_URL` 及上述可选代理变量名合并到各服务的 `env_vars`，包括已匹配的注册项。随后重新加载服务。对于任意名称的已注册服务，可使用 `setup codex-env --server NAME` 或[独立修复脚本](scripts/configure-codex-mcp-env.py)，两者都支持 `--dry-run`。详见[环境转发说明](mcp/DEVELOPMENT_zh_cn.md#codex-stdio-环境变量转发)。只写入变量名，不保存变量值。转发只让进程获得配置，不会启用 Decisions 或建立宿主绑定。

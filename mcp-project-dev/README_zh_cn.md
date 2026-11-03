# 项目开发 MCP

[English](README.md) | [简体中文](README_zh_cn.md)

本独立工程承载 Token I/O Decoupling 仓库的开发工具，按仓库的[客户端边界](../mcp/AGENTS_zh_cn.md)支持本地 Codex CLI MCP 客户端。

## 当前能力

[#190](https://github.com/john-z-huang/token-io-decoupling/issues/190) 的第一阶段由 [#192](https://github.com/john-z-huang/token-io-decoupling/issues/192) 跟踪，提供独立 stdio 服务及一个确定性只读工具 `dev_capabilities`。初始化指令和工具发现元数据区分已实现与不可用能力。该工具不读取仓库内容、不写文件、不调用 OpenAI、不访问 Git/GitHub、不读取聊天或写入 Memory。

本阶段的规则映射与编译、项目专用合规检查和 Skill 指令维护尚不可用。现有产品工具和维护脚本在指定迁移阶段前保持当前行为。本服务不授予后续写入或外部操作权限。

## 运行与检查

在仓库根目录创建或复用本独立工程的环境，并安装锁定依赖：

```bash
uv sync --project mcp-project-dev --locked --group dev
uv run --project mcp-project-dev --locked token-io-decoupling-dev --help
uv run --project mcp-project-dev --locked token-io-decoupling-dev --version
uv run --project mcp-project-dev --locked token-io-decoupling-dev --stdio
```

最后一条命令启动 MCP stdio 传输；连接完成协商的 MCP 客户端以检查初始化信息和 `tools/list`。stdout 专用于协议。本操作不会在用户配置中注册服务，也不会安装或更新用户 Skill。

## 职责与迁移

项目维护使用仓库的[开发 Skill](../.agents/skills/token-io-decoupling-dev/SKILL_zh_cn.md)；组件归属和分阶段迁移见[职责与迁移清单](../.agents/skills/token-io-decoupling-dev/references/responsibility-migration_zh_cn.md)。产品包仍位于 `mcp/`，开发工程有独立的包和环境。开发组件可以复用必要的产品库；产品包不得依赖本工程或开发 Skill。

## 离线检查

```bash
uv run --project mcp-project-dev --locked pytest -q mcp-project-dev/tests
uv run --project mcp-project-dev --locked ruff check mcp-project-dev
uv run --project mcp-project-dev --locked ruff format --check mcp-project-dev
uv run --project mcp-project-dev --locked ty check --project mcp-project-dev
```

这些检查不运行最终 Codex SDK 检查。执行该检查前，须遵守[仓库测试边界](../AGENTS_zh_cn.md#codex-sdk-最终测试边界)和阶段6的验收顺序。

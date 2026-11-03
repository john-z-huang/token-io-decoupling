# 项目开发 MCP

[English](README.md) | [简体中文](README_zh_cn.md)

本独立工程承载 Token I/O Decoupling 仓库的开发工具，按仓库的[客户端边界](../mcp/AGENTS_zh_cn.md)支持本地 Codex CLI MCP 客户端。

## 当前能力

[#192](https://github.com/john-z-huang/token-io-decoupling/issues/192) 引入的独立 stdio 服务提供确定性只读工具 `dev_capabilities`。在启动时配置可信项目根后，[#193](https://github.com/john-z-huang/token-io-decoupling/issues/193) 增加 `compile_runtime_instructions` 和只读的 `check_runtime_instructions_freshness`。初始化指令与工具发现元数据说明各工具的输入、结果、限制和副作用。

编译读取已审核的本地映射及策略 Markdown，并写入一个固定生成资源。新鲜度检查验证这些输入并比较生成资源，不执行写入。这些工具不调用 OpenAI、不访问网络或 Git/GitHub、不读取聊天或写入 Memory。项目专用合规检查与 Skill 指令维护在 [#190](https://github.com/john-z-huang/token-io-decoupling/issues/190) 的指定阶段前仍不可用。产品运行时加载和现有维护脚本保持当前行为。

## 运行与检查

在仓库根目录创建或复用本独立工程的环境，并安装锁定依赖：

```bash
uv sync --project mcp-project-dev --locked --group dev
uv run --project mcp-project-dev --locked token-io-decoupling-dev --help
uv run --project mcp-project-dev --locked token-io-decoupling-dev --version
uv run --project mcp-project-dev --locked token-io-decoupling-dev --stdio
```

最后一条命令启动仅提供能力发现的 MCP stdio 传输。启用编译工具时，在仓库根目录运行，并在启动参数中传入其绝对路径：

```bash
uv run --project mcp-project-dev --locked token-io-decoupling-dev --project-root "$PWD" --stdio
```

连接完成协商的 MCP 客户端以检查初始化信息和 `tools/list`；各工具接受空参数对象。工具调用不能更改项目根、manifest、输出路径、模型或权限。stdout 专用于协议。启动服务不会在用户配置中注册它，也不会安装或更新用户 Skill。

## 职责与迁移

项目维护使用仓库的[开发 Skill](../.agents/skills/token-io-decoupling-dev/SKILL_zh_cn.md)；组件归属和分阶段迁移见[职责与迁移清单](../.agents/skills/token-io-decoupling-dev/references/responsibility-migration_zh_cn.md)。产品包仍位于 `mcp/`，开发工程有独立的包和环境。开发组件可以复用必要的产品库；产品包不得依赖本工程或开发 Skill。

## 编译与检查

在已配置的根目录下维护已审核映射 `mcp-project-dev/compiler-manifest.v1.json`。`compile_runtime_instructions` 验证其来源、引用分类、完整依赖、双语结构、版本、哈希和预算后，发布 `mcp-project-dev/generated/runtime-instructions.v1.json`。验证失败保留既有输出。审核草稿与发布 manifest 分开。

替换已有且内容变化的输出时，manifest 的 `output_baseline_sha256` 必须匹配当前产物经验证的 `canonical_sha256`；它不是原始文件哈希。即使输出相同，也会核对显式提供的基线。未提供基线时，只允许新建或字节完全相同的不变操作。检查返回结果并调用 `check_runtime_instructions_freshness`；只有 `fresh` 表示与当前已验证输入一致。使用产物前须解决 missing、stale 或 failed 结果。

schema、来源、兼容与限制的细节由[编译器契约](../.agents/skills/token-io-decoupling-dev/references/compiler-contract_zh_cn.md)维护。本阶段不将产品 loader 切换为编译资源，也不授予其他文件写入。

## 离线检查

```bash
uv run --project mcp-project-dev --locked pytest -q mcp-project-dev/tests
uv run --project mcp-project-dev --locked ruff check mcp-project-dev
uv run --project mcp-project-dev --locked ruff format --check mcp-project-dev
uv run --project mcp-project-dev --locked ty check --project mcp-project-dev
```

这些检查不运行最终 Codex SDK 检查。执行该检查前，须遵守[仓库测试边界](../AGENTS_zh_cn.md#codex-sdk-最终测试边界)和阶段6的验收顺序。

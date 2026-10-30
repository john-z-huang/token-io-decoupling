# MCP Server 开发指令

[English](AGENTS.md) | [简体中文](AGENTS_zh_cn.md)

本文负责 `mcp/` 下 MCP Server、各包、测试、元数据和文档的客户端支持边界。修改文档前，先读取仓库的[多语言规则](../MULTI_LINGUAL_zh_cn.md)。

## 支持的客户端

- MCP Server 面向本地可用的 Codex CLI，包括本地 Work 使用的本地 Codex CLI/app-server 路径。云端 ChatGPT 对话和远端 Work 不是直接客户端；其他 Code Agent 也不作为直接客户端受支持。
- 如果其他 Agent 在自己的环境安装 Codex CLI，并按本仓库说明在该环境配置 MCP Server，则受支持的调用路径仅为该环境内的本地 Codex CLI；这不会增加对其他 Agent 或云端界面的适配器或直接支持。Server 不要求调用者选择或分类运行环境。
- 修改 `mcp/` 下的代码时，考虑上述场景中的 Codex CLI 行为。不得为其他 Code Agent 添加兼容分支、适配器、配置、示例、测试或工具指令。仓库级跨厂商对应能力核验不适用于本目录。
- 删除过时的不受支持客户端路径和声明，不将其保留为回退路线。共享协议或操作系统抽象不能证明支持额外客户端。
- 固定客户端范围不等于实际宿主集成已经可用或通过验证。仍须核验已暴露能力、可信身份、守卫与权限，保留不可用结果及失败关闭行为。

## 范围与权限

### Codex SDK 仅限测试

遵守仓库的 [Codex SDK 最终测试边界](../AGENTS_zh_cn.md#codex-sdk-最终测试边界)。`openai-codex` 只能放在 `codex-test` 中，禁止加入运行依赖或由生产代码导入。`tests/support/codex_sdk.py` 是唯一的 SDK 导入／启动适配器；仅允许 `tests/support/final_codex_check.py` 在其他所有检查及本次构建的 `uv tool` 安装成功后调用真实最终查看。普通单测可使用 fake 验证这些边界，但不得启动 SDK。全新 CLI 仅执行版本、发现、能力和规则查看，模型回合数必须为零。保留根目录指令强制要求的环境变量复用、固定模型／推理强度、配置隔离及失败边界。


此限制适用于 MCP Server，不删除 `mcp/` 之外的原生运行时指令，也不增加文件系统、网络、凭据、Agent 创建或 Git 授权。

## 相关文档

- [MCP 开发指南](DEVELOPMENT_zh_cn.md)
- [Codex 调用者匹配](CODEX_CALLER_CONTEXT_zh_cn.md)

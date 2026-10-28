# MCP Server 开发指令

[English](AGENTS.md) | [简体中文](AGENTS_zh_cn.md)

本文负责 `mcp/` 下 MCP Server、各包、测试、元数据和文档的客户端支持边界。修改文档前，先读取仓库的[多语言规则](../MULTI_LINGUAL_zh_cn.md)。

## 支持的客户端

- MCP Server 仅支持 Codex 和 ChatGPT Desktop，不支持 Claude Code、Claude Desktop 或其他 Code Agent。
- 修改 `mcp/` 下的代码时，仅考虑基于 Codex 的 Agent 行为和受支持的桌面客户端。不得为其他 Code Agent 添加兼容分支、适配器、配置、示例、测试或工具指令。仓库级跨厂商对应能力核验不适用于本目录。
- 删除过时的不受支持客户端路径和声明，不将其保留为回退路线。共享协议或操作系统抽象不能证明支持额外客户端。
- 支持范围不等于实际宿主集成已经可用或通过验证。仍须核验已暴露能力、可信身份、守卫与权限，保留不可用结果及失败关闭行为。

## 范围与权限

此限制适用于 MCP Server，不删除 `mcp/` 之外的原生运行时指令，也不增加文件系统、网络、凭据、Agent 创建或 Git 授权。

## 相关文档

- [MCP 开发指南](DEVELOPMENT_zh_cn.md)
- [Codex 调用者匹配](CODEX_CALLER_CONTEXT_zh_cn.md)

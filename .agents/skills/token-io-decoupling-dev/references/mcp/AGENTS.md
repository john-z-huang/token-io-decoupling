# MCP Server 开发指令


本文负责 `mcp/` 下 MCP Server、各包、测试、元数据和文档的客户端支持边界。修改文档前，先读取仓库的[中文文档与指令规范](../MULTI_LINGUAL.md)。

## 支持的客户端

- MCP Server 面向本地可用的 Codex CLI，包括本地 Work 使用的本地 Codex CLI/app-server 路径。云端 ChatGPT 对话和远端 Work 不是直接客户端；其他 Code Agent 也不作为直接客户端受支持。
- 如果其他 Agent 在自己的环境安装 Codex CLI，并按本仓库说明在该环境配置 MCP Server，则受支持的调用路径仅为该环境内的本地 Codex CLI；这不会增加对其他 Agent 或云端界面的适配器或直接支持。Server 不要求调用者选择或分类运行环境。
- 修改 `mcp/` 下的代码时，考虑上述场景中的 Codex CLI 行为。不得为其他 Code Agent 添加兼容分支、适配器、配置、示例、测试或工具指令。仓库级跨厂商对应能力核验不适用于本目录。
- 删除过时的不受支持客户端路径和声明，不将其保留为回退路线。共享协议或操作系统抽象不能证明支持额外客户端。
- 无状态导航和结构评估不要求身份绑定，也不持久化分配状态。对于受保护操作，使用本地 stdio 请求范围，并执行当前角色、分配、应用路径和操作授权检查。不要求特权宿主集成，不声明独立身份认证；受保护的材料化操作仍保留可信绑定、授权和路径检查。

## 范围与权限

### Codex App Server 仅限测试

当前[最终检查协调器](../../tests/mcp/support/final_codex_check.py)和 [App Server adapter](../../tests/mcp/support/codex_app_server.py)实现[开发指南](DEVELOPMENT.md#codex-app-server-最终查看)描述的仅测试 App Server 路径。测试使用标准库 stdio JSON-RPC 客户端；协调器完成适用检查及当前构建安装后，再启动全新只读 CLI 查看。普通单元测试使用 fake，不启动 App Server。这些实现检查不授予生产编排或其他任务动作的授权。


此限制适用于 MCP Server，不删除 `mcp/` 之外的原生运行时指令，也不增加文件系统、网络、凭据、Agent 创建或 Git 授权。

## 相关文档

- [MCP 开发指南](DEVELOPMENT.md)
- [Codex 调用者匹配](CODEX_CALLER_CONTEXT.md)

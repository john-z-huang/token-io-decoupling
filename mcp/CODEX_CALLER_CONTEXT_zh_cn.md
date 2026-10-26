# Codex MCP 调用者匹配

[English](CODEX_CALLER_CONTEXT.md) | [简体中文](CODEX_CALLER_CONTEXT_zh_cn.md)

本文负责可选 Codex 请求匹配功能的实现契约与开发验证。匹配只约束已经验证的宿主绑定，不认证 Session、不分配角色、不证明父子关系，也不提供操作守卫。

## 源码契约

只读检查本地 Codex 源码快照 `bb8f5304fcd9f901d8e0747fccb8c8904cbc504e`，确认了以下事实：

- `codex-rs/core/src/mcp_tool_call.rs::with_mcp_tool_call_ids_meta` 在工具请求顶层 `_meta` 中加入 `threadId` 和 `sessionId`。两者是不同字段，均不提供 Root/Worker 角色或父子关系。
- `augment_mcp_tool_request_meta_with_sandbox_state` 和 `codex-rs/codex-mcp/src/sandbox_metadata.rs::augment_metadata` 可在服务声明相应能力时转发不透明沙箱状态。状态与 launcher 信息相互独立。调用者匹配器不请求这些能力，也不解释或执行 launcher 信息。

这些是源码事实，不证明当前连接的客户端运行该修订，也不证明它提供可信绑定。部署时必须分别核验实际客户端的线协议行为及身份、权限边界。此集成不修改 Codex 源码。

## 启用与权限来源

可信 supervisor 可通过 `token-io-mcp --host-fd N --codex-context` 启动服务，使用[开发指南](DEVELOPMENT_zh_cn.md#已认证的宿主通道)描述的已认证继承通道。`--codex-context` 必须与可用的宿主通道一起使用。等价的 Python factory 选项是在 `create_server` 中向经过验证的 provider 配置 `require_codex_context=True`。

这两个字段只从 MCP SDK 请求上下文读取。匹配器要求字符串非空且长度有界，缺少上下文或格式错误时拒绝。`threadId` 必须与可信 provider 的 `current_session_id` 完全相等。`sessionId` 仅作为不透明上下文；它的变化不会重置 canonical 身份、Mode/count、Run 或数据库状态。项目、Root、当前 Session、角色、能力和守卫仍由 provider 提供。工具 payload、环境变量和客户端名称均不能替代请求上下文或建立上述权限。

每个受保护的 Root/Worker callback 和已绑定 schema 诊断都在独立调用者作用域内执行。状态服务每次读取绑定，都将当前请求与 provider 的新鲜结果重新核对。作用域在返回或错误后重置，并在并发请求之间隔离；请求不得借用前一请求或并发请求的身份。身份不匹配时，在检查或修改状态路径前拒绝。公共规则与能力查询保持可用。

无关 `_meta` 字段被忽略。调用者元数据不会持久化到 SQLite，也不会出现在错误正文中。即使字符串匹配，provider 证据缺失或撤销时仍须拒绝。此选项不提供尚缺的真实宿主认证、沙箱执行边界或特权 supervisor 安装能力。

## 运行时对应关系

本次查阅的 [Claude Code MCP 文档](https://code.claude.com/docs/en/mcp)没有说明相同的顶层 `threadId`/`sessionId` 契约；其 [Hook 文档](https://code.claude.com/docs/en/hooks#common-input-fields)描述的是 Hook 输入中的 `session_id`，属于另一接口，不推断等价。Claude Code 不启用此 Codex 匹配器；在独立适配器得到验证前，使用通用可信宿主绑定路径。仅有 Hook 输入和环境变量，不能满足宿主认证或操作守卫要求。

## 开发验证

测试必须使用真实 MCP SDK 请求元数据，不能把字段放进工具参数代替。覆盖 Root、Worker 调用与持久化回读；调用者缺失、格式错误与不匹配；公共读取可用性；并发隔离；不透明 `sessionId` 变化；两次读取之间 provider 身份变化；以及文件系统副作用发生前的拒绝。保留精确工具 schema 和清单检查，确保 SDK context 不成为用户可提供的工具参数。

合成 provider 和对端认证覆盖仅构成测试证据，不证明实际客户端的认证、父子图、沙箱或当前会话数据库访问。修改后运行开发指南中的锁定检查。

## 相关概念

- [MCP 开发指南](DEVELOPMENT_zh_cn.md)
- [增强宿主绑定](../references/coding/layer-01-fundamental-concepts/enhanced-host-binding_zh_cn.md)
- [增强状态存储](../references/coding/layer-01-fundamental-concepts/enhanced-state-store_zh_cn.md)

# 外部参考资料

[English](EXTERNAL_REFERENCES.md) | [简体中文](EXTERNAL_REFERENCES_zh_cn.md)

本索引仅供开发和维护 `token-io-decoupling` Skill 时查阅。它是来源目录，不是执行指导。普通 Coding 任务不应加载本索引；Coding 工作流不依赖它。

| 来源 | URL | 对应文档 | 开发用途与边界 |
| --- | --- | --- | --- |
| Codex 桌面应用 | https://developers.openai.com/codex/app/ | [delegation-mode-confirmation_zh_cn.md](references/coding/layer-01-fundamental-concepts/delegation-mode-confirmation_zh_cn.md) | 仅作一般 composer 背景资料；不是 `request_user_input_async` 能力来源。 |
| Codex CLI | https://developers.openai.com/codex/cli/ | [delegation-mode-confirmation_zh_cn.md](references/coding/layer-01-fundamental-concepts/delegation-mode-confirmation_zh_cn.md) | 交互式终端使用的背景资料。 |
| Codex Prompting Guide | https://developers.openai.com/cookbook/examples/gpt-5/codex_prompting_guide | [delegation-mode-confirmation_zh_cn.md](references/coding/layer-01-fundamental-concepts/delegation-mode-confirmation_zh_cn.md) | 将多个建议呈现为编号选项的背景资料。 |
| Claude Code 工具参考 | https://code.claude.com/docs/en/tools#askuserquestion | [delegation-mode-confirmation_zh_cn.md](references/coding/layer-01-fundamental-concepts/delegation-mode-confirmation_zh_cn.md) | `AskUserQuestion` 界面及其回复行为的背景资料。 |
| MCP Python SDK v2 | https://py.sdk.modelcontextprotocol.io/whats-new/ | [增强架构](ENHANCED_ARCHITECTURE_zh_cn.md) | 核验 v2 服务端/客户端 API，并区分协议修订与包版本。 |
| MCP SDK 测试 | https://py.sdk.modelcontextprotocol.io/get-started/testing/ | [增强架构](ENHANCED_ARCHITECTURE_zh_cn.md) | 设计内存行为测试；它们不能证明任一宿主客户端的兼容性或线上传输交换。 |
| MCP 协议版本 | https://py.sdk.modelcontextprotocol.io/protocol-versions/ | [增强架构](ENHANCED_ARCHITECTURE_zh_cn.md) | 独立核验现代协议发现与版本证据，不依赖 SDK 主版本标签。 |
| MCP 客户端传输 | https://py.sdk.modelcontextprotocol.io/client/transports/ | [增强架构](ENHANCED_ARCHITECTURE_zh_cn.md) | 核验子进程 stdio 测试，不使用 GUI 交互或额外 Agent Session。 |
| MCP 传输授权 | https://py.sdk.modelcontextprotocol.io/run/authorization/ | [增强架构](ENHANCED_ARCHITECTURE_zh_cn.md) | 核验 HTTP 令牌校验不能认证 stdio 或进程内客户端；要求独立的可信启动边界。 |
| OpenAI Decisions | https://developers.openai.com/api/docs/guides/decisions | [增强架构](ENHANCED_ARCHITECTURE_zh_cn.md) | 核验可选语义判断的类型化选项请求及拒绝响应；此引用不授权真实请求。 |
| SQLite 备份 API | https://docs.python.org/3/library/sqlite3.html#sqlite3.Connection.backup | [增强架构](ENHANCED_ARCHITECTURE_zh_cn.md) | 在已授权的 schema 升级前使用数据库备份 API。 |
| Codex MCP | https://learn.chatgpt.com/docs/extend/mcp?surface=cli | [增强架构](ENHANCED_ARCHITECTURE_zh_cn.md) | 核验本地传输控制，不据此推断可信的逐 Agent 身份或文件系统隔离。 |
| Claude Code MCP 运行时 | https://code.claude.com/docs/en/mcp | [增强架构](ENHANCED_ARCHITECTURE_zh_cn.md) | 检查对应客户端的协议行为及依赖运行时的限制。 |

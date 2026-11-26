# 2026-11-18 · MCP 服务初始化与规则查询

## 服务初始化与参数校验

- 服务初始化不再拼接上游 `dev-workflow-standards-tools` 的长说明，改为本服务维护的中文调用说明。工具参数、返回格式和副作用仍以发现时的单项工具契约为准；34 个工具的发现元数据保持一致。[服务说明](../mcp/packages/token_io_decoupling_transport/src/token_io_decoupling_transport/tool_metadata.py) · [MCP 开发指南](../docs/project/mcp/DEVELOPMENT.md)
- MCP 服务在本项目内处理 SDK 参数校验错误，不再依赖上游私有的 `_SafeMCPServer`。拒绝的参数值仍不回显。嵌套 `payload` 改用 Pydantic 模型的 `model_validate_json`，保留原有 JSON 形状和严格类型校验；受保护的输出物化仍要求可信调用方绑定及授权。[服务入口](../mcp/src/token_io_decoupling/server.py) · [注册层](../mcp/packages/token_io_decoupling_transport/src/token_io_decoupling_transport/registration.py)

## 从源码检出运行

- [Skill 生成调整](2026-11-18-reference-readme-and-skill-build.md)后，源码检出直接运行 MCP 服务时，`rules_get_context` 仍从 `docs/skill/` 读取 Markdown。若尚未生成该目录，合法的规则查询也会失败。直接从源码启动 MCP 或运行依赖规则文档的测试前，在仓库根目录执行 `npm run build:skill`。构建钩子会生成打包所需的资源。[规则加载器](../mcp/packages/token_io_decoupling_core/src/token_io_decoupling_core/rules.py)

## 验证

- **PASS** · 使用相同版本的 MCP SDK 和 Pydantic，在隔离快照中对比缓存远端基线 `47941c7` 与本地基线 `1cf4b47`。34 个工具的发现元数据一致；所测无效参数的错误返回和缺少可信绑定时的拒绝行为一致。
- **PASS** · 旧基线 67 项 MCP 相关测试通过；本地基线未生成 Skill 时有 2 项规则读取测试失败，生成后 68 项全部通过。
- **SKIPPED** · 真实 API 调用及 Pi 客户端端到端验证。

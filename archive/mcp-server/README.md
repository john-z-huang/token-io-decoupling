# MCP Server 归档

此目录保存面向 Pi 的旧 `token-io-decoupling-tools` 服务。归档基线为本仓库提交 `9a507f31b5265e52daff6c2dfd085c5af15bbb53`。

- [服务源码、包配置及规则索引](mcp/)保持原目录结构。
- [测试与冒烟脚本](mcp/tests/)包含单元、模拟 API、真实 API 和安装验证的历史用例。[Pi 结构检查的旧测试](tests/test_pi_runtime_support.py)记录与 MCP 校验核心共享规则的做法。
- [历史开发指南](docs/mcp/DEVELOPMENT.md)、[安装说明](INSTALL.md)、[架构](docs/WORKFLOW_ARCHITECTURE.md)和[外部参考](docs/EXTERNAL_REFERENCES.md)记录原服务的工具契约及维护流程。旧安装与支持脚本在 [scripts/](scripts/)，测量数据在 [benchmarks/](mcp/benchmarks/)。
- [文档与工作流迁移资料](docs/migrations/WORKFLOW_MODULE_MIGRATION.md)包含两份清单、历史校验脚本与对应测试的基线快照。
- [旧 Context Exchange 校验](scripts/check-context-exchange.py)及[对应测试](tests/test_check_context_exchange.py)用于历史文件式 capsule。现行上下文交换遵循 [Serena 项目 Memory 合同](../../rules/references/coding/layer-01-fundamental-concepts/context-exchange/context-exchange.yaml)。

归档供查阅，历史命令及测试依赖归档基线中的完整目录和环境。现行 Hooks 构建、Skill 安装和默认验证排除本目录。 [当前 Skill 安装与更新](../../INSTALL.md)

项目 Memory 尾部读取和字面核验已迁往 `dev-workflow-standards`。 [迁移 PR](https://github.com/john-z-huang/dev-workflow-standards/pull/139)

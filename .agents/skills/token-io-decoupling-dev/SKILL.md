---
name: token-io-decoupling-dev
description: 维护本仓库的 MCP 运行时、指令编译器、生成 Skill、检查与发布工具；用于开发 token-io-decoupling 项目本身。
---

# Token I/O Decoupling 项目开发


本项目私有 Skill 负责本仓库的维护流程与验证，不进入产品包或安装目录。

1. 参考[项目开发指导](AGENTS.md)，再根据当前任务和用户指令选择本 Skill 中适用的流程。
2. 运行时实现属于 mcp，指令作者源与可执行依赖契约属于 instruction-compiler。不得手工编辑生成的产品资源或交付 Skill。
3. 优先使用有界 Serena 代码查询，以及覆盖所需操作的工作流、开发 MCP 工具；未覆盖操作可使用获准 CLI，以用户当前指令决定已释放范围。
4. 指令变更维护单一中文作者源与相关依赖、分支场景，编译并审阅生成行为，然后验证源新鲜度。必要执行依赖缺失或有歧义时阻止发布。
5. 本 Skill 的 scripts 负责仓库检查；开发检查和文档回归直接使用本私有 Skill 的实际入口。根 scripts 仅保留真实安装入口，不保留开发或测试转发别名。产品测试位于 tests/mcp，编译器测试由编译项目负责。
6. 包检查与有序最终协调器见 [MCP 开发指南](references/mcp/DEVELOPMENT.md)。先通过其它适用检查，再构建、隔离 uv tool 安装及全新 CLI 检查。App Server 仅测试、有界只读且零 model turns。
7. 保留通用运行时身份、独立 grant、路径、baseline、preflight 及写入时守卫。项目专属作者文档检查保持私有；hash 不证明语义正确或授权。
8. 验收前检查包内容、同批次 manifest 与独立 sdist 重建。Git 和远端副作用遵循已有任务授权。

## 相关概念

- [MCP 开发边界](references/mcp/AGENTS.md)。
- [外部来源登记](references/EXTERNAL_REFERENCES.md)，仅开发指令时读取。
- [作者工作流架构](../../../instruction-compiler/sources/skill/WORKFLOW_ARCHITECTURE.md)。

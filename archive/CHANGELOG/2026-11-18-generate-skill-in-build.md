# 2026-11-18 · 安装与打包时自动生成 Skill

## 改动

- 将 Skill 生成从 npm 的 `prepack` 移到 `prepare`。从干净检出运行 `npm ci --legacy-peer-deps` 或 `npm pack` 时，npm 会调用 `uv` 从 `docs/rules/` 生成 `docs/skill/`，加载扩展前不必再单独生成。保留 `npm test` 的生成步骤和单独重建用的 `npm run build:skill`；生成目录仍由 Git 忽略。[项目命令](../package.json) · [Pi Extension 安装说明](../docs/project/PI_EXTENSION.md#试用与安装)
- [MCP 源码测试流程](../docs/project/mcp/DEVELOPMENT.md#包结构与验证)明确在 `uv sync` 和测试前生成 Skill。即使复用已有的依赖和包构建结果，规则查询仍能读取当前检出的生成文档。MCP 打包钩子保持不变。

## 验证

- **PASS** · 在两个没有 `docs/skill/` 的独立源码副本中，分别离线运行 `npm ci` 和 `npm pack`。生成结果校验通过，打包产物包含全部 115 个 Skill 文件，包括入口 `SKILL.md` 和注册元数据。
- **PASS** · 147 项 Pi 扩展测试、36 项相关 MCP 测试及 Hook 检查全部通过。

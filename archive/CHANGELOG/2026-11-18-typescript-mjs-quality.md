# 2026-11-18 TypeScript 与 MJS 代码质量优化

## 改动需求

对仓库原有的 28 个 TypeScript 和 MJS 文件做全量可读性审查，按职责拆分过长实现和测试，逐步清理存量 Lint 抑制。使用 ESLint 调用 Prettier 完成排版，延续仓库的静态规则。

- 工作流引擎将检查点推进、Slice 与委派守卫、暂停恢复、快照验证分开。保持批量上报的原子性、证据核验、精确路径和 epoch 约束，以及两条路线的分支和返回条件。 [引擎入口](../archive/pi-coding-workflow/extensions/coding-workflow/engine.ts) · 检查点推进（历史路径 `extensions/coding-workflow/engine/checkpoint-progress.ts`）
- Pi 运行时将会话状态、恢复、启动命令、工具事件和回合事件分开。保持现有 `/coding` 命令、工具 Schema、会话预算、工具授权和效果读回的行为。为启动答案、模型选型和两种子代理调用 Schema 明确输入校验与类型边界。 [运行时入口](../archive/pi-coding-workflow/extensions/coding-workflow/runtime.ts) · [启动参数](../archive/pi-coding-workflow/extensions/coding-workflow/startup.ts) · [子代理适配](../archive/pi-coding-workflow/extensions/coding-workflow/subagent-adapter.ts)
- 规则读取将 YAML 块解析、片段渲染、链接转换和目录验证分开。保持规则 ID、阶段绑定、Hook 触发条件和注入正文。工作流摘要要覆盖拆分后的全部扩展源码，旧快照按既有摘要校验要求重新核验。 [运行时目录](../archive/pi-coding-workflow/extensions/coding-workflow/catalog.ts) · [规则加载](../archive/pi-coding-workflow/extensions/coding-workflow/reference-data.ts)
- 按检查点恢复、规则目录和运行时查询场景整理回归用例，保持测试可独立运行。Pi 验证脚本复用宿主包解析和加载逻辑，旧版子代理冒烟检查继续核对部署副本并使用模拟进程。npm 包清单递归纳入扩展 TypeScript 文件。 恢复测试（历史路径 `extension-tests/engine-recovery.test.mjs`） · [规则查询测试](../archive/pi-coding-workflow/extension-tests/runtime-rule-queries.test.mjs) · [宿主检查公共模块](../archive/pi-coding-workflow/scripts/pi-installed-host.mjs) · [npm 包清单](../package.json)

## 文件范围

| 位置 | 变更范围 |
| --- | --- |
| `extensions/coding-workflow/` | 更新 12 个入口与实现文件，在 `engine/`、`host/` 和 `rules/` 下新增 12 个模块。 |
| `extension-tests/` | 更新 4 个现有测试或 fixture，新增 4 个按场景拆分的测试或 fixture。 |
| `scripts/` | 更新 6 个 Pi 和 Hook 检查脚本，新增共享宿主加载模块。 |
| 仓库根目录 | 更新 `eslint-suppressions.json` 和 `package.json`。保留 Pi 固定五参数回调所需的 4 处抑制。 |

改动范围共 41 个代码、测试和配置路径，另新增本日志。

## 验证

- `npm run lint:fix` 和 `npm run lint` 通过。关闭抑制扫描时，诊断数从 134 条降到 4 条，均为 Pi 固定回调签名。
- `npm test` 的 154 项测试、Hook 检查、规则 DSL 检查、Pi 宿主类型与加载检查、`@mjakl/pi-subagent` 3.1.0 契约检查均通过。旧版子代理在隔离目录中通过模拟进程检查。
- 使用同一规则目录比较重构前后，405 个工作流上下文、573 个规则片段和 16 份 Hook 正文一致。npm 打包预检确认 27 个扩展 TypeScript 文件全部进入包清单和工作流源码摘要。

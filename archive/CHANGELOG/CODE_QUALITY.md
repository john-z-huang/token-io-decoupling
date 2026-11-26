# 代码质量工具与规范自动化变更日志

## 未发布

### 自动化 JS、TS 和 MJS 代码规范检查

将可由工具判定的代码规范纳入日常 Lint。Code Agent 根据实际变更审查需要语义和上下文证据的条款。

- 用 ESLint 检查非测试代码的规模、复杂度与嵌套，检查测试的规模、名称与分组，以及适用的标识符、TypeScript 类型约束与模块依赖。函数行数限制涵盖立即执行函数。锁定 SonarJS 和 import-x 开发依赖，显式配置 Prettier 排版规则。`npm run lint` 汇总检查结果，`npm run lint:fix` 只应用排版修复。
- 按文件和规则登记启用检查时已有的违规，包括 Pi 固定回调的参数限制例外。新文件出现违规或存量文件超出登记数量时由 Lint 报错。Code Agent 核对受影响的存量违规位置和程度。
- 在项目文档中维护 [TypeScript / JavaScript 代码规范](../docs/project/TS_JS_CODE_SPECIFICATION.md) 和独立的 [静态代码检查](../docs/project/STATIC_CODE_CHECKS.md)，逐项说明自动化范围与 Code Agent 的审查要求。更新自检指引、仓库指令、文档索引和 Pi Extension 验证入口。

### JS、TS 和 MJS 的格式化与可读性

为 Extension、测试和开发脚本提供可重复的代码检查与格式化命令。

- `npm run lint` 检查代码规则和格式，`npm run lint:fix` 由 ESLint 调用 Prettier，只应用排版修复。同步更新 npm 开发依赖、锁文件和项目开发说明。ESLint 配置位于仓库源码路径 `eslint.config.js`，Prettier 配置位于 `.prettierrc.json`。

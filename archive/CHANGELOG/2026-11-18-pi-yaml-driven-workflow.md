# 2026-11-18 · Pi Coding 工作流改用 YAML 指令与 Hooks

## 两条工作流路线

Single-Agent 和 Multi-Agent 路线保留七个主阶段、Hook 绑定和验收终点。补证、修复、回验、未知效果及原位恢复由各自的 Hook 合同定义，Pi Coding Agent 在对话上下文中按实际证据决定何时应用。路线模板、结构检查和链接规则同步核对必要顺序及 Hook 归属。 [单代理路线](../docs/rules/coding-workflows/coding-single-agent.yaml) · [多代理路线](../docs/rules/coding-workflows/coding-multi-agent.yaml)

## 扩展运行时

- 删除 `workflow-context.ts`、`workflow-state.ts`、`workflow-tools.ts`，以及检查点推进和证据处理模块。扩展注入所选 YAML 和触发的合同，移除 `coding_checkpoint report`、固定阶段返回和自动续跑。
- 保留工具执行的保护条件。文件写入核对 Slice 和精确路径，不透明工具经 Pi 宿主校验链执行，委派核对模式、预算、职责和实际工具 Schema。旧会话可读回既有委派名额和未决效果，旧阶段位置仅供恢复时参考。
- 手动启动失败或取消后，未启用的扩展恢复被动。普通用户输入只撤销旧写入范围，上下文压缩保留当前会话状态。用户显式启动后续任务时沿用会话模式和已占名额，有暂停或未决效果时先处理恢复。
- 模型卡供主 Agent 选型参考，适配器可向宿主转发其他精确模型 ID。Git 前置验证核对内容和文档回执的时效，Git 元数据由交付 Hook 单独核验。

使用方式与界限见 [Pi 扩展说明](../docs/project/PI_EXTENSION.md)和[工作流架构](../docs/project/WORKFLOW_ARCHITECTURE.md)。

## 验证

- **PASS**　122 项扩展离线测试、62 项仓库测试、lint、规则 DSL、文档链接和 Hook 检查。
- **PASS**　Pi 1.5.2 类型及入口加载检查、`@mjakl/pi-subagent` 3.1.0 注册 Schema 和参数契约检查。
- **SKIPPED**　真实模型驱动的 Pi 会话、实际子代理派发和 Memory 后端的端到端测试。

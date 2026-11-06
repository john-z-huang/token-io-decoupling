# 工作流规则上下文

[English](rule-context.md) | [简体中文](rule-context_zh_cn.md)

本文档负责当前编译工作流指令的交付与有界消费；不负责检查点结构评估、底层政策、调用方身份或工作授权。

## 通用规范

### 消费当前可执行指令

作者 owner 是开发期政策源。执行时消费当前步骤完整的编译指令，不依靠作者文件名或需要自行拼政策的摘录。明确的指令继续入口标识下一独立单元，须在其依赖动作前取得；保留暂停动作，仅在构建和语言仍一致时复用已持有单元。资源标识、Hash 或完整状态均不能证明任务事实或检查点完成。

将消费范围限制在当前判断所需内容。不得扫描仓库或沿原始 owner 链接查找；仅解决当前动作所需的明确继续入口。指令资源缺失、损坏、不兼容或混构建时阻塞依赖工作，不回退作者 Markdown，也不推断遗漏政策。选择获授权的文档路径时，可由同一构建生成的纯文档 Skill 提供相应编译单元。可选导航不需要时，记录附理由的 `Not applicable`。


## Codex CLI / ChatGPT Desktop 特别优化指令

使用 `rules_get_context`，传入 `context_version: 2`、注册的 `node_id`、一种语言，以及当前继续入口要求的明确编译 `fragment_ids`。审阅返回的指令正文、构建标识、未解决事实和失败状态；预算失败不允许执行部分内容。工具发现不建立身份或授权；服务仅按其客户端边界支持本地 Codex CLI。

## Claude Code CLI / Claude Desktop 特别优化指令

本项目 MCP Server 没有受支持的 Claude 直接对应能力。将该 MCP 优化记为 `Not applicable`，通过实际暴露且获授权的文档能力，消费同一构建生成的纯文档 Skill 中的明确指令单元。这不增加 MCP 客户端，也不允许回退作者源；遵循通用证据与失败边界。

## 相关概念

- [工作流导航可用性](navigation-availability_zh_cn.md) — 负责导航不可用分支。
- [检查点结构检查](checkpoint-structure-checks_zh_cn.md) — 负责评估调用方提供的检查点事实结构。
- [Workflow Routing Advice](../execution-planning/workflow-routing-advice_zh_cn.md) — 负责可选阶段建议。
- [Coding Execution Control](../execution-control/execution-control_zh_cn.md) — 负责 Slice 与 Control 决策。
- [Coding Delegation State Record](../delegation/delegation-state-record_zh_cn.md) — 负责规范的父级控制工作流记录。

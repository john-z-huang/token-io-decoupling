# 工作流规则上下文

[English](rule-context.md) | [简体中文](rule-context_zh_cn.md)

本文档负责有界导航至当前工作流规则；不负责检查点结构评估、底层规则、调用方身份或工作授权。

## 通用规范

### 仅读取所需规则上下文

使用当前工作流 owner 作为权威来源。注册表或有界摘录可帮助定位适用标题，但其存在、Hash 或完整状态不能证明已读取完整任务上下文，也不能证明检查点已通过。若判断依赖返回材料未包含的直接链接 owner，应以相同语言单独读取该 owner。绝不能根据索引、摘录、过期快照或 Hash 推断缺失的策略。

将导航范围限制在当前判断所需内容。不得扫描整个仓库，也不得将链接引用视为已递归加载。必需内容缺失或结果不完整时，调用方必须直接获取权威 owner；若无法获取，则仅阻塞依赖该内容的判断。导航不需要时，记录附有理由的 `Not applicable`。


## Codex CLI / ChatGPT Desktop 特别优化指令

需要时使用 `rules_get_context` 定位当前注册规则上下文，再核验任何未覆盖的直接 owner。发现工具不代表身份或授权已成立。

## Claude Code CLI / Claude Desktop 特别优化指令

当前没有 Claude 专属的规则上下文优化。遵循通用规范，仅使用当前 Session 实际暴露的能力，并直接依据权威 owner 保持等效证据。

## 相关概念

- [工作流导航可用性](navigation-availability_zh_cn.md) — 负责导航不可用分支。
- [检查点结构检查](checkpoint-structure-checks_zh_cn.md) — 负责评估调用方提供的检查点事实结构。
- [Workflow Routing Advice](../execution-planning/workflow-routing-advice_zh_cn.md) — 负责可选阶段建议。
- [Coding Execution Control](../execution-control/execution-control_zh_cn.md) — 负责 Slice 与 Control 决策。
- [Coding Delegation State Record](../delegation/delegation-state-record_zh_cn.md) — 负责规范的父级控制工作流记录。

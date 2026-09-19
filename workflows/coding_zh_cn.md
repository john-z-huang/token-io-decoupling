# Coding 工作流

[English](coding.md) | [简体中文](coding_zh_cn.md)

当仓库文本、开发工具输出、实现、测试、文档或 Git 状态是主要工作状态时，使用本工作流。本文件只负责 Coding 路线选择和完成索引。选定的 `exist-workflow` 文档负责组合执行所需的 references 与检查点。根指令模式和委派决策只由 `references/coding/agent-delegation-control_zh_cn.md` 负责。

## 入口

1. 加载根指令模式门禁所需的委派权威。
2. 识别真实运行环境并完成运行环境检查点。
3. 在模式门禁和运行环境检查完成后，只选择一条完整路线。该路线自行加载 references 并组合检查点。

## 路线

- [单代理 Coding](exist-workflow/coding-single-agent_zh_cn.md)：只有权威状态记录单代理结果时使用。
- [多代理 Coding](exist-workflow/coding-multi-agent_zh_cn.md)：只有权威状态记录多代理结果且委派状态可用时使用。

不要同时加载两条路线。如果后续实质事实使路线失效，停止当前切片，按需修改 Contract，并返回路线选择。

## 检查点目录

路线可以按条件组合以下独立动作边界：

`contract` → `environment` → `mode` → `context` → `decision` → `implementation` → `control` → `verification` → `repair` → `documentation` → `git` → `acceptance`

目录只用于导航。检查点不负责路由到另一个检查点；选定路线定义实际顺序，并记录跳过条件检查点的原因。

## 完成

只有选定路线以当前证据通过验收后，才能返回 `COMPLETE`。报告不可用检查、假设、剩余风险、已授权影响和已记录的委派状态。没有明确授权时不得产生外部影响。

# Coding 工作流

[English](coding.md) | [简体中文](coding_zh_cn.md)

当仓库文本、开发工具输出、实现、测试、文档或 Git 状态是主要工作状态时，使用本工作流。本文件只负责 Coding 路线选择和完成索引。选定的 layer-03 workflow 模板负责组合执行所需的 layer-01 概念和 layer-02 工作流概念。根指令模式和委派规则由模式检查点组合的原子委派 references 负责；任务控制记录保存当前状态。

## 入口

1. 通过模式检查点组合根指令模式门禁所需的委派 references。
2. 识别真实运行环境并完成运行环境检查点。
3. 在模式门禁和运行环境检查完成后，只选择一条完整路线。该路线自行加载 references 并组合检查点。

## 路线

- [单代理 Coding](../references/coding/layer-03-workflows/coding-single-agent_zh_cn.md)：只有任务记录写明 `mode: Single-Agent Coding` 时使用。
- [多代理 Coding](../references/coding/layer-03-workflows/coding-multi-agent_zh_cn.md)：只有任务记录写明 `mode: Multi-Agent Coding` 且已锁定正整数 `child_count` 时使用。

不要同时加载两条路线。如果后续实质事实使路线失效，停止当前切片，按需修改 Contract，并返回路线选择。

## 文档层级

这些层级规定组合方向，不改变策略归属。每个文档可以保留语言切换链接；依赖链接必须保持同语言。

| 层级 | 作用 | 允许依赖的目标 |
| --- | --- | --- |
| [`layer-01-fundamental-concepts`](../references/coding/layer-01-fundamental-concepts/) | 基础原子概念 | 仅其语言镜像 |
| [`layer-02-workflow-concepts`](../references/coding/layer-02-workflow-concepts/) | 工作流检查点 | `layer-01-fundamental-concepts`；不得链接 layer-03 |
| [`layer-03-workflows`](../references/coding/layer-03-workflows/) | 可直接使用的工作流模板 | layer-01 和 layer-02；不得回链本选择器 |
| `workflows/coding_zh_cn.md` | 路线选择器和三层索引 | 三个层级；只负责导航，不拥有策略 |

如果低层文档需要由高层拥有的概念，应将其视为原子化失败：拆分低层文档，并把组合关系上移到高层。`SKILL.md`、`README.md` 和 `docs/` 等根入口文档可以向下链接到入口。使用 `python3 scripts/check-doc-layer-links.py` 检查边界；语言切换链接是唯一有意保留的跨语言链接。

## 检查点目录

路线可以按条件组合 [layer-02 工作流概念](../references/coding/layer-02-workflow-concepts/) 中的以下独立动作边界：

`contract` → `environment` → `mode` → `context` → `decision` → `implementation` → `control` → `verification` → `repair` → `documentation` → `git` → `acceptance`

目录只用于导航。检查点不负责路由到另一个检查点；选定路线定义实际顺序，并记录跳过条件检查点的原因。

## 完成

只有选定路线以当前证据通过验收后，才能返回 `COMPLETE`。报告不可用检查、假设、剩余风险、已授权影响和已记录的委派状态。没有明确授权时不得产生外部影响。

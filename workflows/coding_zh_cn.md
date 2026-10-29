# Coding 工作流

[English](coding.md) | [简体中文](coding_zh_cn.md)

当仓库文本、开发工具输出、实现、测试、文档或 Git 状态是主要工作状态时，使用本工作流。本文件只负责 Coding 路线选择和完成索引。Layer-03 决策检查点判断当前任务的适用性与分支；选定的 Layer-04 路线排列这些决策，并组合执行所需的 Layer-01 概念与 Layer-02 检查点动作。根指令模式和委派规则由模式检查点组合的原子委派 references 负责；父级控制的记录保存会话级模式/数量选择和当前任务状态。

## 入口

1. 在路线选择前完成 Contract 检查点。
2. 识别真实运行环境，完成运行环境检查点，并建立或加载[运行环境能力清单](../references/coding/layer-02-workflow-concepts/entry-and-context/environment-capability-inventory_zh_cn.md)进行能力检查。
3. 通过消费已建立的运行环境能力清单的模式检查点，组合根指令模式门禁所需的委派 references。
4. 使用当前证据调用[路线入口](../references/coding/layer-03-workflow-checkpoints/route-entry_zh_cn.md)，确认 Contract、运行环境、能力清单和 Mode 均已通过。只选择其授权的完整路线，并将已释放的 mode/count 证据交给首个模块检查点 SM01/MM01。每条路线依次组合[入口就绪](../references/coding/layer-04-workflows/modules/entry-readiness_zh_cn.md)、[Session 就绪](../references/coding/layer-04-workflows/modules/session-readiness_zh_cn.md)、[工作定义](../references/coding/layer-04-workflows/modules/work-definition_zh_cn.md)、对应模式的执行模块、[验证与修复](../references/coding/layer-04-workflows/modules/verification-repair_zh_cn.md)、[文档](../references/coding/layer-04-workflows/modules/documentation_zh_cn.md)和[交付与验收](../references/coding/layer-04-workflows/modules/delivery-acceptance_zh_cn.md)。只在到达时加载已选路线及对应模块。

## 路线

- [单代理 Coding](../references/coding/layer-04-workflows/coding-single-agent_zh_cn.md)：用户明确选择 `mode: Single-Agent Coding` 时使用；与指令相关的任务事项留在当前 Session 中完成。
- [多代理 Coding](../references/coding/layer-04-workflows/coding-multi-agent_zh_cn.md)：已释放的 Mode 选择 Multi-Agent Coding 且已锁定正整数 `child_count` 时使用。Mode 检查点负责四项菜单、默认值和无效输入处理；锁定预算不初始化子代理。

不要同时加载两条路线。如果后续实质事实使路线失效，停止当前切片，按需修改 Contract，并返回路线入口。

## 文档层级

这些层级规定组合方向，不改变策略归属。每个文档可以保留语言切换链接；依赖链接必须保持同语言。

| 层级 | 作用 | 允许依赖的目标 |
| --- | --- | --- |
| [`layer-01-fundamental-concepts`](../references/coding/layer-01-fundamental-concepts/) | 基础原子概念 | 同语言的 layer-01 概念及其语言镜像 |
| [`layer-02-workflow-concepts`](../references/coding/layer-02-workflow-concepts/) | 通用工作流检查点动作与证据 | `layer-01-fundamental-concepts`；不得链接 layer-03/04 |
| [`layer-03-workflow-checkpoints`](../references/coding/layer-03-workflow-checkpoints/) | 当前任务的适用性、分支与组合决策 | layer-01、layer-02；不得链接 layer-04 |
| [`layer-04-workflows`](../references/coding/layer-04-workflows/) | 完整可执行路线 | 共享协议、layer-01、layer-02 和 layer-03；路线也可调用其精确批准的同语言 Layer-04 模块，模块仅依赖共享协议与 Layers 01–03 且不得调用同级模块 |
| `workflows/coding_zh_cn.md` | 路线选择器和四层索引 | 四个层级；只负责导航，不拥有策略 |

如果低层文档需要由高层拥有的概念，应将其视为原子化失败：拆分低层文档，并把组合关系上移到高层。`SKILL.md`、`README.md` 和 `docs/` 等根入口文档可以向下链接到入口。使用 `python3 scripts/check-doc-layer-links.py` 检查边界；语言切换链接是唯一有意保留的跨语言链接。

## 检查点目录

路线按序消费 [layer-02 检查点](../references/coding/layer-02-workflow-concepts/)、[layer-03 工作流决策](../references/coding/layer-03-workflow-checkpoints/)，并由 layer-04 完整路线组合以下独立动作边界：

`contract` → `environment`（+ 能力清单）→ `mode` → `context` → `decision` → `implementation` → `control` → `verification` → `repair` → `documentation` → `git` → `acceptance`

目录只用于导航。检查点不负责路由到另一个检查点；选定路线定义实际顺序，并记录跳过条件检查点的原因。

## 完成

只有选定路线以当前证据通过验收后，才能返回 `COMPLETE`。报告不可用检查、假设、剩余风险、已授权影响和已记录的委派状态。没有明确授权时不得产生外部影响。

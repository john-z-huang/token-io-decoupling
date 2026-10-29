# 决策上下文选择

[English](decision-context-selection.md) | [简体中文](decision-context-selection_zh_cn.md)

本检查点负责决定下游决策是否需要生成背景，以及该背景是否当前且可用；不代替执行主体、输出路由、职责、建议资格或其他下游决策。

## 触发与输入

在 S05/M06 消费当前决策问题、带来源溯源的已核实事实、用户明确指令，以及可能使用生成上下文的下游决策。应用[决策上下文生成](../layer-01-fundamental-concepts/execution-planning/decision-context-generation_zh_cn.md)。本检查点不启用建议。单独的可选五节点阶段建议门禁由路线建议选择和[Decisions 建议](../layer-01-fundamental-concepts/execution-planning/decisions-advisory_zh_cn.md)负责；它不会重开或改变 Mode。执行主体、输出路由、候选和职责决策仍由各自直接 owner 负责。

## 决策与结果

1. 命名尚未解决的下游问题，并识别与问题有关的当前事实和约束，保留来源指针及来源标签。区分用户要求、当前证据、计划、假设和未经核实的说法。
2. 若用户明确指令已经决定相关选项，或没有下游决策需要生成上下文，则记录 `Not applicable` 和原因。否则仅把该问题必需的有界事实、来源和具体决策目标交给 Decision Context Generation。
3. 审阅返回上下文的事实准确性、来源、语言、相关性和缺失信息。将输入 Hash 与当前确切源材料和目标比较；将政策绑定与当前适用规则比较。拒绝过期、不匹配、不完整或冲突的上下文，不得发送给下游建议。
4. 向指定下游 owner 返回以下一种结果：

| 结果 | 必需路线动作 |
| --- | --- |
| 上下文已审阅，输入/政策绑定精确且当前 | 仅向对应建议消费者传递该上下文及来源/Hash 证据。 |
| 明确指令已决定选项，或下游决策无需生成上下文 | 记录 `Not applicable` 和原因；遵循明确指令或按直接决策 owner 继续。 |
| 生成失败，或必需事实缺失/冲突 | 不得伪造上下文或 Hash。仅当直接 owner 下的已核实事实足够时直接判断；否则阻塞依赖决策并请求缺失证据。 |

## 失败边界

生成的上下文仅是辅助输入，不是决策、授权或当前直接 owner 的替代品。本检查点不决定任何建议是否启用、相关或可接受；各直接决策 owner 保留自身门禁，单独的可选五节点阶段建议门禁仍由对应的路线检查点负责。

## 相关概念

- [决策上下文生成](../layer-01-fundamental-concepts/execution-planning/decision-context-generation_zh_cn.md)

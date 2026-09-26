---
name: token-io-decoupling
description: "面向 Coding 的高体量 Agent Token I/O 解耦：将输入侧高价值推理、实现输出、独立改动验证，以及负责获准文档/注释与非简单仓库 Git 工作的 Documentation/Comments & Git Operations 角色分离，同时让 Core 的角色与 Session 规则保持对具体 Code Agent 产品和模型无关；运行环境绑定和能力检查由 Coding 工作流声明。"
---

# Token I/O Decoupling

[English](SKILL.md) | [简体中文](SKILL_zh_cn.md)

当前本 Skill 只维护一套可执行工作流：Coding。它用于把高价值语义决策与高体量项目状态消费、输出物化分离。Multimodal 和 Mixed 内容目前不作为本仓库中的可执行工作流维护。

Coding 的委派和 Session 拓扑规则拆分为原子 reference：状态记录、模式/数量门禁，以及按条件加载的子代理派发/生命周期策略。模式检查点在路线选择前组合并验证这些 reference；父级控制的记录保存会话级模式/数量选择和当前任务状态。

本 Skill 只定义调度约定，不能绕过更高优先级的权限、用户授权、产品限制、仓库指令或安全规则，也不把价格、缓存命中、额度节省、延迟或 Runtime 质量表述为未经实测的事实。

## 从这里开始

按以下顺序逐项执行。确认当前检查点的结果后才能进入下一项；条件步骤不适用时，记录原因，不得默默跳过。

1. 读取 [Coding 工作流](workflows/coding_zh_cn.md)并完成 Contract 检查点；确认任务约束和验收条件。
2. 完成运行环境检查点；建立或加载运行环境能力清单，确认本任务所需能力。
3. 使用该清单完成模式检查点。本次会话首次 Coding 指令使用用户明确选择；否则只询问一次并等待 15 秒，未观察到明确回复则默认多代理及 1 个子代理。确认任务控制记录包含已放行模式及其必需状态；后续指令沿用已锁定模式/数量。
4. 根据该记录只选择一条路线：`mode: Single-Agent Coding` 时使用[单代理路线](references/coding/layer-03-workflows/coding-single-agent_zh_cn.md)；`mode: Multi-Agent Coding` 且已锁定正整数 `child_count` 时使用[多代理路线](references/coding/layer-03-workflows/coding-multi-agent_zh_cn.md)。
5. 按所选路线的编号检查点顺序逐项执行。只加载当前步骤需要的 reference；每项完成或明确处置后才能进入下一项。
6. 任务改变方向或最终验收前，返回 [Coding 工作流](workflows/coding_zh_cn.md)；报告 `COMPLETE` 前确认路线的完成证据。

## 适用范围

仓库或项目探索、实现、重构、调试、测试、文档、开发工具输出以及非简单 Git 工作均使用 Coding。Coding 工作流负责共用队列、模块组合、运行环境选择、模式路由、checkpoint、验证边界、文档/Git 边界和验收。

## 硬约束

- 采取行动前记录用户、运行环境、仓库、权限、安全和 Session 硬约束。
- “不要创建子代理”“不要使用浏览器”等任务级禁止条件在整个任务中持续有效。
- 路线选择或任何委派/Session 拓扑工作前，模式检查点必须组合并验证委派 references；这些 references 在各自的原子边界内规定会话级模式选择及 15 秒默认值、子代理数量、创建、分配、复用、替换、例外和限制。
- 不得虚构授权、能力、证据、产品支持，或为未维护场景推导可执行路线。
- Core 规则不依赖具体产品；受支持的运行环境分支和模型绑定见[运行环境与模型厂商支持](references/coding/layer-01-fundamental-concepts/runtime-provider-support_zh_cn.md)。
- 按需读取 reference。不要仅因为可能以后有用，就预加载整个 Skill、`references/` 或原始项目状态。

## 完成

遵循选定的 Coding 工作流，只有其最终验收门禁拥有明确证据后才能返回 `COMPLETE`。清楚报告跳过或不可用的检查、假设、剩余风险和未授权效果。
